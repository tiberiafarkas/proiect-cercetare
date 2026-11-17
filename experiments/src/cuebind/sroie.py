"""Transfer tests on real receipts from SROIE (report, Section 5.2).

SROIE provides OCR line segments with pixel boxes. A value inside a segment is located by the share of
characters before and after it, which approximates the value's horizontal extent within the line.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from cuebind.e1 import amount_spans, dates, parse_value
from cuebind.render import Word

REPO, REVISION = "jsdnrs/ICDAR2019-SROIE", "bffe40c26759f3376ec2b3ae9031dbba54cd587c"
GRAY = (128, 128, 128)

QUESTIONS = {
    "date": "What is the date of this receipt?",
    "total": "What is the total amount of this receipt?",
}
F1_HEADER = "Text extracted from the receipt, line by line:"
F2_HEADER = ("Text extracted from the receipt, line by line. Each text segment is followed by its box "
             "[x0,y0,x1,y1] on the page, on a 0-1000 scale:")


@dataclass(frozen=True)
class Receipt:
    key: str
    image: bytes
    width: int
    height: int
    entities: dict[str, str]
    segments: list[tuple[str, list[int]]]

    def words(self) -> list[Word]:
        """Segments in the Word form used by the text serializations of conditions F1 and F2."""
        return [Word(text, tuple(box), None, None, None) for text, box in self.segments]

    def save_image(self, path: Path) -> Path:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.open(io.BytesIO(self.image)).convert("RGB").save(path)
        return path


def load_test_split() -> list[Receipt]:
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(REPO, "data/test-00000-of-00001.parquet", repo_type="dataset", revision=REVISION)
    rows = pq.read_table(path).to_pylist()
    return [Receipt(r["key"], r["image"]["bytes"], r["image_size"]["width"], r["image_size"]["height"],
                    r["entities"], list(zip(r["words"], r["bboxes"]))) for r in rows]


def is_correct(field: str, answer: str, gold: str) -> bool:
    gold_value = parse_value(field, gold)
    if gold_value is None or not answer:
        return False
    if field == "date":
        found = set(dates(answer))
        return found == {gold_value}
    value = parse_value("total", answer)
    return value is not None and abs(value - gold_value) < 0.005


def total_instances(receipt: Receipt) -> list[list[float]]:
    """Approximate pixel box of every occurrence of the annotated total."""
    gold = parse_value("total", receipt.entities["total"])
    boxes = []
    for text, (x0, y0, x1, y1) in receipt.segments:
        n = max(len(text), 1)
        for value, start, end in amount_spans(text):
            if abs(value - gold) < 1e-9:
                char = (x1 - x0) / n
                boxes.append([max(x0, x0 + start * char - char / 2), y0, min(x1, x0 + end * char + char / 2), y1])
    return boxes


def random_control_box(receipt: Receipt, like: list[float], avoid: list[list[float]], seed: int) -> list[float] | None:
    """A box of the same size placed on a text segment that contains none of the avoided boxes."""
    w, h = like[2] - like[0], like[3] - like[1]

    def overlaps(a: list[float], b: list[float]) -> bool:
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    candidates = []
    for _, (x0, y0, x1, y1) in receipt.segments:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        box = [max(0, cx - w / 2), max(0, cy - h / 2), min(receipt.width, cx + w / 2), min(receipt.height, cy + h / 2)]
        if not any(overlaps(box, a) for a in avoid):
            candidates.append(box)
    return random.Random(seed).choice(candidates) if candidates else None


def mask(receipt: Receipt, boxes: list[list[float]], path: Path) -> Path:
    image = Image.open(io.BytesIO(receipt.image)).convert("RGB")
    draw = ImageDraw.Draw(image)
    for x0, y0, x1, y1 in boxes:
        draw.rectangle([x0, y0, x1, y1], fill=GRAY)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def sample(receipts: list[Receipt], n: int, seed: int, predicate=None) -> list[Receipt]:
    pool = [r for r in receipts if predicate is None or predicate(r)]
    return sorted(random.Random(seed).sample(pool, min(n, len(pool))), key=lambda r: r.key)
