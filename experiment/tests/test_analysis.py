import json
import shutil
import subprocess
from pathlib import Path

import nbformat
import pytest
from nbformat.v4 import new_code_cell, new_notebook

from analysis.metrics import compute, reexecute
from analysis.system_prompt import extract_system_prompt, first_request_has

SIDE = Path(__file__).parent / "fixtures/side"
BILLING = "x-anthropic-billing-header: cc_version=2.1.316.b94; cc_entrypoint=sdk-py; cch=00000;"


def test_counts_on_the_fixture_side():
    m = compute(SIDE)
    assert m["notebook_present"] is True
    assert m["executions"] == 2 and m["batch_sizes"] == [2, 1]
    assert m["mixed_output_cells"] == 1 and m["cell_errors"] == 1 and m["inline_images"] == 1
    assert m["figures_created"] == 1 and m["figures_opened"] == 1
    assert m["rework_cells"] == 1 and m["tool_errors"] == 1
    assert m["package_installs"] == 1 and m["web_searches"] == 0 and m["web_fetches"] == 0
    assert m["turns"] == 5 and m["duration_s"] == 60.0 and m["cost_usd"] == 0.5
    assert m["input_tokens"] == 100 and m["output_tokens"] == 50
    assert m["cache_read_input_tokens"] == 1000 and m["cache_creation_input_tokens"] == 200


def test_outside_activity_is_listed(tmp_path):
    side = tmp_path / "side"
    shutil.copytree(SIDE, side)
    with (side / "messages.jsonl").open("a") as f:
        f.write(json.dumps({"_type": "AssistantMessage", "content": [
            {"id": "w", "name": "WebSearch", "input": {"query": "chicago taxi tips"}},
            {"id": "f", "name": "WebFetch", "input": {"url": "https://example.org", "prompt": "x"}}]}) + "\n")
    m = compute(side)
    assert m["web_searches"] == 1 and m["web_fetches"] == 1
    assert [a["tool"] for a in m["outside_activity"]] == ["Bash", "WebSearch", "WebFetch"]


def test_side_without_a_notebook(tmp_path):
    side = tmp_path / "side"
    side.mkdir()
    shutil.copy(SIDE / "messages.jsonl", side)
    shutil.copy(SIDE / "result.json", side)
    m = compute(side)
    assert m["notebook_present"] is False
    assert m["executions"] == 0 and m["batch_sizes"] == [] and m["mixed_output_cells"] == 0
    assert m["cell_errors"] == 0 and m["rework_cells"] == 0 and m["figures_created"] == 0


def test_cells_without_ids_are_matched_by_position(tmp_path):
    side = tmp_path / "side"
    shutil.copytree(SIDE, side)
    for p in (side / "snapshots").glob("*.ipynb"):
        nb = json.loads(p.read_text())
        for c in nb["cells"]:
            c.pop("id", None)
        nb["nbformat_minor"] = 4
        p.write_text(json.dumps(nb))
    m = compute(side)
    assert m["executions"] == 2 and m["batch_sizes"] == [2, 1] and m["rework_cells"] == 1


def write_bodies(d: Path, billing: str) -> Path:
    d.mkdir()
    reqs = [("generate_session_title", "claude-haiku-5-5", "title prompt", "hi"),
            ("sdk", "claude-sonnet-5-5", "You are a Claude agent.", "/iterative-data-science go\n# Iterative Data Science Workflow"),
            ("sdk", "claude-sonnet-5-5", "later", "later")]
    with (d / "index.jsonl").open("w") as idx:
        for i, (src, model, system, user) in enumerate(reqs):
            body = {"system": [{"type": "text", "text": billing}, {"type": "text", "text": system},
                               {"type": "text", "text": "Second block."}],
                    "messages": [{"role": "user", "content": [{"type": "text", "text": user}]}]}
            (d / f"{i}.request.json").write_text(json.dumps(body))
            idx.write(json.dumps({"query_source": src, "model": model, "request_file": f"{i}.request.json"}) + "\n")
    return d


def test_system_prompt_is_the_main_thread_one_without_billing(tmp_path):
    a = extract_system_prompt(write_bodies(tmp_path / "a", BILLING))
    b = extract_system_prompt(write_bodies(tmp_path / "b", BILLING.replace("b94", "c07")))
    assert a == b == "You are a Claude agent.\n\nSecond block."


def test_first_request_has_marker(tmp_path):
    bodies = write_bodies(tmp_path / "a", BILLING)
    assert first_request_has(bodies, "# Iterative Data Science Workflow") is True
    assert first_request_has(bodies, "never there") is False


def docker_image_present() -> bool:
    return shutil.which("docker") is not None and subprocess.run(
        ["docker", "image", "inspect", "ids-experiment"], capture_output=True).returncode == 0


@pytest.mark.skipif(not docker_image_present(), reason="needs docker and the ids-experiment image")
def test_reexecute_in_a_fresh_container(tmp_path):
    good, bad = tmp_path / "good", tmp_path / "bad"
    for d, src in ((good, "import pandas as pd\nprint(len(pd.read_csv('trips.csv')))"), (bad, "1/0")):
        d.mkdir()
        nbformat.write(new_notebook(cells=[new_code_cell(src)]), d / "analysis.ipynb")
    csv = tmp_path / "week.csv"
    csv.write_text("trip_id\nA\n")
    assert reexecute(good / "analysis.ipynb", "ids-experiment", csv) is True
    assert reexecute(bad / "analysis.ipynb", "ids-experiment", csv) is False


def test_a_snapshot_that_is_json_but_not_a_notebook_is_skipped(tmp_path):
    side = tmp_path / "side"
    shutil.copytree(SIDE, side)
    (side / "snapshots/snap-0004.ipynb").write_text('{"cells": "oops"}')
    m = compute(side)
    assert m["executions"] == 2 and m["batch_sizes"] == [2, 1]


def raw_nb(cells, minor=5):
    return json.dumps({"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": minor})


def code(src, count=None, outputs=(), cid=None):
    c = {"cell_type": "code", "source": src, "metadata": {}, "execution_count": count, "outputs": list(outputs)}
    if cid:
        c["id"] = cid
    return c


OUT = {"output_type": "stream", "name": "stdout", "text": "1\n"}
OUT2 = {"output_type": "stream", "name": "stdout", "text": "2\n"}


def side_with_snapshots(tmp_path, notebooks):
    side = tmp_path / "side"
    (side / "snapshots").mkdir(parents=True)
    for i, text in enumerate(notebooks, 1):
        (side / f"snapshots/snap-{i:04d}.ipynb").write_text(text)
    return side


def test_clearing_outputs_is_not_an_execution(tmp_path):
    # NotebookEdit replaces a cell's source and clears its outputs and execution count
    side = side_with_snapshots(tmp_path, [
        raw_nb([code("x = 1", 1, cid="a"), code("print(x)", 2, [OUT], cid="b")]),
        raw_nb([code("x = 1", 1, cid="a"), code("print(x + 1)", None, cid="b")]),
        raw_nb([code("x = 1", 1, cid="a"), code("print(x + 1)", 3, [OUT2], cid="b")]),
    ])
    m = compute(side)
    assert m["executions"] == 2 and m["batch_sizes"] == [2, 1] and m["rework_cells"] == 1


def test_cells_without_ids_in_a_v4_5_notebook_match_by_position(tmp_path):
    # nbformat would invent fresh random IDs on every read; the raw file has none
    side = side_with_snapshots(tmp_path, [
        raw_nb([code("x = 1"), code("print(x)")]),
        raw_nb([code("x = 1", 1), code("print(x)", 2, [OUT])]),
        raw_nb([code("x = 1", 1), code("print(x + 1)", 3, [OUT2])]),
    ])
    m = compute(side)
    assert m["executions"] == 2 and m["batch_sizes"] == [2, 1] and m["rework_cells"] == 1


def test_final_notebook_with_cells_missing_outputs(tmp_path):
    side = tmp_path / "side"
    (side / "workspace").mkdir(parents=True)
    cell = code("x = 1")
    del cell["outputs"]
    (side / "workspace/analysis.ipynb").write_text(raw_nb([cell]))
    m = compute(side)
    assert m["notebook_valid"] is True and m["mixed_output_cells"] == 0 and m["cell_errors"] == 0


def test_final_notebook_that_is_not_json(tmp_path):
    side = tmp_path / "side"
    (side / "workspace").mkdir(parents=True)
    (side / "workspace/analysis.ipynb").write_text("{not json")
    m = compute(side)
    assert m["notebook_present"] is True and m["notebook_valid"] is False
    assert m["mixed_output_cells"] == 0 and m["inline_images"] == 0


def test_other_notebooks_are_listed(tmp_path):
    side = tmp_path / "side"
    shutil.copytree(SIDE, side)
    (side / "snapshots/other/analysis.nbconvert.ipynb").mkdir(parents=True)
    (side / "snapshots/other/analysis.nbconvert.ipynb/snap-0001.ipynb").write_text("{}")
    (side / "workspace/scratch.ipynb").write_text("{}")
    assert compute(side)["other_notebooks"] == ["analysis.nbconvert.ipynb", "scratch.ipynb"]


def test_added_after_runs_measures_are_kept_apart(tmp_path):
    side = tmp_path / "side"
    shutil.copytree(SIDE, side)
    (side / "packages.txt").write_text("pandas==3.1.0\npyarrow==20.0.0\n")
    with (side / "messages.jsonl").open("a") as f:
        f.write(json.dumps({"_type": "AssistantMessage", "content": [
            {"id": "c1", "name": "Bash", "input": {"command": "curl -sO https://example.org/x.csv"}},
            {"id": "n1", "name": "Read", "input": {"file_path": "/home/analyst/work/analysis.ipynb"}},
            {"id": "o1", "name": "Bash", "input": {"command": "ls /out"}}]}) + "\n")
        f.write(json.dumps({"_type": "UserMessage", "content": [
            {"tool_use_id": "n1", "content": [{"type": "text", "text": "cell"}, {"type": "image", "source": {}}]}]}) + "\n")
    nb = json.loads((side / "snapshots/snap-0002.ipynb").read_text())
    nb["cells"].append({"cell_type": "code", "source": "%pip install pyarrow", "metadata": {},
                        "execution_count": None, "outputs": []})
    (side / "snapshots/snap-0002.ipynb").write_text(json.dumps(nb))
    late = compute(side, pinned={"pandas": "3.1.0"})["added_after_runs"]
    assert late["packages_not_in_image"] == ["pyarrow==20.0.0"]
    assert late["notebook_install_cells"] == 1
    assert late["download_commands"] == 1
    assert late["images_seen_by_source"] == {"image_file": 1, "notebook": 1}
    assert late["tool_calls_touching_out"] == 1
    assert late["skill_text_in_tool_results"] is False



def test_added_after_runs_batch_sizes_match_cells_by_source(tmp_path):
    # a notebook regenerated with fresh IDs each time: same code, new IDs
    side = side_with_snapshots(tmp_path, [
        raw_nb([code("x = 1", 1, cid="a1"), code("print(x)", 2, [OUT], cid="b1")]),
        raw_nb([code("x = 1", 1, cid="a2"), code("print(x)", 2, [OUT], cid="b2"),
                code("print(x + 1)", 3, [OUT2], cid="c2")]),
    ])
    m = compute(side, pinned={})
    assert m["batch_sizes"] == [2, 3]                                  # committed: by ID
    assert m["added_after_runs"]["batch_sizes_by_source"] == [2, 1]    # by code text
