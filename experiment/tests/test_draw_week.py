import hashlib
import json
from datetime import date

import pytest

from data import draw_week
from data.draw_week import SEED, candidate_weeks, draw, pick_index


def test_candidates_exclude_first_and_last_full_week():
    weeks = candidate_weeks(2023)
    assert len(weeks) == 50
    assert weeks[0] == (date(2023, 1, 9), date(2023, 1, 15))
    assert weeks[-1] == (date(2023, 12, 18), date(2023, 12, 24))
    assert all(m.weekday() == 0 and (s - m).days == 6 for m, s in weeks)


def test_pick_index_is_sha256_mod_n():
    assert pick_index("abc", 50) == int(hashlib.sha256(b"abc").hexdigest(), 16) % 50
    assert pick_index("abc", 50) == pick_index("abc", 50)


def test_seed_is_the_committed_string():
    assert SEED == "chicago-taxi-2023-week/2026-10-31"


def test_draw_returns_the_indexed_week():
    d = draw("abc")
    m, s = candidate_weeks(2023)[pick_index("abc", 50)]
    assert d == {"seed": "abc", "index": pick_index("abc", 50),
                 "monday": m.isoformat(), "sunday": s.isoformat()}


def test_cli_refuses_to_overwrite(tmp_path, monkeypatch):
    out = tmp_path / "week.json"
    out.write_text('{"keep": true}')
    monkeypatch.setattr(draw_week, "WEEK_JSON", out)
    with pytest.raises(SystemExit):
        draw_week.main()
    assert json.loads(out.read_text()) == {"keep": True}


def test_cli_writes_week_json(tmp_path, monkeypatch):
    out = tmp_path / "week.json"
    monkeypatch.setattr(draw_week, "WEEK_JSON", out)
    draw_week.main()
    assert json.loads(out.read_text()) == draw()
