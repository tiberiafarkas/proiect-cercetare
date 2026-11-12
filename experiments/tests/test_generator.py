import hashlib
import unicodedata
from dataclasses import asdict
from pathlib import Path

import pytest

from cuebind.baselines import BASELINES, EXPECTED
from cuebind.conflicts import Condition, Conflict, build_meta
from cuebind.generator import DEV_TEMPLATES, TEMPLATE_DIR, environment, pilot_design, render_html
from cuebind.labels import LABELS, LabelForm, labels_for
from cuebind.render import Renderer
from cuebind.values import DUE_OFFSETS, sample_values

SEEDS = range(25)


def strip_diacritics(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))


@pytest.fixture(scope="module")
def renderer():
    with Renderer() as r:
        yield r


def test_values_are_deterministic_and_dates_differ():
    for seed in SEEDS:
        a, b = sample_values(seed), sample_values(seed)
        assert a == b
        assert (a.due_date - a.issue_date).days in DUE_OFFSETS
        assert a.seller.name != a.buyer.name


def test_nd_labels_are_ro_labels_without_diacritics():
    for forms in LABELS.values():
        assert forms[LabelForm.ND] == strip_diacritics(forms[LabelForm.RO])


def test_candidates_are_distinct_in_conflicts_and_equal_in_controls():
    for seed in SEEDS:
        values = sample_values(seed)
        for conflict in Conflict:
            for form in LabelForm:
                labels = labels_for(form)
                control = build_meta(values, labels, conflict, Condition.CONTROL).candidates
                assert control == {"A": values.due, "B": values.due}
                cand = build_meta(values, labels, conflict, Condition.CONFLICT).candidates
                assert cand["A"] != cand["B"]
                assert set(cand.values()) == {values.issue, values.due}


def test_pilot_design_is_balanced():
    items = [item for item, _ in pilot_design(bases_per_conflict=5, master_seed=1)]
    assert len(items) == 4 * 5 * 4 * 2
    per_template = {t: sum(i.template == t for i in items) for t in DEV_TEMPLATES}
    assert set(per_template.values()) == {len(items) // len(DEV_TEMPLATES)}
    # Each pair shares its base invoice; each base appears in every label form.
    bases = {}
    for i in items:
        bases.setdefault(i.base_id, set()).add(i.label_form)
    assert all(forms == {str(f) for f in LabelForm} for forms in bases.values())


def test_templates_exist():
    for name in DEV_TEMPLATES:
        assert (TEMPLATE_DIR / f"{name}.html").is_file()


def _render_items(renderer, tmp_path: Path, bases_per_conflict: int = 1):
    env = environment()
    for item, seed in pilot_design(bases_per_conflict, master_seed=7):
        html, candidates = render_html(env, item.template, seed, Conflict(item.conflict),
                                       LabelForm(item.label_form), Condition(item.condition))
        page = renderer.render(html, tmp_path / f"{item.item_id}.png")
        yield item, candidates, page


def test_every_baseline_follows_its_cue(renderer, tmp_path):
    """Manipulation check (report, Section 3.5)."""
    for item, candidates, page in _render_items(renderer, tmp_path):
        labels = labels_for(LabelForm(item.label_form))
        answers = {name: fn(page.words, labels) for name, fn in BASELINES.items()}
        if item.condition == Condition.CONTROL:
            assert all(a == item.gold for a in answers.values()), (item.item_id, answers)
        else:
            follows_a, follows_b = EXPECTED[item.conflict]
            assert answers[follows_a] == candidates["A"], (item.item_id, answers)
            assert answers[follows_b] == candidates["B"], (item.item_id, answers)


def test_word_tags_and_boxes(renderer, tmp_path):
    for item, candidates, page in _render_items(renderer, tmp_path):
        due_label = [w for w in page.words if w.field == "due_date" and w.role == "label"]
        assert due_label, item.item_id
        values = {w.text for w in page.words if w.role == "value" and w.field in ("issue_date", "due_date")}
        assert set(candidates.values()) <= values
        for w in page.words:
            x0, y0, x1, y1 = w.box
            assert 0 <= x0 < x1 <= page.width and 0 <= y0 < y1 <= page.height, (item.item_id, w)


def test_rendering_is_deterministic(renderer, tmp_path):
    env = environment()
    values_seed = 123
    html, _ = render_html(env, DEV_TEMPLATES[0], values_seed, Conflict.C1, LabelForm.RO, Condition.CONFLICT)
    first = renderer.render(html, tmp_path / "a.png")
    second = renderer.render(html, tmp_path / "b.png")
    assert [asdict(w) for w in first.words] == [asdict(w) for w in second.words]
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
    assert digest(first.image_path) == digest(second.image_path)


def test_text_transform_is_rejected(renderer, tmp_path):
    html = '<html><body><div style="text-transform: uppercase">Furnizor</div></body></html>'
    with pytest.raises(ValueError):
        renderer.render(html, tmp_path / "x.png")
