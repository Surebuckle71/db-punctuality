"""Export the dbt marts to data/marts/ so the dashboard runs without the raw data.

uv run python -m analysis.export_marts
"""

import json
from pathlib import Path

import duckdb

WAREHOUSE = "data/warehouse.duckdb"
OUT_DIR = Path("data/marts")
MARTS = ["fct_delay_by_phase", "fct_delay_locations"]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(WAREHOUSE, read_only=True)
    for mart in MARTS:
        dst = OUT_DIR / f"{mart}.parquet"
        con.sql(f"COPY (SELECT * FROM {mart} ORDER BY ALL) TO '{dst}' (FORMAT parquet)")
        print(f"wrote {dst}")

    # record which upstream revision each month came from
    manifest = json.loads(Path("data/raw/_manifest.json").read_text())
    provenance = {
        "source": "Deutsche Bahn Timetables API (CC BY 4.0) via piebro/deutsche-bahn-data",
        "months": {m: {k: v[k] for k in ("source_revision", "rows")} for m, v in manifest.items()},
    }
    (OUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2))
    print(f"wrote {OUT_DIR / 'provenance.json'}")


if __name__ == "__main__":
    main()
