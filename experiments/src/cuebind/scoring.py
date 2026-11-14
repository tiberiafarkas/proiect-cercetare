"""Answer parsing, normalization and categorization (report, Section 3.4)."""

from __future__ import annotations

import json
import re

_DATE = re.compile(r"(\d{1,2})\s*[./\-]\s*(\d{1,2})\s*[./\-]\s*(\d{4})")


def parse_json(text: str) -> dict | None:
    """First JSON object in a model output, or None if there is none."""
    match = re.search(r"\{.*?\}", text, re.S)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def normalize(answer: str) -> str:
    """An answer with exactly one date and no other number becomes dd.mm.yyyy.

    Words around the date (for example an echoed label) are allowed. Any other answer, including a date
    mixed with an amount, is lowercased and trimmed, so it can never equal a candidate date.
    """
    found = list(_DATE.finditer(answer))
    if len(found) == 1:
        rest = answer[: found[0].start()] + answer[found[0].end():]
        if not re.search(r"\d", rest):
            day, month, year = found[0].groups()
            return f"{int(day):02d}.{int(month):02d}.{year}"
    return " ".join(answer.lower().split())


def categorize(raw_output: str, candidates: dict[str, str]) -> tuple[str, str | None]:
    """Return (category, normalized answer); category is A, B, other or invalid.

    In a control both candidates equal the true due date, so a correct answer is categorized as A.
    """
    parsed = parse_json(raw_output)
    if parsed is None or not isinstance(parsed.get("answer"), str):
        return "invalid", None
    answer = normalize(parsed["answer"])
    if answer == normalize(candidates["A"]):
        return "A", answer
    if answer == normalize(candidates["B"]):
        return "B", answer
    return "other", answer


def box_area(b: list[float]) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def intersection(a: list[float], b: list[float]) -> float:
    return box_area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])


def iou(a: list[float], b: list[float]) -> float:
    inter = intersection(a, b)
    union = box_area(a) + box_area(b) - inter
    return inter / union if union > 0 else 0.0


def coverage(cited: list[float], target: list[float]) -> float:
    """Share of the target box covered by the cited box."""
    area = box_area(target)
    return intersection(cited, target) / area if area > 0 else 0.0
