"""Generation of the pilot stimuli: base invoices x conflicts x label forms x control/conflict."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from cuebind.conflicts import Condition, Conflict, build_meta
from cuebind.labels import LabelForm, labels_for, static_for
from cuebind.render import Renderer
from cuebind.values import sample_values

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
DEV_TEMPLATES = ("t01_classic", "t02_letterhead", "t03_boxed", "t04_band")


@dataclass(frozen=True)
class Item:
    item_id: str
    pair_id: str
    base_id: str
    base_seed: int
    template: str
    conflict: str
    label_form: str
    condition: str
    question_field: str
    candidates: dict[str, str]
    gold: str | None  # true due date in a control; None in a conflict item

    def to_dict(self) -> dict:
        return asdict(self)


def base_seed(conflict: Conflict, index: int, master_seed: int) -> int:
    digest = hashlib.sha256(f"{master_seed}:{conflict}:{index}".encode()).hexdigest()
    return int(digest[:12], 16)


def environment() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATE_DIR), undefined=StrictUndefined, autoescape=True)


def render_html(env: Environment, template: str, seed: int, conflict: Conflict, form: LabelForm,
                condition: Condition) -> tuple[str, dict[str, str]]:
    values = sample_values(seed)
    labels = labels_for(form)
    meta = build_meta(values, labels, conflict, condition)
    html = env.get_template(f"{template}.html").render(
        v=values, L=labels, S=static_for(form), meta=meta.html, extras=""
    )
    return html, meta.candidates


def pilot_design(bases_per_conflict: int, master_seed: int,
                 templates: tuple[str, ...] = DEV_TEMPLATES) -> Iterator[tuple[Item, int]]:
    """Each base invoice is rendered in every label form, as a control and as a conflict.

    Templates rotate over bases so that every template carries the same number of bases per design.
    """
    for c_index, conflict in enumerate(Conflict):
        for b in range(bases_per_conflict):
            seed = base_seed(conflict, b, master_seed)
            template = templates[(b + c_index) % len(templates)]
            base_id = f"{conflict}-b{b:02d}"
            values = sample_values(seed)
            for form in LabelForm:
                pair_id = f"{base_id}-{form}"
                for condition in Condition:
                    item = Item(
                        item_id=f"{pair_id}-{condition}",
                        pair_id=pair_id,
                        base_id=base_id,
                        base_seed=seed,
                        template=template,
                        conflict=str(conflict),
                        label_form=str(form),
                        condition=str(condition),
                        question_field="due_date",
                        candidates={},
                        gold=values.due if condition is Condition.CONTROL else None,
                    )
                    yield item, seed


def generate(out_dir: Path, bases_per_conflict: int = 5, master_seed: int = 20261112) -> Path:
    env = environment()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "items.jsonl"
    with Renderer() as renderer, manifest.open("w", encoding="utf-8") as fh:
        for item, seed in pilot_design(bases_per_conflict, master_seed):
            html, candidates = render_html(env, item.template, seed, Conflict(item.conflict),
                                           LabelForm(item.label_form), Condition(item.condition))
            item = Item(**{**item.to_dict(), "candidates": candidates})
            if item.condition == Condition.CONFLICT and candidates["A"] == candidates["B"]:
                raise ValueError(f"{item.item_id}: candidates are not distinct")
            page = renderer.render(html, out_dir / "images" / f"{item.item_id}.png")
            record = {**item.to_dict(), "image": f"images/{item.item_id}.png",
                      "width": page.width, "height": page.height,
                      "words": [asdict(w) for w in page.words]}
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return manifest
