"""E1 audit: repetition of answer values on SROIE (test split) and FATURA pages.

Writes summaries and samples of repeated cases (with context) for the manual same-fact/collision check
to runs/e1/. Datasets are downloaded to a local cache outside the repository.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from cuebind.e1 import occurrences, parse_value

ROOT = Path(__file__).resolve().parents[1]
SROIE_REPO, SROIE_REV = "jsdnrs/ICDAR2019-SROIE", "bffe40c26759f3376ec2b3ae9031dbba54cd587c"


def audit_sroie(out: Path, sample_size: int, seed: int) -> dict:
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(SROIE_REPO, "data/test-00000-of-00001.parquet", repo_type="dataset", revision=SROIE_REV)
    rows = pq.read_table(path, columns=["key", "entities", "words"]).to_pylist()
    summary, repeated = {}, []
    for field in ("date", "total"):
        counts, not_found, unparsable = Counter(), 0, 0
        for r in rows:
            value = parse_value(field, r["entities"][field] or "")
            if value is None:
                unparsable += 1
                continue
            hits = occurrences(field, value, r["words"])
            if not hits:
                not_found += 1
                continue
            counts[min(len(hits), 5)] += 1
            if len(hits) > 1:
                context = [f"{r['words'][i - 1] if i > 0 else ''} | {r['words'][i]}" for i in hits]
                repeated.append({"dataset": "SROIE", "document": r["key"], "field": field,
                                 "value": r["entities"][field], "occurrences": len(hits),
                                 "contexts": " || ".join(context), "manual_label": ""})
        found = sum(counts.values())
        summary[field] = {
            "documents": len(rows), "value_unparsable": unparsable, "value_not_found_in_ocr": not_found,
            "value_found": found, "repeated": found - counts[1],
            "repeated_rate": (found - counts[1]) / found if found else None,
            "occurrence_distribution": {("5+" if k == 5 else str(k)): v for k, v in sorted(counts.items())},
        }
    random.Random(seed).shuffle(repeated)
    _write_sample(out / "sroie_repeats_sample.csv", repeated[:sample_size])
    return summary


FATURA_FIELDS = {"date": ["DATE"], "due_date": ["DUE_DATE"], "total": ["TOTAL", "AMOUNT_DUE"]}


def audit_fatura(archive: Path, out: Path, sample_size: int, seed: int) -> dict:
    """FATURA test split (strategy 1); values come from the field annotations, page text from 'OTHER'."""
    import zipfile

    from cuebind.e1 import amounts, parse_fatura_date

    prefix = "invoices_dataset_final/"
    with zipfile.ZipFile(archive) as z:
        split = z.read(prefix + "strat1_test.csv").decode("utf-8").splitlines()
        names = sorted({Path(line.split(",")[0]).stem for line in split[1:] if line.strip()})
        documents = []
        for name in names:
            member = f"{prefix}Annotations/Original_Format/{name}.json"
            try:
                documents.append((name, json.loads(z.read(member))))
            except KeyError:
                continue
    summary, repeated = {}, []
    for field, keys in FATURA_FIELDS.items():
        counts, absent, unparsable, not_found = Counter(), 0, 0, 0
        for name, ann in documents:
            entry = next((ann[k] for k in keys if isinstance(ann.get(k), dict) and ann[k].get("text")), None)
            if entry is None:
                absent += 1
                continue
            text = entry["text"].split(":", 1)[-1]
            if field == "total":
                found = amounts(text)
                value = found[-1] if found else None
            else:
                value = parse_fatura_date(text)
            if value is None:
                unparsable += 1
                continue
            segments = [s for s in ann.get("OTHER", {}).get("text", "").splitlines() if s.strip()]
            hits = occurrences("total" if field == "total" else "date", value, segments)
            if not hits:
                not_found += 1
                continue
            counts[min(len(hits), 5)] += 1
            if len(hits) > 1:
                context = [f"{segments[i - 1] if i > 0 else ''} | {segments[i]}" for i in hits]
                repeated.append({"dataset": "FATURA", "document": name, "field": field, "value": entry["text"],
                                 "occurrences": len(hits), "contexts": " || ".join(context), "manual_label": ""})
        found = sum(counts.values())
        summary[field] = {
            "documents": len(documents), "field_absent": absent, "value_unparsable": unparsable,
            "value_not_found_in_text": not_found, "value_found": found, "repeated": found - counts[1],
            "repeated_rate": (found - counts[1]) / found if found else None,
            "occurrence_distribution": {("5+" if k == 5 else str(k)): v for k, v in sorted(counts.items())},
        }
    random.Random(seed).shuffle(repeated)
    _write_sample(out / "fatura_repeats_sample.csv", repeated[:sample_size])
    return summary


def _write_sample(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["dataset", "document", "field", "value", "occurrences", "contexts",
                                                "manual_label"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "runs" / "e1")
    parser.add_argument("--sample", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--fatura", type=Path, default=None,
                        help="path to FATURA2.zip (Zenodo 10.5281/zenodo.10371464); skipped if omitted")
    args = parser.parse_args()
    summary = {"SROIE (test split, " + SROIE_REPO + "@" + SROIE_REV[:8] + ")": audit_sroie(args.out, args.sample, args.seed)}
    if args.fatura:
        summary["FATURA (strategy-1 test split, Zenodo 10371464)"] = audit_fatura(args.fatura, args.out, args.sample, args.seed)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
