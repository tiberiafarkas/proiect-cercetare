"""Transfer tests on SROIE receipts (report, Section 5.3); resumable, raw outputs only.

--part competence: conditions F1, F2 and F4 answer the date and the total of a random sample of receipts.
--part removal:    F4 answers the total of receipts on which the total occurs at least twice, then the same
                   receipt with the cited occurrence masked, with every occurrence masked, and with a
                   same-size random region masked.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from cuebind.e3_analysis import cited_instance, to_page_box
from cuebind.models import LLM_ID, LLM_REV, VLM_ID, VLM_REV
from cuebind.runio import done_keys, load_jsonl, repair
from cuebind.scoring import parse_json
from cuebind.sroie import (F1_HEADER, F2_HEADER, QUESTIONS, load_test_split, mask, random_control_box, sample,
                           total_instances)
from cuebind.text import plain_text, text_with_boxes

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "data" / "generated" / "sroie"
OUT = ROOT / "runs" / "sroie"
COMPETENCE_N, COMPETENCE_SEED = 60, 0
REMOVAL_N, REMOVAL_SEED = 30, 1


def record(key: str, slot: str, condition: str, gen, extra: dict | None = None) -> dict:
    return {
        "item_id": key, "paraphrase": slot, "condition": condition,
        "model": VLM_ID if condition == "F4" else LLM_ID, "revision": VLM_REV if condition == "F4" else LLM_REV,
        "raw_output": gen.raw_output, "input_tokens": gen.input_tokens, "seconds": gen.seconds,
        "resized_image": gen.resized_image, "timestamp": datetime.now().isoformat(timespec="seconds"),
        **(extra or {}),
    }


def competence(condition: str, receipts) -> None:
    out = OUT / f"competence_{condition}.jsonl"
    repair(out)
    chosen = sample(receipts, COMPETENCE_N, COMPETENCE_SEED)
    done = done_keys(out)
    todo = [(r, f) for r in chosen for f in QUESTIONS if (r.key, f) not in done]
    print(f"competence {condition}: {len(todo)} queries ({len(done)} done)", flush=True)
    if not todo:
        return
    if condition == "F4":
        from cuebind.models import VisionModel
        model = VisionModel()
    else:
        from cuebind.models import TextModel
        model = TextModel()
    started = time.perf_counter()
    with out.open("a", encoding="utf-8") as fh:
        for n, (receipt, field) in enumerate(todo, 1):
            if condition == "F4":
                gen = model.generate(str(receipt.save_image(IMAGES / f"{receipt.key}.png")), QUESTIONS[field])
            elif condition == "F1":
                gen = model.generate(model.prompt(F1_HEADER, plain_text(receipt.words()), QUESTIONS[field]))
            else:
                text = text_with_boxes(receipt.words(), receipt.width, receipt.height)
                gen = model.generate(model.prompt(F2_HEADER, text, QUESTIONS[field]))
            fh.write(json.dumps(record(receipt.key, field, condition, gen), ensure_ascii=False) + "\n")
            fh.flush()
            if n % 10 == 0 or n == len(todo):
                rate = (time.perf_counter() - started) / n
                print(f"competence {condition}: {n}/{len(todo)}, {rate:.1f} s/query, "
                      f"about {rate * (len(todo) - n) / 60:.0f} min left", flush=True)


def removal(receipts) -> None:
    from cuebind.models import VisionModel

    out = OUT / "removal_F4.jsonl"
    repair(out)
    chosen = sample(receipts, REMOVAL_N, REMOVAL_SEED, lambda r: len(total_instances(r)) >= 2)
    done = {(r["item_id"], r["paraphrase"]): r for r in load_jsonl(out)} if out.exists() else {}
    print(f"removal: {len(chosen)} receipts ({len(done)} queries already done)", flush=True)
    model = None
    started, count = time.perf_counter(), 0
    with out.open("a", encoding="utf-8") as fh:
        def run(receipt, slot: str, image: Path, extra: dict) -> dict:
            nonlocal model, count
            if (receipt.key, slot) in done:
                return done[(receipt.key, slot)]
            model = model or VisionModel()
            rec = record(receipt.key, slot, "F4", model.generate(str(image), QUESTIONS["total"]), extra)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            done[(receipt.key, slot)] = rec
            count += 1
            return rec

        for i, receipt in enumerate(chosen, 1):
            instances = total_instances(receipt)
            named = {f"i{k}": b for k, b in enumerate(instances)}
            original = run(receipt, "original", receipt.save_image(IMAGES / f"{receipt.key}.png"),
                           {"instances": named})
            parsed = parse_json(original["raw_output"]) or {}
            box = parsed.get("bbox_2d")
            ok = isinstance(box, list) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box)
            page_box = to_page_box(box, original["resized_image"], receipt.width, receipt.height) if ok else None
            cited = cited_instance(page_box, named)
            if cited in named:
                run(receipt, "mask_cited", mask(receipt, [named[cited]], IMAGES / f"{receipt.key}-mask_cited.png"),
                    {"cited": cited, "masked": [named[cited]]})
            run(receipt, "mask_all", mask(receipt, instances, IMAGES / f"{receipt.key}-mask_all.png"),
                {"cited": cited, "masked": instances})
            like = named.get(cited, instances[0])
            control = random_control_box(receipt, like, instances, seed=i)
            if control:
                run(receipt, "mask_random", mask(receipt, [control], IMAGES / f"{receipt.key}-mask_random.png"),
                    {"cited": cited, "masked": [control]})
            if count:
                rate = (time.perf_counter() - started) / count
                print(f"removal: receipt {i}/{len(chosen)}, {rate:.1f} s/query", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["competence", "removal"], required=True)
    parser.add_argument("--condition", choices=["F1", "F2", "F4"], default="F4")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    receipts = load_test_split()
    if args.part == "competence":
        competence(args.condition, receipts)
    else:
        removal(receipts)


if __name__ == "__main__":
    main()
