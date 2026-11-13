from cuebind.e3_analysis import cited_instance, response, to_page_box

INSTANCES = {"meta": [100, 100, 180, 120], "dup": [300, 500, 380, 520]}


def test_cited_instance_uses_coverage_threshold():
    assert cited_instance([90, 95, 400, 125], INSTANCES) == "meta"  # whole line around the meta value
    assert cited_instance([300, 500, 340, 520], INSTANCES) == "dup"  # exactly half of the duplicate
    assert cited_instance([0, 0, 10, 10], INSTANCES) == "none"
    assert cited_instance(None, INSTANCES) == "no_box"


def test_response_categories():
    assert response('{"answer": "08.01.2026", "bbox_2d": [1,2,3,4]}', "08.01.2026", "11.01.2026") == (
        "retains", [1, 2, 3, 4])
    assert response('{"answer": "11/01/2026"}', "08.01.2026", "11.01.2026")[0] == "follows_edit"
    assert response('{"answer": "07.02.2026"}', "08.01.2026", "11.01.2026")[0] == "other"
    assert response("nothing", "08.01.2026", "11.01.2026") == ("invalid", None)


def test_box_is_scaled_to_page_pixels():
    assert to_page_box([100, 50, 200, 100], [620, 400], 1240, 800) == [200, 100, 400, 200]
