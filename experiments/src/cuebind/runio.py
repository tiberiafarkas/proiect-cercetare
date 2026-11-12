"""Shared helpers for resumable model runs that append raw outputs to JSONL files."""

from __future__ import annotations

import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def done_keys(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    return {(r["item_id"], r["paraphrase"]) for r in load_jsonl(path)}
