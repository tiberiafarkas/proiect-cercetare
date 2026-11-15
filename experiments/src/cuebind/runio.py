"""Shared helpers for resumable model runs that append raw outputs to JSONL files."""

from __future__ import annotations

import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    """Records of a JSONL file. A truncated last line (from a run stopped while writing) is ignored."""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = []
    for i, line in enumerate(lines):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            if i != len(lines) - 1:
                raise
    return records


def done_keys(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    return {(r["item_id"], r["paraphrase"]) for r in load_jsonl(path)}


def repair(path: Path) -> None:
    """Remove a truncated last line so that appended records start on a new line."""
    if not path.exists():
        return
    records = load_jsonl(path)
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    if text != path.read_text(encoding="utf-8"):
        path.write_text(text, encoding="utf-8")
