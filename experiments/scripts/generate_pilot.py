"""Generate the pilot stimuli (report, Section 3.6) into data/generated/pilot."""

import argparse
from pathlib import Path

from cuebind.generator import generate

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bases-per-conflict", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261112)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "generated" / "pilot")
    args = parser.parse_args()
    manifest = generate(args.out, args.bases_per_conflict, args.seed)
    print(f"Wrote {sum(1 for _ in manifest.open(encoding='utf-8'))} items to {manifest}")


if __name__ == "__main__":
    main()
