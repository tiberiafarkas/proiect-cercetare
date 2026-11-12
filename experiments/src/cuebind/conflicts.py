"""Cue conflicts C1-C4 and their matched controls (report, Section 3.2).

Every function builds the HTML of the invoice's metadata block (invoice number, issue date, due date).
Only this block differs between a conflict item and its control.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from html import escape

from cuebind.values import InvoiceValues


class Conflict(StrEnum):
    C1 = "C1"  # label vs typical position
    C2 = "C2"  # row order vs same-row adjacency
    C3 = "C3"  # spatial pairing vs reading order
    C4 = "C4"  # label vs plausibility


class Condition(StrEnum):
    CONTROL = "control"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class Entry:
    """One label-value pair; `value_field` is the field the value fills in the document's row structure."""

    field: str
    label: str
    value: str
    value_field: str


@dataclass(frozen=True)
class MetaBlock:
    html: str
    candidates: dict[str, str]  # {"A": ..., "B": ...}; equal to the true due date in a control


def _label(e: Entry) -> str:
    return f'<span data-field="{e.field}" data-role="label">{escape(e.label)}:</span>'


def _value(e: Entry) -> str:
    return f'<span data-field="{e.value_field}" data-role="value" data-instance="0">{escape(e.value)}</span>'


def rows(entries: list[Entry], shift: int = 0) -> str:
    """Two-column table of labels and values; `shift` moves the value column down by whole rows."""
    n = len(entries) + shift
    labels = [_label(e) for e in entries] + [""] * shift
    values = [""] * shift + [_value(e) for e in entries]
    body = "".join(f"<tr><td class='ml'>{labels[i]}</td><td class='mv'>{values[i]}</td></tr>" for i in range(n))
    return f"<table class='meta meta-rows'>{body}</table>"


def grid(entries: list[Entry]) -> str:
    """All labels in one row, each value directly below its label."""
    head = "".join(f"<td class='ml'>{_label(e)}</td>" for e in entries)
    vals = "".join(f"<td class='mv'>{_value(e)}</td>" for e in entries)
    return f"<table class='meta meta-grid'><tr>{head}</tr><tr>{vals}</tr></table>"


def stacked(entries: list[Entry]) -> str:
    """Each label directly above its value, pairs stacked vertically."""
    blocks = "".join(f"<div class='pair'><div class='ml'>{_label(e)}</div><div class='mv'>{_value(e)}</div></div>"
                     for e in entries)
    return f"<div class='meta meta-stacked'>{blocks}</div>"


def build_meta(values: InvoiceValues, labels: dict[str, str], conflict: Conflict, condition: Condition) -> MetaBlock:
    number = Entry("invoice_number", labels["invoice_number"], values.invoice_number, "invoice_number")
    issue = Entry("issue_date", labels["issue_date"], values.issue, "issue_date")
    due = Entry("due_date", labels["due_date"], values.due, "due_date")
    standard = [number, issue, due]
    control = condition is Condition.CONTROL
    agree = {"A": values.due, "B": values.due}

    if conflict is Conflict.C1:
        if control:
            return MetaBlock(rows(standard), agree)
        return MetaBlock(rows([number, due, issue]), {"A": values.due, "B": values.issue})

    if conflict is Conflict.C2:
        if control:
            return MetaBlock(rows(standard), agree)
        return MetaBlock(rows(standard, shift=1), {"A": values.due, "B": values.issue})

    if conflict is Conflict.C3:
        if control:
            return MetaBlock(stacked(standard), agree)
        return MetaBlock(grid(standard), {"A": values.due, "B": values.issue})

    if conflict is Conflict.C4:
        if control:
            return MetaBlock(rows(standard), agree)
        # The two dates swap, so the date shown as due date is earlier than the issue date.
        swapped = [number,
                   Entry("issue_date", labels["issue_date"], values.due, "issue_date"),
                   Entry("due_date", labels["due_date"], values.issue, "due_date")]
        return MetaBlock(rows(swapped), {"A": values.issue, "B": values.due})

    raise ValueError(conflict)
