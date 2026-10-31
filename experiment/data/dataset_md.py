"""Write dataset.md, the only thing the clean-room task writer sees.

It holds the portal's public description and column list verbatim, the drawn
week's dates and row count, and the file name the analyst will get. No rows.
"""
import json
import sys
import urllib.request
from pathlib import Path

from data.draw_week import WEEK_JSON
from data.fetch_week import DATASET

METADATA_URL = f"https://data.cityofchicago.org/api/views/{DATASET}.json"


def render(metadata: dict, week: dict) -> str:
    rows = [f"| `{c['fieldName']}` | {c['dataTypeName']} | {c.get('description', '')} |"
            for c in metadata["columns"] if not c["fieldName"].startswith(":")]
    return "\n".join([
        f"# {metadata['name']}",
        "",
        "## Description from the City of Chicago data portal",
        "",
        metadata["description"],
        "",
        "## Columns",
        "",
        "| Column | Type | Description |",
        "|---|---|---|",
        *rows,
        "",
        "## The data you will receive",
        "",
        f"One week of trips, Monday {week['monday']} to Sunday {week['sunday']}: "
        f"{week['rows']:,} rows, in a CSV file named `trips.csv` with the columns above.",
        "",
    ])


def main() -> None:
    out = Path(sys.argv[1])
    with urllib.request.urlopen(METADATA_URL, timeout=60) as r:
        metadata = json.load(r)
    out.write_text(render(metadata, json.loads(WEEK_JSON.read_text())))


if __name__ == "__main__":
    main()
