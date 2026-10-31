import json
from pathlib import Path

from data.dataset_md import render

METADATA_FIXTURE = json.loads((Path(__file__).parent / "fixtures/views_wrvz-psew.json").read_text())
WEEK = {"monday": "2023-06-05", "sunday": "2023-06-11", "rows": 150573}


def test_render_is_verbatim_and_has_no_rows():
    md = render(METADATA_FIXTURE, WEEK)
    assert METADATA_FIXTURE["description"] in md
    for c in METADATA_FIXTURE["columns"]:
        if c["fieldName"].startswith(":"):
            continue
        assert c["fieldName"] in md and c["dataTypeName"] in md and c.get("description", "") in md
    assert "2023-06-05" in md and "150,573" in md and "trips.csv" in md


def test_render_leaves_out_portal_computed_columns():
    # columns whose name starts with ":" are portal internals and are not in the CSV
    assert ":@computed_region" not in render(METADATA_FIXTURE, WEEK)
