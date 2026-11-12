"""E2 analysis: cue-following rates with cluster-bootstrap intervals (report, Sections 3.4-3.5)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from cuebind.scoring import categorize

CELL = ["condition_model", "conflict", "label_form"]


def score(items_path: Path, run_paths: list[Path]) -> pd.DataFrame:
    """One row per (item, paraphrase, model condition) with the answer category."""
    items = {}
    for line in items_path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        r.pop("words")
        items[r["item_id"]] = r
    rows = []
    for path in run_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            run = json.loads(line)
            item = items[run["item_id"]]
            category, answer = categorize(run["raw_output"], item["candidates"])
            rows.append({
                "item_id": item["item_id"], "pair_id": item["pair_id"], "base_id": item["base_id"],
                "template": item["template"], "conflict": item["conflict"], "label_form": item["label_form"],
                "condition": item["condition"], "paraphrase": run["paraphrase"],
                "condition_model": run["condition"], "category": category, "answer": answer,
                "raw_output": run["raw_output"],
            })
    df = pd.DataFrame(rows)
    # Control correctness of the matched control, for the same model condition and paraphrase.
    control = df[df.condition == "control"].set_index(["pair_id", "paraphrase", "condition_model"])["category"] == "A"
    key = pd.MultiIndex.from_frame(df[["pair_id", "paraphrase", "condition_model"]])
    df["control_correct"] = control.reindex(key).fillna(False).astype(bool).to_numpy()
    return df


def _counts(df: pd.DataFrame) -> pd.DataFrame:
    """Per cell and base invoice: counts that the statistics are computed from."""
    conflict = df[df.condition == "conflict"]
    control = df[df.condition == "control"]
    agg = conflict.groupby(CELL + ["base_id"]).agg(
        n=("category", "size"),
        n_a=("category", lambda s: (s == "A").sum()),
        n_b=("category", lambda s: (s == "B").sum()),
        n_other=("category", lambda s: (s == "other").sum()),
        n_invalid=("category", lambda s: (s == "invalid").sum()),
        n_a_cond=("category", lambda s: (s[conflict.loc[s.index, "control_correct"]] == "A").sum()),
        n_b_cond=("category", lambda s: (s[conflict.loc[s.index, "control_correct"]] == "B").sum()),
    )
    ctrl = control.groupby(CELL + ["base_id"]).agg(n_ctrl=("category", "size"),
                                                  n_ctrl_ok=("category", lambda s: (s == "A").sum()))
    return agg.join(ctrl, how="outer").fillna(0).astype(int).reset_index()


def _stats(c: pd.DataFrame) -> dict[str, float]:
    s = c[["n", "n_a", "n_b", "n_other", "n_invalid", "n_a_cond", "n_b_cond", "n_ctrl", "n_ctrl_ok"]].sum()
    ratio = lambda a, b: a / b if b else np.nan  # noqa: E731
    return {
        "control_accuracy": ratio(s.n_ctrl_ok, s.n_ctrl),
        "F_A": ratio(s.n_a, s.n_a + s.n_b),
        "D": ratio(s.n_a + s.n_b, s.n),
        "F_A_conditioned": ratio(s.n_a_cond, s.n_a_cond + s.n_b_cond),
        "other_rate": ratio(s.n_other, s.n),
        "invalid_rate": ratio(s.n_invalid, s.n),
    }


def summarize(df: pd.DataFrame, replicates: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Point estimates and 95% percentile intervals from resampling base invoices within each cell."""
    counts = _counts(df)
    rng = np.random.default_rng(seed)
    rows = []
    for cell, c in counts.groupby(CELL):
        point = _stats(c)
        boots = []
        for _ in range(replicates):
            boots.append(_stats(c.iloc[rng.integers(0, len(c), len(c))]))
        boots = pd.DataFrame(boots)
        row = dict(zip(CELL, cell))
        row.update({"bases": len(c), "queries": int(c.n.sum()), "decisive": int((c.n_a + c.n_b).sum())})
        for k, v in point.items():
            row[k] = v
            if k in ("control_accuracy", "F_A", "D", "F_A_conditioned"):
                row[f"{k}_lo"], row[f"{k}_hi"] = boots[k].quantile([0.025, 0.975]).to_numpy()
        rows.append(row)
    return pd.DataFrame(rows)


def label_form_effects(df: pd.DataFrame, replicates: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Delta_l = F_A(l) - F_A(RO), resampling base invoices jointly because forms share bases."""
    counts = _counts(df)
    rng = np.random.default_rng(seed)
    rows = []
    for (model, conflict), c in counts.groupby(["condition_model", "conflict"]):
        bases = c.base_id.unique()
        by_form = {f: g.set_index("base_id") for f, g in c.groupby("label_form")}
        if "RO" not in by_form:
            continue

        def rate(form: str, sample: np.ndarray) -> float:
            g = by_form[form].reindex(sample).dropna()
            a, b = g.n_a.sum(), g.n_b.sum()
            return a / (a + b) if a + b else np.nan

        for form in ("ND", "AB", "EN"):
            if form not in by_form:
                continue
            point = rate(form, bases) - rate("RO", bases)
            boots = []
            for _ in range(replicates):
                sample = rng.choice(bases, len(bases))
                boots.append(rate(form, sample) - rate("RO", sample))
            lo, hi = np.nanquantile(boots, [0.025, 0.975])
            rows.append({"condition_model": model, "conflict": conflict, "label_form": form,
                         "delta_F_A": point, "lo": lo, "hi": hi})
    return pd.DataFrame(rows)
