"""Analyse the human reference study (report, Sections 3.5 and 4.4).

Reads the answer files in human_study/responses and the participant table human_study/participants.json,
which maps each file to a participant and gives the order in which that participant completed lists.
Answers given on a participant's first list are first viewings; answers on later lists were given after
the participant had seen the same invoices in other versions. Results are reported for all answers and
for first viewings only. Files in human_study/test_responses and repeat_responses are never read by default.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from cuebind.runio import load_jsonl
from cuebind.scoring import categorize

ROOT = Path(__file__).resolve().parents[1]


def load_responses(folder: Path, lists: dict[str, list[str]], participants: dict) -> pd.DataFrame:
    owner = {stem: (pid, order) for pid, p in participants.items() for order, stem in enumerate(p["completions"], 1)}
    rows = []
    for path in sorted(folder.glob("raspunsuri_lista*.json")):
        if path.stem not in owner:
            raise ValueError(f"{path.name} is not listed in participants.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = lists[f"lista{data['list']}.html"]
        if sorted(a["item_id"] for a in data["answers"]) != sorted(expected):
            raise ValueError(f"{path.name}: items do not match list {data['list']}")
        pid, order = owner[path.stem]
        for a in data["answers"]:
            rows.append({"participant": pid, "completion": path.stem, "order": order, "list": data["list"],
                         "native_language": data["native_language"], "item_id": a["item_id"],
                         "answer": a["answer"], "realism": a["realism"], "seconds": a["ms"] / 1000})
    return pd.DataFrame(rows)


def model_answers(items: dict) -> dict[str, dict[str, str]]:
    """Category of each model condition's answer per item (paraphrase P1, or P0 for F3)."""
    models = {}
    for path in sorted((ROOT / "runs" / "pilot").glob("e2_F*.jsonl")):
        answers = {}
        for run in load_jsonl(path):
            if run["paraphrase"] in ("P1", "P0"):
                answers[run["item_id"]] = categorize(run["raw_output"], items[run["item_id"]]["candidates"])[0]
        models[path.stem.split("_")[1]] = answers
    return models


def summarize(df: pd.DataFrame, models: dict[str, dict[str, str]]) -> dict:
    out = {"participants": int(df.participant.nunique()), "completions": int(df.completion.nunique()),
           "answers": len(df), "distinct_items": int(df.item_id.nunique()), "by_conflict": {}, "realism": {}}
    for conflict, g in df.groupby("conflict"):
        control, conflicted = g[g.condition == "control"], g[g.condition == "conflict"]
        decisive = conflicted[conflicted.category.isin(["A", "B"])]
        out["by_conflict"][conflict] = {
            "control_answers": len(control), "control_correct": int((control.category == "A").sum()),
            "conflict_answers": len(conflicted), "decisive": len(decisive),
            "follows_A": int((decisive.category == "A").sum()),
            "cannot_tell": int((conflicted.category == "cannot_tell").sum()),
        }
    for condition, g in df.groupby("condition"):
        out["realism"][condition] = {"mean": round(float(g.realism.mean()), 2), "n": len(g)}
    decisive = df[(df.condition == "conflict") & df.category.isin(["A", "B"])]
    out["agreement_with_models_on_conflicts"] = {
        name: {"matches": int(sum(answers.get(i) == c for i, c in zip(decisive.item_id, decisive.category))),
               "of": len(decisive)}
        for name, answers in models.items()
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, default=ROOT / "human_study" / "responses")
    parser.add_argument("--participants", type=Path, default=ROOT / "human_study" / "participants.json")
    parser.add_argument("--out", type=Path, default=ROOT / "runs" / "human")
    args = parser.parse_args()

    lists = json.loads((ROOT / "human_study" / "lists.json").read_text(encoding="utf-8"))
    participants = json.loads(args.participants.read_text(encoding="utf-8"))
    df = load_responses(args.responses, lists, participants)
    if df.empty:
        print(f"No answer files in {args.responses}")
        return
    items = {r["item_id"]: r for r in load_jsonl(ROOT / "data" / "generated" / "pilot" / "items.jsonl")}
    for key in ("conflict", "condition", "label_form", "template"):
        df[key] = df.item_id.map(lambda i, k=key: items[i][k])
    df["category"] = [
        "cannot_tell" if answer == "cannot_tell"
        else categorize(json.dumps({"answer": answer}), items[item]["candidates"])[0]
        for item, answer in zip(df.item_id, df.answer)
    ]
    args.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out / "human_scored.csv", index=False)

    models = model_answers(items)
    per_completion = (df.groupby(["participant", "order", "list"])
                      .agg(minutes=("seconds", lambda s: round(s.sum() / 60, 1)),
                           cannot_tell=("category", lambda s: int((s == "cannot_tell").sum())))
                      .reset_index().to_dict("records"))
    summary = {"completions": per_completion,
               "all_answers": summarize(df, models),
               "first_viewings_only": summarize(df[df.order == 1], models)}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
