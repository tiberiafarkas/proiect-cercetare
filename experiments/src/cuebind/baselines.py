"""Rule-based baselines that each follow exactly one cue (report, Section 3.3).

They see the oracle words and the label strings of the current label form, and return the
date string they would answer for the due-date question, or None.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from cuebind.render import Word
from cuebind.text import DATE_RE, reading_order


def _dates(words: Sequence[Word]) -> list[Word]:
    return [w for w in words if DATE_RE.match(w.text)]


def _find_label(words: Sequence[Word], label: str) -> list[Word]:
    """Consecutive words in reading order whose joined text equals the label (optionally with a colon)."""
    target = label.split()
    ordered = reading_order(words)
    for i in range(len(ordered) - len(target) + 1):
        span = ordered[i : i + len(target)]
        texts = [w.text for w in span]
        texts[-1] = texts[-1].rstrip(":")
        if texts == target:
            return span
    return []


def _union(span: Sequence[Word]) -> tuple[float, float, float, float]:
    return (min(w.box[0] for w in span), min(w.box[1] for w in span),
            max(w.box[2] for w in span), max(w.box[3] for w in span))


def same_row(words: Sequence[Word], labels: dict[str, str]) -> str | None:
    """Adjacency: the first date to the right of the label on its row; else the nearest date directly below."""
    span = _find_label(words, labels["due_date"])
    if not span:
        return None
    x0, y0, x1, y1 = _union(span)
    right = [d for d in _dates(words) if d.box[0] >= x1 and d.box[1] < y1 and d.box[3] > y0]
    if right:
        return min(right, key=lambda d: d.box[0]).text
    below = [d for d in _dates(words) if d.box[1] >= y1 and d.box[0] < x1 and d.box[2] > x0]
    return min(below, key=lambda d: d.box[1]).text if below else None


def rank(words: Sequence[Word], labels: dict[str, str]) -> str | None:
    """Row order: the due-date label's rank among date labels selects the date of the same rank."""
    found = []
    for field in ("issue_date", "due_date"):
        span = _find_label(words, labels[field])
        if not span:
            return None
        found.append((field, _union(span)))
    order = [f for f, box in sorted(found, key=lambda fb: (fb[1][1], fb[1][0]))]
    dates = reading_order(_dates(words))
    position = order.index("due_date")
    return dates[position].text if position < len(dates) else None


def first_after_label(words: Sequence[Word], labels: dict[str, str]) -> str | None:
    """Reading order: the first date that follows the label in line-by-line serialization."""
    span = _find_label(words, labels["due_date"])
    if not span:
        return None
    ordered = reading_order(words)
    start = ordered.index(span[-1]) + 1
    return next((w.text for w in ordered[start:] if DATE_RE.match(w.text)), None)


def usual_row(words: Sequence[Word], labels: dict[str, str]) -> str | None:
    """Typical position: the due date is usually the second date of the document."""
    dates = reading_order(_dates(words))
    return dates[1].text if len(dates) >= 2 else None


def latest(words: Sequence[Word], labels: dict[str, str]) -> str | None:
    """Plausibility: a due date cannot precede the issue date, so take the latest date."""
    dates = _dates(words)
    if not dates:
        return None
    return max(dates, key=lambda d: datetime.strptime(d.text, "%d.%m.%Y")).text


BASELINES = {
    "same_row": same_row,
    "rank": rank,
    "first_after_label": first_after_label,
    "usual_row": usual_row,
    "latest": latest,
}

# For each conflict, the baseline that must choose candidate A and the one that must choose candidate B.
EXPECTED = {
    "C1": ("same_row", "usual_row"),
    "C2": ("rank", "same_row"),
    "C3": ("same_row", "first_after_label"),
    "C4": ("same_row", "latest"),
}
