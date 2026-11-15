import json

import pytest

from cuebind.runio import done_keys, load_jsonl, repair


def test_truncated_last_line_is_ignored(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_text(json.dumps({"item_id": "a", "paraphrase": "P1"}) + "\n" + '{"item_id": "b", "para', encoding="utf-8")
    assert done_keys(path) == {("a", "P1")}
    repair(path)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"item_id": "b", "paraphrase": "P1"}) + "\n")
    assert done_keys(path) == {("a", "P1"), ("b", "P1")}


def test_corrupt_middle_line_raises(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_text('{"broken\n' + json.dumps({"item_id": "a", "paraphrase": "P1"}) + "\n", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_jsonl(path)
