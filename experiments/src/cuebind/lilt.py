"""Condition F3: LiLT with the InfoXLM text encoder, fine-tuned as a field tagger (report, Section 3.3).

LiLT sees the oracle words and their boxes, not the image. It is trained only on control invoices rendered
from separate training templates, and it answers the due-date "question" by tagging the due-date span.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path

import torch

from cuebind.conflicts import Condition, Conflict
from cuebind.generator import environment, render_html
from cuebind.labels import FIELDS, LabelForm
from cuebind.render import Renderer, Word

LILT_ID, LILT_REV = "SCUT-DLVCLab/lilt-infoxlm-base", "9f07474e82c0b3fd1a0a8506fa68a10ef5101dd4"
TRAIN_TEMPLATES = ("t05_mono", "t06_sidebar", "t07_boxed_grid")
# Control layouts only: label-value rows (control of C1, C2, C4) and stacked pairs (control of C3).
TRAIN_LAYOUTS = (Conflict.C1, Conflict.C3)
TAGS = ["O"] + [f"{p}-{f}" for f in FIELDS for p in ("B", "I")]
TAG_ID = {t: i for i, t in enumerate(TAGS)}
MAX_LEN = 512


def word_tags(words: list[Word]) -> list[str]:
    tags, previous = [], None
    for w in words:
        field = w.field if w.role == "value" and w.field in FIELDS else None
        if field is None:
            tags.append("O")
        else:
            key = (field, w.instance)
            tags.append(("I-" if key == previous else "B-") + field)
        previous = (field, w.instance) if field else None
    return tags


def training_design(per_cell: int, master_seed: int, split: str) -> Iterator[tuple[str, int, Conflict, LabelForm, str]]:
    for template in TRAIN_TEMPLATES:
        for layout in TRAIN_LAYOUTS:
            for form in LabelForm:
                for i in range(per_cell):
                    digest = hashlib.sha256(f"{master_seed}:{split}:{template}:{layout}:{form}:{i}".encode())
                    seed = int(digest.hexdigest()[:12], 16)
                    yield template, seed, layout, form, f"{split}-{template}-{layout}-{form}-{i:02d}"


def generate_training(out_dir: Path, per_cell: int = 12, val_per_cell: int = 2, master_seed: int = 20261115) -> Path:
    env = environment()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "docs.jsonl"
    with Renderer() as renderer, manifest.open("w", encoding="utf-8") as fh:
        for split, n in (("train", per_cell), ("val", val_per_cell)):
            for template, seed, layout, form, doc_id in training_design(n, master_seed, split):
                html, _ = render_html(env, template, seed, layout, form, Condition.CONTROL)
                page = renderer.render(html, out_dir / "images" / f"{doc_id}.png")
                fh.write(json.dumps({"doc_id": doc_id, "split": split, "template": template, "layout": str(layout),
                                     "label_form": str(form), "width": page.width, "height": page.height,
                                     "words": [asdict(w) for w in page.words]}, ensure_ascii=False) + "\n")
    return manifest


def encode(tokenizer, words: list[Word], width: int, height: int, tags: list[str] | None = None) -> dict:
    """Tokenize words with their boxes (0-1000); the tokenizer labels only the first sub-token of each word."""

    def norm(box: tuple[float, ...]) -> list[int]:
        x0, y0, x1, y1 = box
        return [min(1000, max(0, round(1000 * x0 / width))), min(1000, max(0, round(1000 * y0 / height))),
                min(1000, max(0, round(1000 * x1 / width))), min(1000, max(0, round(1000 * y1 / height)))]

    enc = tokenizer([w.text for w in words], boxes=[norm(w.box) for w in words],
                    word_labels=[TAG_ID[t] for t in tags] if tags is not None else None,
                    truncation=True, max_length=MAX_LEN, return_tensors="pt")
    enc["word_ids"] = enc.word_ids(0)
    return enc


def due_date_answer(model, tokenizer, words: list[Word], width: int, height: int) -> tuple[str | None, float]:
    """The due-date span with the highest mean probability, read from the first sub-token of each word."""
    enc = encode(tokenizer, words, width, height)
    word_ids = enc.pop("word_ids")
    with torch.inference_mode():
        probs = model(**{k: v for k, v in enc.items()}).logits.softmax(-1)[0]
    b, i = TAG_ID["B-due_date"], TAG_ID["I-due_date"]
    first = {}
    for pos, w in enumerate(word_ids):
        if w is not None and w not in first:
            first[w] = pos
    spans, current = [], []
    for w in sorted(first):
        p = probs[first[w]]
        tag = int(p.argmax())
        if tag == b or (tag == i and not current):
            if current:
                spans.append(current)
            current = [(w, float(p[b] + p[i]))]
        elif tag == i:
            current.append((w, float(p[b] + p[i])))
        elif current:
            spans.append(current)
            current = []
    if current:
        spans.append(current)
    if not spans:
        return None, 0.0
    best = max(spans, key=lambda s: sum(x for _, x in s) / len(s))
    return " ".join(words[w].text for w, _ in best), sum(x for _, x in best) / len(best)
