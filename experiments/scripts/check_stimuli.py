"""Manipulation check on a generated stimulus set: every baseline must follow its own cue.

Writes a JSON summary next to the items so that the case study can report it.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from cuebind.baselines import BASELINES, EXPECTED
from cuebind.labels import LabelForm, labels_for
from cuebind.render import Word

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=Path, default=ROOT / "data" / "generated" / "pilot" / "items.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "runs" / "pilot" / "stimulus_check.json")
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.items.read_text(encoding="utf-8").splitlines()]
    passed, failures = Counter(), []
    for r in rows:
        words = [Word(w["text"], tuple(w["box"]), w["field"], w["role"], w["instance"]) for w in r["words"]]
        answers = {name: fn(words, labels_for(LabelForm(r["label_form"]))) for name, fn in BASELINES.items()}
        if r["condition"] == "control":
            ok = all(a == r["gold"] for a in answers.values())
        else:
            follows_a, follows_b = EXPECTED[r["conflict"]]
            ok = answers[follows_a] == r["candidates"]["A"] and answers[follows_b] == r["candidates"]["B"]
        key = f"{r['conflict']}-{r['condition']}"
        passed[key] += ok
        if not ok:
            failures.append({"item_id": r["item_id"], "answers": answers, "candidates": r["candidates"]})

    summary = {
        "items": len(rows),
        "passed": sum(passed.values()),
        "by_cell": {k: passed[k] for k in sorted(passed)},
        "templates": dict(Counter(r["template"] for r in rows)),
        "failures": failures,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{summary['passed']}/{summary['items']} items pass; templates {summary['templates']}")


if __name__ == "__main__":
    main()
