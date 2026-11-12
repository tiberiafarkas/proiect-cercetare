"""Text serializations of rendered words, shared by the baselines and the text-only model conditions."""

from __future__ import annotations

import re
from collections.abc import Sequence

from cuebind.render import Word

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
LINE_TOLERANCE_PX = 6


def centre_y(w: Word) -> float:
    return (w.box[1] + w.box[3]) / 2


def reading_order_lines(words: Sequence[Word]) -> list[list[Word]]:
    """Group words into lines by vertical centre (top to bottom), each line left to right."""
    lines: list[list[Word]] = []
    for w in sorted(words, key=lambda w: (centre_y(w), w.box[0])):
        if lines and abs(centre_y(w) - centre_y(lines[-1][0])) <= LINE_TOLERANCE_PX:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(line, key=lambda w: w.box[0]) for line in lines]


def reading_order(words: Sequence[Word]) -> list[Word]:
    return [w for line in reading_order_lines(words) for w in line]


def plain_text(words: Sequence[Word]) -> str:
    """Condition F1: oracle words, one line of text per visual line."""
    return "\n".join(" ".join(w.text for w in line) for line in reading_order_lines(words))


def text_with_boxes(words: Sequence[Word], width: int, height: int) -> str:
    """Condition F2: the same lines, each word followed by its box normalized to 0-1000."""

    def norm(w: Word) -> str:
        x0, y0, x1, y1 = w.box
        return (f"{w.text} [{round(1000 * x0 / width)},{round(1000 * y0 / height)},"
                f"{round(1000 * x1 / width)},{round(1000 * y1 / height)}]")

    return "\n".join(" ".join(norm(w) for w in line) for line in reading_order_lines(words))
