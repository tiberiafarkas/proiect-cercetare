"""E3 analysis: cited instance, overlap correctness and responses to edits (report, Section 3.4)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from cuebind.runio import load_jsonl
from cuebind.scoring import coverage, iou, normalize, parse_json

COVERAGE_THRESHOLD = 0.5
IOU_THRESHOLD = 0.5


def to_page_box(box: list[float], resized: list[int], width: int, height: int) -> list[float]:
    """Qwen2.5-VL returns pixels of the resized input; convert them to pixels of the rendered page."""
    sx, sy = width / resized[0], height / resized[1]
    return [box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy]


def cited_instance(box: list[float] | None, instances: dict[str, list[float]]) -> str:
    if box is None:
        return "no_box"
    scores = {name: coverage(box, b) for name, b in instances.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= COVERAGE_THRESHOLD else "none"


def response(raw_output: str, original: str, new_date: str) -> tuple[str, list[float] | None]:
    parsed = parse_json(raw_output)
    if parsed is None or not isinstance(parsed.get("answer"), str):
        return "invalid", None
    box = parsed.get("bbox_2d")
    box = box if isinstance(box, list) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box) else None
    answer = normalize(parsed["answer"])
    if answer == normalize(new_date):
        return "follows_edit", box
    if answer == normalize(original):
        return "retains", box
    return "other", box


def score(items_path: Path, run_path: Path) -> pd.DataFrame:
    items = {r["item_id"]: r for r in load_jsonl(items_path)}
    rows = []
    for run in load_jsonl(run_path):
        item = items[run["item_id"]]
        category, box = response(run["raw_output"], item["original"], item["new_date"])
        page_box = to_page_box(box, run["resized_image"], item["width"], item["height"]) if box else None
        rows.append({
            "base_id": item["base_id"], "kind": item["kind"], "variant": item["variant"],
            "paraphrase": run["paraphrase"], "category": category, "box": page_box,
            "edit_confined": item["edit_confined"], "raw_output": run["raw_output"],
            "instance_boxes": item["instance_boxes"],
        })
    return pd.DataFrame(rows)


def per_query(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (invoice, paraphrase): the original citation and the responses to I1, I2, U and masking."""
    out = []
    for (base, paraphrase), g in df.groupby(["base_id", "paraphrase"]):
        v = g.set_index("variant")
        orig = v.loc["original"]
        instances = {k: orig.instance_boxes[k] for k in ("meta", "dup")}
        cited = cited_instance(orig.box, instances)
        row = {
            "base_id": base, "kind": orig.kind, "paraphrase": paraphrase,
            "original_category": orig.category, "cited": cited,
            "iou_meta": iou(orig.box, instances["meta"]) if orig.box else np.nan,
            "overlap_correct": bool(orig.box) and iou(orig.box, instances["meta"]) >= IOU_THRESHOLD,
            "U": v.loc["sub_unrelated"].category, "mask_all": v.loc["mask_all"].category,
        }
        if cited in ("meta", "dup"):
            other = "dup" if cited == "meta" else "meta"
            row.update({"I1": v.loc[f"sub_{cited}"].category, "I2": v.loc[f"sub_{other}"].category,
                        "mask_cited": v.loc[f"mask_{cited}"].category, "mask_other": v.loc[f"mask_{other}"].category})
        out.append(row)
    return pd.DataFrame(out)


def rates(q: pd.DataFrame, replicates: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Share of each response per edit, among queries whose original answer was correct and box cited an instance."""
    eligible = q[(q.original_category == "retains") & q.cited.isin(["meta", "dup"])]
    rng = np.random.default_rng(seed)
    rows = []
    for kind, g in [("all", eligible)] + list(eligible.groupby("kind")):
        bases = g.base_id.unique()
        for edit in ("I1", "I2", "U", "mask_cited", "mask_other", "mask_all"):
            for cat in ("follows_edit", "retains"):
                if edit.startswith("mask") and cat == "follows_edit":
                    continue
                share = lambda frame: (frame[edit] == cat).mean() if len(frame) else np.nan  # noqa: E731
                boots = [share(pd.concat([g[g.base_id == b] for b in rng.choice(bases, len(bases))]))
                         for _ in range(replicates)] if len(bases) else [np.nan]
                lo, hi = np.nanquantile(boots, [0.025, 0.975]) if len(bases) else (np.nan, np.nan)
                rows.append({"kind": kind, "edit": edit, "response": cat, "n": len(g), "bases": len(bases),
                             "rate": share(g), "lo": lo, "hi": hi})
    return pd.DataFrame(rows)


def crosstab(q: pd.DataFrame) -> pd.DataFrame:
    """Overlap-correct citations against the response to substituting the cited and the non-cited instance."""
    eligible = q[(q.original_category == "retains") & q.cited.isin(["meta", "dup"])]
    return pd.crosstab([eligible.overlap_correct, eligible.I1], eligible.I2, margins=True)
