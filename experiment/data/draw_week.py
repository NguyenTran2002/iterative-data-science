"""Draw the one week of 2023 taxi trips the experiment uses.

The week is fixed by a seed string committed before the draw, so nobody picks it.
SHA-256 is used instead of a random-number generator so the result cannot change
across Python versions. Run once: the output is final and is never overwritten.
"""
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SEED = "chicago-taxi-2023-week/2026-10-31"
WEEK_JSON = Path(__file__).with_name("week.json")


def candidate_weeks(year: int = 2023) -> list[tuple[date, date]]:
    """Monday-to-Sunday weeks lying fully inside `year`, minus the first and the last."""
    monday = date(year, 1, 1)
    monday += timedelta(days=-monday.weekday() % 7)
    weeks = []
    while (sunday := monday + timedelta(days=6)).year == year:
        weeks.append((monday, sunday))
        monday += timedelta(days=7)
    return weeks[1:-1]


def pick_index(seed: str, n: int) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest(), 16) % n


def draw(seed: str = SEED) -> dict:
    weeks = candidate_weeks(2023)
    i = pick_index(seed, len(weeks))
    monday, sunday = weeks[i]
    return {"seed": seed, "index": i, "monday": monday.isoformat(), "sunday": sunday.isoformat()}


def main() -> None:
    if WEEK_JSON.exists():
        sys.exit(f"{WEEK_JSON} already exists; the draw is final and is never redone.")
    week = draw()
    WEEK_JSON.write_text(json.dumps(week, indent=2) + "\n")
    print(f"Drew week {week['index']}: {week['monday']} to {week['sunday']}")


if __name__ == "__main__":
    main()
