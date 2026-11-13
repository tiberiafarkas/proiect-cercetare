"""E1: how often the answer value of a field occurs more than once on the same page (report, Section 3.4).

String-level counts are automatic. Whether a repeated string is a copy of the same fact or a collision
with another field needs a manual check; the audit exports a sample with context for that purpose.
"""

from __future__ import annotations

import re
from datetime import date, datetime

_AMOUNT = re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3})*\.\d{2}(?![\d])|(?<![\d.,])\d+\.\d{2}(?![\d])")
_DATE_NUMERIC = re.compile(r"(?<!\d)(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{2,4})(?!\d)")
_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
_DATE_TEXT = re.compile(r"(?<!\d)(\d{1,2})[\s\-/.]*(" + "|".join(_MONTHS) + r")[A-Z]*[\s\-/.,]*(\d{2,4})", re.I)


def amounts(text: str) -> list[float]:
    return [float(m.replace(",", "")) for m in _AMOUNT.findall(text)]


def _year(y: str) -> int:
    return int(y) + 2000 if len(y) == 2 else int(y)


def dates(text: str) -> list[date]:
    found = []
    for a, b, c in _DATE_NUMERIC.findall(text):
        try:
            if len(a) == 4:
                found.append(date(int(a), int(b), int(c)))
                continue
            try:
                found.append(date(_year(c), int(b), int(a)))
            except ValueError:
                # Month-first order (e.g. 4/22/2018) when the day-first reading is not a valid date.
                found.append(date(_year(c), int(a), int(b)))
        except ValueError:
            continue
    for d, mon, y in _DATE_TEXT.findall(text):
        try:
            found.append(date(_year(y), _MONTHS[mon.upper()[:3]], int(d)))
        except ValueError:
            continue
    return found


def parse_value(field: str, value: str) -> float | date | None:
    if field == "total":
        values = amounts(value) or [float(v) for v in re.findall(r"\d+(?:\.\d+)?", value.replace(",", ""))]
        return values[0] if values else None
    if field == "date":
        found = dates(value)
        return found[0] if found else None
    raise ValueError(field)


def occurrences(field: str, value: float | date, segments: list[str]) -> list[int]:
    """Indices of the text segments that contain the value, once per occurrence."""
    hits = []
    for i, segment in enumerate(segments):
        found = amounts(segment) if field == "total" else dates(segment)
        hits.extend(i for v in found if (abs(v - value) < 1e-9 if field == "total" else v == value))
    return hits


def parse_fatura_date(text: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%b %d, %Y", "%d %b %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    found = dates(text)
    return found[0] if found else None
