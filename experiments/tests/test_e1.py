from datetime import date

from cuebind.e1 import amounts, dates, occurrences, parse_value


def test_amounts_and_dates_are_extracted():
    assert amounts("TOTAL INCLUSIVE GST: 1,193.00 RM 5.50") == [1193.0, 5.5]
    assert dates(": 15/01/2019 11:05:16 AM") == [date(2019, 1, 15)]
    assert dates("DATE:09-02-18") == [date(2018, 2, 9)]
    assert dates("25 DEC 2018") == [date(2018, 12, 25)]
    assert dates("2018-12-25") == [date(2018, 12, 25)]
    assert dates("27/MAR/2018") == [date(2018, 3, 27)]
    assert dates("4/22/2018") == [date(2018, 4, 22)]


def test_occurrences_count_every_match():
    segments = ["193.00", "193.00 SR", "TOTAL:", "193.00", "TOTAL GST @6%: 0.00"]
    value = parse_value("total", "193.00")
    assert occurrences("total", value, segments) == [0, 1, 3]
    assert occurrences("date", parse_value("date", "15/01/2019"), ["DATE 15/01/2019", "15-01-19"]) == [0, 1]
