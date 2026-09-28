"""Download monthly Deutsche Bahn stop data and keep only long-distance trains.

Source: piebro/deutsche-bahn-data on Hugging Face (data by Deutsche Bahn, CC BY 4.0).
Incremental: months already in data/raw/ are skipped, so this is safe to run on a schedule.

    uv run python -m ingest.fetch_months --months 2026-06 2026-08
    uv run python -m ingest.fetch_months --latest 1
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from huggingface_hub import HfApi

REPO_ID = "piebro/deutsche-bahn-data"
MONTHLY_DIR = "monthly_processed_data"
RAW_DIR = Path("data/raw")
MANIFEST = RAW_DIR / "_manifest.json"
LONG_DISTANCE = ("ICE", "IC", "EC")
COLUMNS = [
    "id",
    "eva",
    "station_name",
    "train_type",
    "train_number",
    "train_line_ride_id",
    "train_line_station_num",
    "delay_in_min",
    "arrival_planned_time",
    "arrival_change_time",
    "departure_planned_time",
    "departure_change_time",
    "arrival_is_canceled",
    "departure_is_canceled",
    "is_additional_stop",
    "is_replacement_train",
]


def month_from_path(path: str) -> str | None:
    match = re.search(rf"{MONTHLY_DIR}/data-(\d{{4}}-\d{{2}})\.parquet$", path)
    return match.group(1) if match else None


def months_to_fetch(
    available: list[str],
    existing: list[str],
    requested: list[str] | None = None,
    latest: int | None = None,
) -> list[str]:
    if requested is not None:
        missing = sorted(set(requested) - set(available))
        if missing:
            raise ValueError(f"Months not available upstream: {', '.join(missing)}")
        wanted = requested
    else:
        wanted = sorted(available)[-latest:]
    return sorted(m for m in wanted if m not in existing)


def source_url(month: str, revision: str) -> str:
    return (
        f"https://huggingface.co/datasets/{REPO_ID}/resolve/{revision}/"
        f"{MONTHLY_DIR}/data-{month}.parquet"
    )


def extract_month(src: str, dst: str, columns: list[str] = COLUMNS) -> int:
    """Copy long-distance rows from src to a local parquet file; return the row count."""
    types = ", ".join(f"'{t}'" for t in LONG_DISTANCE)
    con = duckdb.connect()
    con.sql(
        f"COPY (SELECT {', '.join(columns)} FROM '{src}' WHERE train_type IN ({types})) "
        f"TO '{dst}' (FORMAT parquet)"
    )
    return con.sql(f"SELECT count(*) FROM '{dst}'").fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--months", nargs="+", help="months to fetch, e.g. 2026-06 2026-08")
    group.add_argument("--latest", type=int, help="fetch the newest N months available")
    args = parser.parse_args()

    api = HfApi()
    revision = api.dataset_info(REPO_ID).sha
    tree = api.list_repo_tree(
        REPO_ID, path_in_repo=MONTHLY_DIR, repo_type="dataset", revision=revision
    )
    available = [m for m in (month_from_path(f.path) for f in tree) if m]

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    todo = months_to_fetch(available, list(manifest), args.months, args.latest)
    if not todo:
        print("Nothing to fetch: all requested months are already in data/raw/.")
        return

    for month in todo:
        dst = RAW_DIR / f"stops-{month}.parquet"
        print(f"Fetching {month} (revision {revision[:8]}) ...", flush=True)
        n_rows = extract_month(source_url(month, revision), str(dst))
        manifest[month] = {
            "file": dst.name,
            "rows": n_rows,
            "source_revision": revision,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2))
        print(f"  wrote {dst} ({n_rows:,} rows)")


if __name__ == "__main__":
    main()
