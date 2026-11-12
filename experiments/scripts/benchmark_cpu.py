"""Measure CPU latency and memory of the pilot models on the smoke-test invoice.

The result decides how many pilot items fit in the time budget (report, Chapter 3).
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import time
from datetime import datetime
from pathlib import Path

import psutil
import torch
import transformers
from PIL import Image
from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoProcessor, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "data" / "generated" / "smoke"

VLM_ID, VLM_REV = "Qwen/Qwen2.5-VL-3B-Instruct", "66285546d2b821cf421d4f5eb2576359d3770cd3"
LLM_ID, LLM_REV = "Qwen/Qwen2.5-3B-Instruct", "aa8e72537993ba99e69dfaafa59ed015b17504d1"

QUESTION = 'Care este valoarea câmpului "Data scadenței" din această factură?'
VLM_INSTRUCTION = (
    'Answer with JSON only, in the form {"answer": "<value exactly as written>", '
    '"bbox_2d": [x1, y1, x2, y2]}, where bbox_2d is the box of the value in the image.'
)
LLM_INSTRUCTION = 'Answer with JSON only, in the form {"answer": "<value exactly as written>"}.'


def rss_gb() -> float:
    return psutil.Process().memory_info().rss / 2**30


def parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def iou(a: list[float], b: list[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def gold(words: list[dict]) -> tuple[str, list[float]]:
    value = [w for w in words if w["field"] == "due_date" and w["role"] == "value"]
    boxes = [w["box"] for w in value]
    return " ".join(w["text"] for w in value), [
        min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)
    ]


def reading_order_text(words: list[dict]) -> str:
    """Oracle text: words grouped into lines by vertical centre, lines top to bottom, words left to right."""
    lines: list[list[dict]] = []
    for w in sorted(words, key=lambda w: ((w["box"][1] + w["box"][3]) / 2, w["box"][0])):
        centre = (w["box"][1] + w["box"][3]) / 2
        if lines and abs(centre - (lines[-1][0]["box"][1] + lines[-1][0]["box"][3]) / 2) < 6:
            lines[-1].append(w)
        else:
            lines.append([w])
    return "\n".join(" ".join(w["text"] for w in sorted(line, key=lambda w: w["box"][0])) for line in lines)


def bench_vlm(image_path: Path, words: list[dict], max_pixels: int, dtype: torch.dtype, repeats: int) -> dict:
    t0 = time.perf_counter()
    processor = AutoProcessor.from_pretrained(VLM_ID, revision=VLM_REV, min_pixels=256 * 28 * 28, max_pixels=max_pixels)
    model = AutoModelForImageTextToText.from_pretrained(VLM_ID, revision=VLM_REV, dtype=dtype).eval()
    load_s = time.perf_counter() - t0

    image = Image.open(image_path).convert("RGB")
    messages = [{"role": "user", "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": f"{QUESTION}\n{VLM_INSTRUCTION}"},
    ]}]
    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
    )
    _, grid_h, grid_w = inputs["image_grid_thw"][0].tolist()
    patch = processor.image_processor.patch_size
    resized_w, resized_h = grid_w * patch, grid_h * patch

    runs = []
    for _ in range(repeats):
        t1 = time.perf_counter()
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=64, do_sample=False)
        runs.append(time.perf_counter() - t1)
    text = processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]

    answer, gold_box = gold(words)
    sx, sy = resized_w / image.width, resized_h / image.height
    gold_resized = [gold_box[0] * sx, gold_box[1] * sy, gold_box[2] * sx, gold_box[3] * sy]
    parsed = parse_json(text)
    box = parsed.get("bbox_2d")
    return {
        "model": VLM_ID, "revision": VLM_REV, "dtype": str(dtype), "max_pixels": max_pixels,
        "resized_image": [resized_w, resized_h], "input_tokens": int(inputs["input_ids"].shape[1]),
        "load_seconds": round(load_s, 1), "generate_seconds": [round(r, 1) for r in runs],
        "peak_rss_gb": round(rss_gb(), 1), "raw_output": text, "gold_answer": answer,
        "answer_correct": parsed.get("answer", "").strip() == answer,
        "iou_with_gold": round(iou(box, gold_resized), 3) if isinstance(box, list) and len(box) == 4 else None,
    }


def bench_llm(words: list[dict], dtype: torch.dtype, repeats: int) -> dict:
    t0 = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(LLM_ID, revision=LLM_REV)
    model = AutoModelForCausalLM.from_pretrained(LLM_ID, revision=LLM_REV, dtype=dtype).eval()
    load_s = time.perf_counter() - t0
    prompt = f"Text extras din factură:\n{reading_order_text(words)}\n\n{QUESTION}\n{LLM_INSTRUCTION}"
    inputs = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], add_generation_prompt=True, return_tensors="pt", return_dict=True
    )
    runs = []
    for _ in range(repeats):
        t1 = time.perf_counter()
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=32, do_sample=False)
        runs.append(time.perf_counter() - t1)
    text = tokenizer.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    answer, _ = gold(words)
    return {
        "model": LLM_ID, "revision": LLM_REV, "dtype": str(dtype),
        "input_tokens": int(inputs["input_ids"].shape[1]), "load_seconds": round(load_s, 1),
        "generate_seconds": [round(r, 1) for r in runs], "peak_rss_gb": round(rss_gb(), 1),
        "raw_output": text, "gold_answer": answer,
        "answer_correct": parse_json(text).get("answer", "").strip() == answer,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--which", choices=["vlm", "llm"], required=True)
    parser.add_argument("--dtype", choices=["float32", "bfloat16"], default="float32")
    parser.add_argument("--max-pixels", type=int, nargs="+", default=[512 * 28 * 28, 1280 * 28 * 28])
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()

    dtype = getattr(torch, args.dtype)
    words = json.loads((SMOKE / "invoice.json").read_text(encoding="utf-8"))["words"]
    results = (
        [bench_vlm(SMOKE / "invoice.png", words, mp, dtype, args.repeats) for mp in args.max_pixels]
        if args.which == "vlm" else [bench_llm(words, dtype, args.repeats)]
    )
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "machine": {"cpu": platform.processor(), "logical_cpus": psutil.cpu_count(),
                    "ram_gb": round(psutil.virtual_memory().total / 2**30), "torch_threads": torch.get_num_threads()},
        "versions": {"torch": torch.__version__, "transformers": transformers.__version__},
        "results": results,
    }
    out = ROOT / "runs" / "benchmark" / f"{args.which}-{args.dtype}-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
