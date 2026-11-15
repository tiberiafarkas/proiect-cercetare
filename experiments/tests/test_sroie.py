from cuebind.sroie import Receipt, is_correct, random_control_box, total_instances


def _receipt(segments):
    return Receipt("k", b"", 400, 800, {"date": "15/01/2019", "total": "193.00"}, segments)


def test_is_correct_date_and_total():
    assert is_correct("date", "15-01-2019", "15/01/2019")
    assert is_correct("date", "15/01/2019 11:05 AM", "15/01/2019")
    assert not is_correct("date", "15/01/2019 or 16/01/2019", "15/01/2019")
    assert is_correct("total", "RM 193.00", "193.00")
    assert is_correct("total", "193", "193.00")
    assert not is_correct("total", "1,193.00", "193.00")
    assert not is_correct("total", "", "193.00")


def test_total_instances_locate_value_within_segment():
    r = _receipt([("TOTAL: 193.00", [100, 500, 230, 520]), ("193.00", [300, 300, 360, 320]),
                  ("1,193.00", [0, 0, 80, 20])])
    boxes = total_instances(r)
    assert len(boxes) == 2
    x0, y0, x1, y1 = boxes[0]
    # "193.00" occupies characters 7-13 of 13 in a 130 px segment, i.e. 70-130 px, widened by half a character.
    assert (y0, y1) == (500, 520) and 160 <= x0 <= 170 and x1 == 230
    assert boxes[1] == [300, 300, 360, 320]


def test_random_control_avoids_value_boxes():
    r = _receipt([("TOTAL: 193.00", [100, 500, 230, 520]), ("THANK YOU", [100, 600, 200, 620])])
    avoid = total_instances(r)
    for seed in range(10):
        box = random_control_box(r, avoid[0], avoid, seed)
        assert box is not None and box[1] >= 590
