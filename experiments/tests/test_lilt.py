from cuebind.generator import DEV_TEMPLATES
from cuebind.lilt import TAGS, TRAIN_TEMPLATES, word_tags
from cuebind.render import Word


def _w(text, field=None, role=None, instance=None):
    return Word(text, (0, 0, 1, 1), field, role, instance)


def test_training_templates_are_disjoint_from_pilot_templates():
    assert not set(TRAIN_TEMPLATES) & set(DEV_TEMPLATES)


def test_word_tags_are_bio_over_values_only():
    words = [_w("Data", "due_date", "label"), _w("scadenței:", "due_date", "label"),
             _w("13.06.2026", "due_date", "value", "0"), _w("Exemplu", "seller", "value", "0"),
             _w("SRL", "seller", "value", "0"), _w("CUI:"), _w("Model", "buyer", "value", "0")]
    assert word_tags(words) == ["O", "O", "B-due_date", "B-seller", "I-seller", "O", "B-buyer"]
    assert all(t in TAGS for t in word_tags(words))


def test_adjacent_instances_of_same_field_start_new_spans():
    words = [_w("13.06.2026", "due_date", "value", "0"), _w("13.06.2026", "due_date", "value", "1")]
    assert word_tags(words) == ["B-due_date", "B-due_date"]
