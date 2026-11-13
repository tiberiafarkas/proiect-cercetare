"""Score the stored E3 raw outputs and write the analysis tables to runs/pilot/analysis."""

import argparse
from pathlib import Path

from cuebind.e3_analysis import crosstab, per_query, rates, score

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=Path, default=ROOT / "data" / "generated" / "e3" / "items.jsonl")
    parser.add_argument("--run", type=Path, default=ROOT / "runs" / "pilot" / "e3_F4.jsonl")
    parser.add_argument("--replicates", type=int, default=2000)
    args = parser.parse_args()

    df = score(args.items, args.run)
    q = per_query(df)
    out = ROOT / "runs" / "pilot" / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    q.to_csv(out / "e3_per_query.csv", index=False)
    r = rates(q, args.replicates)
    r.to_csv(out / "e3_rates.csv", index=False, float_format="%.3f")
    ct = crosstab(q)
    ct.to_csv(out / "e3_crosstab.csv")
    print(f"{len(df)} answers, {len(q)} invoice-paraphrase queries; cited instance: {q.cited.value_counts().to_dict()}")
    print(r.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    print(ct)


if __name__ == "__main__":
    main()
