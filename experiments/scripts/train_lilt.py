"""Fine-tune LiLT (F3) on control invoices from the training templates, then answer the E2 pilot items.

Outputs: runs/lilt/train_log.json (loss and validation accuracy per epoch) and runs/pilot/e2_F3.jsonl
(one answer per pilot item, in the same format as the other conditions, with paraphrase "P0").
The fine-tuned weights are kept in the local cache, outside the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import datetime
from pathlib import Path

import torch

from cuebind.lilt import LILT_ID, LILT_REV, TAGS, due_date_answer, encode, generate_training, word_tags
from cuebind.render import Word
from cuebind.runio import load_jsonl

ROOT = Path(__file__).resolve().parents[1]
TRAIN_DIR = ROOT / "data" / "generated" / "lilt_train"
WEIGHTS = Path(os.environ.get("LOCALAPPDATA", ".")) / "cuebind" / "lilt-f3"


def words_of(doc: dict) -> list[Word]:
    return [Word(w["text"], tuple(w["box"]), w["field"], w["role"], w["instance"]) for w in doc["words"]]


def due_date_accuracy(model, tokenizer, docs: list[dict]) -> float:
    model.eval()
    correct = 0
    for doc in docs:
        words = words_of(doc)
        gold = " ".join(w.text for w in words if w.field == "due_date" and w.role == "value")
        answer, _ = due_date_answer(model, tokenizer, words, doc["width"], doc["height"])
        correct += answer == gold
    return correct / len(docs)


def main() -> None:
    from transformers import AutoTokenizer, LiltForTokenClassification

    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smoke", action="store_true",
                        help="8 training and 4 validation documents, 1 epoch, 4 pilot items; writes nothing to runs/")
    args = parser.parse_args()
    torch.manual_seed(args.seed)

    manifest = TRAIN_DIR / "docs.jsonl"
    if not manifest.exists():
        generate_training(TRAIN_DIR)
    docs = load_jsonl(manifest)
    train = [d for d in docs if d["split"] == "train"]
    val = [d for d in docs if d["split"] == "val"]
    if args.smoke:
        train, val, args.epochs = train[:8], val[:4], 1
    print(f"training documents: {len(train)}, validation documents: {len(val)}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(LILT_ID, revision=LILT_REV)
    model = LiltForTokenClassification.from_pretrained(
        LILT_ID, revision=LILT_REV, num_labels=len(TAGS),
        id2label=dict(enumerate(TAGS)), label2id={t: i for i, t in enumerate(TAGS)})
    examples = []
    for doc in train:
        words = words_of(doc)
        enc = encode(tokenizer, words, doc["width"], doc["height"], word_tags(words))
        enc.pop("word_ids")
        examples.append(enc)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = args.epochs * ((len(examples) + args.batch - 1) // args.batch)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda s: max(0.0, 1 - s / steps))
    log, rng, started = [], random.Random(args.seed), time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        model.train()
        rng.shuffle(examples)
        losses = []
        for start in range(0, len(examples), args.batch):
            batch = examples[start:start + args.batch]
            length = max(e["input_ids"].shape[1] for e in batch)

            def pad(key: str, value) -> torch.Tensor:
                rows = []
                for e in batch:
                    t = e[key][0]
                    fill = torch.full((length - t.shape[0], *t.shape[1:]), value, dtype=t.dtype)
                    rows.append(torch.cat([t, fill]))
                return torch.stack(rows)

            inputs = {"input_ids": pad("input_ids", tokenizer.pad_token_id), "attention_mask": pad("attention_mask", 0),
                      "bbox": pad("bbox", 0), "labels": pad("labels", -100)}
            loss = model(**inputs).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            losses.append(loss.item())
        accuracy = due_date_accuracy(model, tokenizer, val)
        log.append({"epoch": epoch, "mean_loss": sum(losses) / len(losses), "val_due_date_accuracy": accuracy,
                    "minutes": round((time.perf_counter() - started) / 60, 1)})
        print(json.dumps(log[-1]), flush=True)

    if args.smoke:
        model.eval()
        for item in load_jsonl(ROOT / "data" / "generated" / "pilot" / "items.jsonl")[:4]:
            print(item["item_id"], due_date_answer(model, tokenizer, words_of(item), item["width"], item["height"]))
        return

    WEIGHTS.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(WEIGHTS)
    tokenizer.save_pretrained(WEIGHTS)
    out_log = ROOT / "runs" / "lilt" / "train_log.json"
    out_log.parent.mkdir(parents=True, exist_ok=True)
    out_log.write_text(json.dumps({"model": LILT_ID, "revision": LILT_REV, "train_documents": len(train),
                                   "validation_documents": len(val), "args": vars(args), "epochs": log},
                                  indent=1), encoding="utf-8")

    model.eval()
    items = load_jsonl(ROOT / "data" / "generated" / "pilot" / "items.jsonl")
    with (ROOT / "runs" / "pilot" / "e2_F3.jsonl").open("w", encoding="utf-8") as fh:
        for item in items:
            t0 = time.perf_counter()
            answer, confidence = due_date_answer(model, tokenizer, words_of(item), item["width"], item["height"])
            fh.write(json.dumps({
                "item_id": item["item_id"], "paraphrase": "P0", "condition": "F3", "model": LILT_ID,
                "revision": LILT_REV, "raw_output": json.dumps({"answer": answer or ""}, ensure_ascii=False),
                "confidence": round(confidence, 4), "seconds": round(time.perf_counter() - t0, 2),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }, ensure_ascii=False) + "\n")
    print(f"F3 answers written for {len(items)} pilot items", flush=True)


if __name__ == "__main__":
    main()
