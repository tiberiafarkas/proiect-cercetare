"""Run the vision-language model (F4) on the E3 stimuli; resumable, raw outputs only."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from cuebind.models import VLM_ID, VLM_MAX_PIXELS, VLM_REV, VisionModel
from cuebind.runio import done_keys, load_jsonl

ROOT = Path(__file__).resolve().parents[1]
E3_QUESTIONS = {
    "P1": "Care este data emiterii acestei facturi?",
    "P2": "Când a fost emisă această factură?",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=Path, default=ROOT / "data" / "generated" / "e3" / "items.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "runs" / "pilot" / "e3_F4.jsonl")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    items = load_jsonl(args.items)[: args.limit]
    done = done_keys(args.out)
    todo = [(item, p) for item in items for p in E3_QUESTIONS if (item["item_id"], p) not in done]
    print(f"E3: {len(todo)} queries to run ({len(done)} already done)", flush=True)
    if not todo:
        return
    model = VisionModel()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with args.out.open("a", encoding="utf-8") as fh:
        for n, (item, paraphrase) in enumerate(todo, 1):
            gen = model.generate(str(args.items.parent / item["image"]), E3_QUESTIONS[paraphrase])
            fh.write(json.dumps({
                "item_id": item["item_id"], "paraphrase": paraphrase, "condition": "F4", "model": VLM_ID,
                "revision": VLM_REV, "max_pixels": VLM_MAX_PIXELS, "raw_output": gen.raw_output,
                "input_tokens": gen.input_tokens, "seconds": gen.seconds, "resized_image": gen.resized_image,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }, ensure_ascii=False) + "\n")
            fh.flush()
            if n % 10 == 0 or n == len(todo):
                rate = (time.perf_counter() - started) / n
                print(f"E3: {n}/{len(todo)} done, {rate:.1f} s/query, about {rate * (len(todo) - n) / 60:.0f} min left",
                      flush=True)


if __name__ == "__main__":
    main()
