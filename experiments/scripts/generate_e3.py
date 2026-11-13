"""Generate the E3 pilot stimuli into data/generated/e3."""

import argparse
import json
from pathlib import Path

from cuebind.e3 import generate

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-kind", type=int, default=10)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "generated" / "e3")
    args = parser.parse_args()
    manifest = generate(args.out, args.per_kind)
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    confined = sum(r["edit_confined"] for r in rows)
    print(f"Wrote {len(rows)} images; edits confined to the edited box in {confined}/{len(rows)}")
    for r in rows:
        if not r["edit_confined"]:
            print("  not confined:", r["item_id"])


if __name__ == "__main__":
    main()
