import urllib.parse
from datetime import date

import pytest

from data.fetch_week import check_rows, count_rows, soql_url, verify


def test_url_filters_the_week_and_orders_by_trip_id():
    u = urllib.parse.unquote(soql_url(date(2023, 6, 5), date(2023, 6, 11)))
    assert "resource/wrvz-psew.csv" in u
    assert "trip_start_timestamp between '2023-06-05T00:00:00' and '2023-06-11T23:59:59'" in u
    assert "$order=trip_id" in u and "$limit=2000000" in u


def test_row_count_at_limit_is_rejected():
    with pytest.raises(ValueError):
        check_rows(2_000_000, 2_000_000)
    check_rows(1_999_999, 2_000_000)


def test_checksum_mismatch_is_rejected(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("a\n")
    with pytest.raises(ValueError):
        verify(p, "0" * 64)
    verify(p, "87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7")


def test_count_rows_skips_header_and_respects_quoted_newlines(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text('"a","b"\n"1","x"\n"2","line\nbreak"\n')
    assert count_rows(p) == 2
