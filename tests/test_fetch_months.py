import duckdb
import pytest

from ingest.fetch_months import extract_month, month_from_path, months_to_fetch, source_url


def test_month_from_path_parses_monthly_file():
    assert month_from_path("monthly_processed_data/data-2026-08.parquet") == "2026-08"


def test_month_from_path_ignores_other_files():
    assert month_from_path("raw_data/year=2026/month=8/day=1/x.parquet") is None


def test_months_to_fetch_skips_months_already_downloaded():
    available = ["2026-06", "2026-07", "2026-08"]
    assert months_to_fetch(available, existing=["2026-06"], requested=["2026-06", "2026-08"]) == [
        "2026-08"
    ]


def test_months_to_fetch_latest_takes_newest_available():
    available = ["2026-08", "2026-06", "2026-07"]
    assert months_to_fetch(available, existing=[], latest=1) == ["2026-08"]


def test_months_to_fetch_rejects_unavailable_month():
    with pytest.raises(ValueError, match="2030-01"):
        months_to_fetch(["2026-08"], existing=[], requested=["2030-01"])


def test_source_url_is_pinned_to_revision():
    assert source_url("2026-08", "abc123") == (
        "https://huggingface.co/datasets/piebro/deutsche-bahn-data/resolve/abc123/"
        "monthly_processed_data/data-2026-08.parquet"
    )


def test_extract_month_keeps_only_long_distance_trains(tmp_path):
    src = tmp_path / "src.parquet"
    dst = tmp_path / "out.parquet"
    duckdb.sql(
        "SELECT * FROM (VALUES ('ICE', 1), ('IC', 2), ('EC', 3), ('RE', 4), ('S', 5)) "
        "t(train_type, delay_in_min)"
    ).write_parquet(str(src))

    n_rows = extract_month(str(src), str(dst), columns=["train_type", "delay_in_min"])

    kept = duckdb.sql(f"SELECT train_type FROM '{dst}' ORDER BY delay_in_min").fetchall()
    assert kept == [("ICE",), ("IC",), ("EC",)]
    assert n_rows == 3
