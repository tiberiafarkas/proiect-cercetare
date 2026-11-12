"""Score the stored E2 raw outputs and write the analysis tables to runs/pilot/analysis."""

import argparse
from pathlib import Path

from cuebind.analysis import label_form_effects, score, summarize

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=Path, default=ROOT / "data" / "generated" / "pilot" / "items.jsonl")
    parser.add_argument("--runs", type=Path, default=ROOT / "runs" / "pilot")
    parser.add_argument("--replicates", type=int, default=2000)
    args = parser.parse_args()

    run_paths = sorted(args.runs.glob("e2_F*.jsonl"))
    df = score(args.items, run_paths)
    out = args.runs / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "e2_scored.csv", index=False, encoding="utf-8")
    summary = summarize(df, args.replicates)
    summary.to_csv(out / "e2_summary.csv", index=False, float_format="%.3f")
    effects = label_form_effects(df, args.replicates)
    effects.to_csv(out / "e2_label_form_effects.csv", index=False, float_format="%.3f")
    print(f"Scored {len(df)} answers from {[p.name for p in run_paths]}")
    print(summary[["condition_model", "conflict", "label_form", "queries", "control_accuracy", "F_A", "D"]]
          .to_string(index=False, float_format=lambda v: f"{v:.2f}"))


if __name__ == "__main__":
    main()
