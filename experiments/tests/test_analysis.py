import pandas as pd

from cuebind.analysis import _counts, _stats, summarize


def _rows(categories_conflict, control_ok, base="b0"):
    rows = []
    for i, (cat, ok) in enumerate(zip(categories_conflict, control_ok)):
        pair = f"{base}-p{i}"
        common = {"pair_id": pair, "base_id": base, "condition_model": "F1", "conflict": "C1",
                  "label_form": "RO", "paraphrase": "P1"}
        rows.append({**common, "condition": "conflict", "category": cat, "control_correct": ok})
        rows.append({**common, "condition": "control", "category": "A" if ok else "other", "control_correct": ok})
    return rows


def test_cue_following_rate_excludes_other_and_invalid():
    df = pd.DataFrame(_rows(["A", "A", "B", "other", "invalid"], [True] * 5))
    stats = _stats(_counts(df))
    assert stats["F_A"] == 2 / 3
    assert stats["D"] == 3 / 5
    assert stats["control_accuracy"] == 1.0


def test_conditioned_rate_uses_only_pairs_with_correct_control():
    df = pd.DataFrame(_rows(["A", "B", "B"], [True, False, False]))
    stats = _stats(_counts(df))
    assert stats["F_A"] == 1 / 3
    assert stats["F_A_conditioned"] == 1.0
    assert stats["control_accuracy"] == 1 / 3


def test_summary_intervals_contain_point_estimate():
    df = pd.DataFrame(_rows(["A", "B", "A", "A"], [True] * 4, "b0") + _rows(["B", "B", "A", "B"], [True] * 4, "b1"))
    s = summarize(df, replicates=200).iloc[0]
    assert s.F_A_lo <= s.F_A <= s.F_A_hi
    assert s.bases == 2
