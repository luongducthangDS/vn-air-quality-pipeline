import datetime as dt

from ingest import month_end, months


def test_months_cover_range_inclusive():
    got = list(months(dt.date(2022, 11, 15), dt.date(2023, 2, 3)))
    assert got == [dt.date(2022, 11, 1), dt.date(2022, 12, 1), dt.date(2023, 1, 1), dt.date(2023, 2, 1)]


def test_month_end_clamps_to_today():
    today = dt.date(2024, 2, 10)
    assert month_end(dt.date(2024, 1, 1), today) == dt.date(2024, 1, 31)
    assert month_end(dt.date(2024, 2, 1), today) == today  # never ask the API for the future
    assert month_end(dt.date(2023, 2, 1), today) == dt.date(2023, 2, 28)
