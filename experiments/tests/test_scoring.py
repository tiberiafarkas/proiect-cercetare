from cuebind.scoring import categorize, coverage, iou, normalize, parse_json

CANDIDATES = {"A": "13.06.2026", "B": "14.05.2026"}


def test_normalize_unifies_date_formats():
    assert normalize("13.06.2026") == "13.06.2026"
    assert normalize(" 13/6/2026 ") == "13.06.2026"
    assert normalize("13 - 06 - 2026") == "13.06.2026"
    assert normalize("13.06.2026.") == "13.06.2026"
    assert normalize("Data emiterii: 13.06.2026") == "13.06.2026"
    assert normalize("(RON) 27.888,84 13.06.2026") == "(ron) 27.888,84 13.06.2026"
    assert normalize("13.06.2026 - 14.07.2026") == "13.06.2026 - 14.07.2026"
    assert normalize("  Exemplu   SRL ") == "exemplu srl"


def test_parse_json_takes_first_object_and_rejects_garbage():
    assert parse_json('```json\n{"answer": "13.06.2026"}\n```') == {"answer": "13.06.2026"}
    assert parse_json("no json here") is None
    assert parse_json("{not: valid}") is None


def test_categorize():
    assert categorize('{"answer": "13.06.2026"}', CANDIDATES) == ("A", "13.06.2026")
    assert categorize('{"answer": "14/05/2026"}', CANDIDATES) == ("B", "14.05.2026")
    assert categorize('{"answer": "01.01.2026"}', CANDIDATES) == ("other", "01.01.2026")
    assert categorize("I think it is 13.06.2026", CANDIDATES) == ("invalid", None)
    assert categorize('{"answer": "Data scadenței: 13.06.2026"}', CANDIDATES) == ("A", "13.06.2026")
    assert categorize('{"answer": 5}', CANDIDATES) == ("invalid", None)


def test_iou_and_coverage():
    value = [10, 10, 20, 20]
    line = [0, 10, 40, 20]  # a box around the whole line covers the value fully but has low IoU
    assert coverage(line, value) == 1.0
    assert iou(line, value) == 0.25
    assert iou(value, value) == 1.0
    assert coverage([30, 30, 40, 40], value) == 0.0
