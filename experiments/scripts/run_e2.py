"""Run one model condition on the E2 stimuli and append raw outputs to a JSONL file.

The run is resumable: (item_id, paraphrase) pairs already present in the output are skipped.
Scoring is done separately (scripts/score_e2.py) from the stored raw outputs.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from cuebind.models import F1_CONTEXT, F2_CONTEXT, LLM_ID, LLM_REV, QUESTIONS, VLM_ID, VLM_MAX_PIXELS, VLM_REV
from cuebind.render import Word
from cuebind.runio import done_keys, load_jsonl
from cuebind.text import plain_text, text_with_boxes

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=["F1", "F2", "F4"], required=True)
    parser.add_argument("--items", type=Path, default=ROOT / "data" / "generated" / "pilot" / "items.jsonl")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "runs" / "pilot")
    parser.add_argument("--limit", type=int, default=None, help="only the first N items (smoke test)")
    args = parser.parse_args()

    items = load_jsonl(args.items)[: args.limit]
    out = args.out_dir / f"e2_{args.condition}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = done_keys(out)
    todo = [(item, p) for item in items for p in QUESTIONS if (item["item_id"], p) not in done]
    print(f"{args.condition}: {len(todo)} queries to run ({len(done)} already done)", flush=True)
    if not todo:
        return

    if args.condition == "F4":
        from cuebind.models import VisionModel
        model, model_id, revision = VisionModel(), VLM_ID, VLM_REV
    else:
        from cuebind.models import TextModel
        model, model_id, revision = TextModel(), LLM_ID, LLM_REV

    started = time.perf_counter()
    with out.open("a", encoding="utf-8") as fh:
        for n, (item, paraphrase) in enumerate(todo, 1):
            question = QUESTIONS[paraphrase]
            if args.condition == "F4":
                gen = model.generate(str(args.items.parent / item["image"]), question)
            else:
                words = [Word(w["text"], tuple(w["box"]), w["field"], w["role"], w["instance"]) for w in item["words"]]
                if args.condition == "F1":
                    document = plain_text(words)
                    header = F1_CONTEXT
                else:
                    document = text_with_boxes(words, item["width"], item["height"])
                    header = F2_CONTEXT
                gen = model.generate(model.prompt(header, document, question))
            record = {
                "item_id": item["item_id"], "paraphrase": paraphrase, "condition": args.condition,
                "model": model_id, "revision": revision,
                "max_pixels": VLM_MAX_PIXELS if args.condition == "F4" else None,
                "raw_output": gen.raw_output, "input_tokens": gen.input_tokens, "seconds": gen.seconds,
                "resized_image": gen.resized_image, "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            if n % 10 == 0 or n == len(todo):
                rate = (time.perf_counter() - started) / n
                print(f"{args.condition}: {n}/{len(todo)} done, {rate:.1f} s/query, "
                      f"about {rate * (len(todo) - n) / 60:.0f} min left", flush=True)


if __name__ == "__main__":
    main()
