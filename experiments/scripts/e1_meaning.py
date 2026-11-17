"""E1 meaning-level rates from the checked classification of the repeated cases (report, Section 5.2).

For each dataset and field, the share of sampled repeated cases with a strict or loose copy is scaled
by the string-level repetition rate, which estimates the share of all documents with such a copy.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "runs" / "e1"


def main() -> None:
    summary = json.loads((E1 / "summary.json").read_text(encoding="utf-8"))
    string_rates = {}
    for name, fields in summary.items():
        string_rates[name.split()[0]] = {f: v["repeated_rate"] for f, v in fields.items()}
    result = {}
    for path in sorted(E1.glob("*_repeats_sample.csv")):
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        dataset = rows[0]["dataset"]
        checked = [r for r in rows if r["checked_by_author"].strip().lower() == "yes"]
        changed = sum(r["copy"] != r["draft_copy"] or r["other_kinds"] != r["draft_other_kinds"] for r in checked)
        by_field = {}
        for field in sorted({r["field"] for r in checked}):
            g = [r for r in checked if r["field"] == field]
            copies = Counter(r["copy"] for r in g)
            kinds = Counter(k for r in g for k in r["other_kinds"].split(";") if k)
            share = (copies["strict"] + copies["loose"]) / len(g)
            by_field[field] = {
                "cases": len(g), "copy": dict(copies), "other_kinds": dict(kinds),
                "share_with_copy": round(share, 3),
                "share_with_strict_copy": round(copies["strict"] / len(g), 3),
                "estimated_documents_with_copy": round(share * string_rates[dataset][field], 3),
                "estimated_documents_with_strict_copy": round(copies["strict"] / len(g) * string_rates[dataset][field], 3),
            }
        result[dataset] = {"sampled": len(rows), "checked": len(checked), "drafts_changed": changed, "by_field": by_field}
    (E1 / "meaning_summary.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
