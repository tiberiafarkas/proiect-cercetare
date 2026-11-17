"""Score the SROIE transfer tests (report, Section 5.2) from the stored raw outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from cuebind.e3_analysis import cited_instance, to_page_box
from cuebind.runio import load_jsonl
from cuebind.scoring import parse_json
from cuebind.sroie import is_correct, load_test_split

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "sroie"


def interval(values: np.ndarray, replicates: int, seed: int = 0) -> tuple[float, float]:
    """95% percentile bootstrap interval of a mean over receipts."""
    if len(values) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = [values[rng.integers(0, len(values), len(values))].mean() for _ in range(replicates)]
    return tuple(np.quantile(means, [0.025, 0.975]))


def answer_of(raw: str) -> str:
    parsed = parse_json(raw) or {}
    answer = parsed.get("answer")
    return answer if isinstance(answer, str) else ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicates", type=int, default=2000)
    args = parser.parse_args()
    receipts = {r.key: r for r in load_test_split()}
    out = RUNS / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in sorted(RUNS.glob("competence_F*.jsonl")):
        for run in load_jsonl(path):
            gold = receipts[run["item_id"]].entities[run["paraphrase"]]
            rows.append({"condition": run["condition"], "receipt": run["item_id"], "field": run["paraphrase"],
                         "answer": answer_of(run["raw_output"]), "gold": gold,
                         "correct": is_correct(run["paraphrase"], answer_of(run["raw_output"]), gold)})
    competence = pd.DataFrame(rows)
    competence.to_csv(out / "competence_scored.csv", index=False)
    summary = []
    for (condition, field), g in competence.groupby(["condition", "field"]):
        lo, hi = interval(g.correct.to_numpy(dtype=float), args.replicates)
        summary.append({"condition": condition, "field": field, "n": len(g), "accuracy": g.correct.mean(),
                        "lo": lo, "hi": hi})
    summary = pd.DataFrame(summary)
    summary.to_csv(out / "competence_summary.csv", index=False, float_format="%.3f")
    print(summary.to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    removal_path = RUNS / "removal_F4.jsonl"
    if not removal_path.exists():
        return
    runs = load_jsonl(removal_path)
    by_receipt: dict[str, dict] = {}
    for run in runs:
        by_receipt.setdefault(run["item_id"], {})[run["paraphrase"]] = run
    rows = []
    for key, variants in by_receipt.items():
        if "original" not in variants:
            continue
        receipt, original = receipts[key], variants["original"]
        gold = receipt.entities["total"]
        box = (parse_json(original["raw_output"]) or {}).get("bbox_2d")
        valid = isinstance(box, list) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box)
        page_box = to_page_box(box, original["resized_image"], receipt.width, receipt.height) if valid else None
        row = {"receipt": key, "instances": len(original["instances"]),
               "original_correct": is_correct("total", answer_of(original["raw_output"]), gold),
               "cited": cited_instance(page_box, original["instances"])}
        for variant in ("mask_cited", "mask_all", "mask_random"):
            run = variants.get(variant)
            row[variant] = None if run is None else is_correct("total", answer_of(run["raw_output"]), gold)
        rows.append(row)
    removal = pd.DataFrame(rows)
    removal.to_csv(out / "removal_scored.csv", index=False)
    eligible = removal[removal.original_correct]
    result = {"receipts": len(removal), "original_correct": int(removal.original_correct.sum()),
              "cited_an_instance": int(eligible.cited.str.startswith("i").sum())}
    for variant in ("mask_cited", "mask_all", "mask_random"):
        values = eligible[variant].dropna().astype(float).to_numpy()
        lo, hi = interval(values, args.replicates)
        result[variant] = {"n": len(values), "answer_kept": float(values.mean()) if len(values) else None,
                           "lo": lo, "hi": hi}
    (out / "removal_summary.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
