"""Download the drawn week of taxi trips and pin it by checksum.

The first fetch records the row count, byte size and SHA-256 in week.json.
Every later fetch must reproduce that checksum exactly, or the script stops.
"""
import csv
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from data.draw_week import WEEK_JSON

DATASET = "wrvz-psew"
LIMIT = 2_000_000
CSV = Path(__file__).with_name("trips.csv")
ATTEMPTS = 3


def soql_url(monday: date, sunday: date, limit: int = LIMIT) -> str:
    where = (f"trip_start_timestamp between '{monday.isoformat()}T00:00:00' "
             f"and '{sunday.isoformat()}T23:59:59'")
    query = urllib.parse.urlencode({"$where": where, "$order": "trip_id", "$limit": limit},
                                   quote_via=urllib.parse.quote)
    return f"https://data.cityofchicago.org/resource/{DATASET}.csv?{query}"


def check_rows(n_rows: int, limit: int) -> None:
    """A row count at the limit means the download may have been cut short."""
    if n_rows >= limit:
        raise ValueError(f"{n_rows} rows reached the limit of {limit}; the week may be truncated")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(csv_path: Path, expected_sha256: str) -> None:
    actual = sha256(csv_path)
    if actual != expected_sha256:
        raise ValueError(f"{csv_path} has SHA-256 {actual}, expected {expected_sha256}")


def count_rows(csv_path: Path) -> int:
    with csv_path.open(newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def download(url: str, part: Path) -> None:
    for attempt in range(1, ATTEMPTS + 1):
        print(f"Downloading (attempt {attempt} of {ATTEMPTS}); this takes a few minutes...", flush=True)
        try:
            with urllib.request.urlopen(url, timeout=600) as r, part.open("wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            return
        except OSError as e:
            print(f"Download failed: {e}", flush=True)
            if attempt == ATTEMPTS:
                raise
            time.sleep(10 * attempt)


def main() -> None:
    week = json.loads(WEEK_JSON.read_text())
    url = soql_url(date.fromisoformat(week["monday"]), date.fromisoformat(week["sunday"]))
    part = CSV.with_suffix(".part")  # checked before it replaces a good copy
    download(url, part)
    rows = count_rows(part)
    check_rows(rows, LIMIT)
    if "sha256" in week:
        verify(part, week["sha256"])
        part.replace(CSV)
        print(f"Checksum verified: {rows:,} rows, SHA-256 {week['sha256']}")
        return
    part.replace(CSV)
    week |= {"rows": rows, "bytes": CSV.stat().st_size, "sha256": sha256(CSV)}
    WEEK_JSON.write_text(json.dumps(week, indent=2) + "\n")
    print(f"Recorded {rows:,} rows, {week['bytes']:,} bytes, SHA-256 {week['sha256']}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        sys.exit(str(e))
