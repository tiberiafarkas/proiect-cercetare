"""E3 stimuli: invoices whose issue date occurs twice, with substitution and masking variants (report, Section 3.4).

All variants of one invoice are rendered in advance. Which variant is I1 (the cited instance) or I2 (the
non-cited instance) is decided after the original run, from the instance the model's box covers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import timedelta
from enum import StrEnum
from html import escape
from pathlib import Path

from PIL import Image, ImageChops

from cuebind.generator import DEV_TEMPLATES, environment
from cuebind.labels import LabelForm, labels_for, static_for
from cuebind.render import Renderer
from cuebind.values import InvoiceValues, fmt_date, sample_values

MASK_STYLE = "background: rgb(128,128,128); color: transparent;"


class DuplicateKind(StrEnum):
    COPY = "copy"  # the same field stated twice (footer sentence)
    COLLISION = "collision"  # another field with the same string (delivery date)


class Variant(StrEnum):
    ORIGINAL = "original"
    SUB_META = "sub_meta"  # new date in the metadata instance
    SUB_DUP = "sub_dup"  # new date in the duplicate instance
    SUB_UNRELATED = "sub_unrelated"  # new date in the unrelated contract date
    MASK_META = "mask_meta"
    MASK_DUP = "mask_dup"
    MASK_ALL = "mask_all"


def _span(field: str, instance: str, text: str, masked: bool) -> str:
    style = f' style="{MASK_STYLE}"' if masked else ""
    return f'<span data-field="{field}" data-role="value" data-instance="{instance}"{style}>{escape(text)}</span>'


def substitute_date(values: InvoiceValues, index: int) -> str:
    """A new date of the same format that does not occur on the page; earlier or later by item index."""
    shift = 3 + index % 9
    new = values.issue_date + timedelta(days=shift if index % 2 == 0 else -shift)
    assert new not in (values.issue_date, values.due_date)
    return fmt_date(new)


def contract_date(values: InvoiceValues) -> str:
    return fmt_date(values.issue_date - timedelta(days=40))


def build_html(template: str, seed: int, kind: DuplicateKind, variant: Variant, new_date: str,
               form: LabelForm = LabelForm.RO) -> str:
    values = sample_values(seed)
    labels = labels_for(form)
    meta_text = new_date if variant is Variant.SUB_META else values.issue
    dup_text = new_date if variant is Variant.SUB_DUP else values.issue
    contract_text = new_date if variant is Variant.SUB_UNRELATED else contract_date(values)
    mask_meta = variant in (Variant.MASK_META, Variant.MASK_ALL)
    mask_dup = variant in (Variant.MASK_DUP, Variant.MASK_ALL)

    rows = [
        (f'<span data-field="invoice_number" data-role="label">{escape(labels["invoice_number"])}:</span>',
         f'<span data-field="invoice_number" data-role="value" data-instance="0">{escape(values.invoice_number)}</span>'),
        (f'<span data-field="issue_date" data-role="label">{escape(labels["issue_date"])}:</span>',
         _span("issue_date", "meta", meta_text, mask_meta)),
        (f'<span data-field="due_date" data-role="label">{escape(labels["due_date"])}:</span>',
         f'<span data-field="due_date" data-role="value" data-instance="0">{escape(values.due)}</span>'),
    ]
    if kind is DuplicateKind.COLLISION:
        rows.append((f'<span data-field="delivery_date" data-role="label">{escape(labels["delivery_date"])}:</span>',
                     _span("delivery_date", "dup", dup_text, mask_dup)))
    meta = "<table class='meta meta-rows'>" + "".join(
        f"<tr><td class='ml'>{a}</td><td class='mv'>{b}</td></tr>" for a, b in rows) + "</table>"

    contract = (f'<p style="margin-top: 26px;">Contract nr. {seed % 900 + 100} din '
                f'{_span("contract_date", "unrelated", contract_text, False)}</p>')
    footer = ""
    if kind is DuplicateKind.COPY:
        footer = (f'<p>Factura a fost emisă la data de {_span("issue_date", "dup", dup_text, mask_dup)}.</p>')
    return environment().get_template(f"{template}.html").render(
        v=values, L=labels, S=static_for(form), meta=meta, extras=contract + footer
    )


def instance_boxes(words: list[dict]) -> dict[str, list[float]]:
    """Union box per tracked instance (meta, dup, unrelated)."""
    boxes: dict[str, list[float]] = {}
    for w in words:
        inst = w["instance"]
        if inst in ("meta", "dup", "unrelated"):
            b = boxes.get(inst)
            x0, y0, x1, y1 = w["box"]
            boxes[inst] = [x0, y0, x1, y1] if b is None else [min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)]
    return boxes


def diff_is_confined(original: Path, edited: Path, allowed: list[list[float]], margin: float = 2.0) -> bool:
    """True if every changed pixel lies inside one of the allowed boxes (manipulation check)."""
    a, b = Image.open(original).convert("RGB"), Image.open(edited).convert("RGB")
    if a.size != b.size:
        return False
    bbox = ImageChops.difference(a, b).getbbox()
    if bbox is None:
        return True
    diff = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v else 0)
    for x0, y0, x1, y1 in allowed:
        diff.paste(0, (int(x0 - margin), int(y0 - margin), int(x1 + margin + 1), int(y1 + margin + 1)))
    return diff.getbbox() is None


def generate(out_dir: Path, n_per_kind: int = 10, master_seed: int = 20261113) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "items.jsonl"
    with Renderer() as renderer, manifest.open("w", encoding="utf-8") as fh:
        for k_index, kind in enumerate(DuplicateKind):
            for i in range(n_per_kind):
                index = k_index * n_per_kind + i
                seed = int(hashlib.sha256(f"{master_seed}:{kind}:{i}".encode()).hexdigest()[:12], 16)
                template = DEV_TEMPLATES[index % len(DEV_TEMPLATES)]
                values = sample_values(seed)
                new_date = substitute_date(values, index)
                base_id = f"E3-{kind}-{i:02d}"
                pages = {}
                for variant in Variant:
                    html = build_html(template, seed, kind, variant, new_date)
                    image = out_dir / "images" / f"{base_id}-{variant}.png"
                    pages[variant] = renderer.render(html, image)
                original_boxes = instance_boxes([asdict(w) for w in pages[Variant.ORIGINAL].words])
                edited_box = {Variant.SUB_META: ["meta"], Variant.SUB_DUP: ["dup"], Variant.SUB_UNRELATED: ["unrelated"],
                              Variant.MASK_META: ["meta"], Variant.MASK_DUP: ["dup"], Variant.MASK_ALL: ["meta", "dup"]}
                for variant, page in pages.items():
                    confined = variant is Variant.ORIGINAL or diff_is_confined(
                        Path(pages[Variant.ORIGINAL].image_path), Path(page.image_path),
                        [original_boxes[name] for name in edited_box[variant]])
                    record = {
                        "item_id": f"{base_id}-{variant}", "base_id": base_id, "base_seed": seed, "template": template,
                        "kind": str(kind), "variant": str(variant), "question_field": "issue_date",
                        "original": values.issue, "new_date": new_date, "edit_confined": confined,
                        "image": f"images/{base_id}-{variant}.png", "width": page.width, "height": page.height,
                        "instance_boxes": original_boxes, "words": [asdict(w) for w in page.words],
                    }
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return manifest
