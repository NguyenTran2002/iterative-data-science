import shutil
import subprocess
from pathlib import Path

import pytest

from launch.docker import docker_run_args, wait_all
from launch.scrub import scrub_tree
from launch.signin import signin_env
from launch.workspace import SKILL_MD, build_prompt, prepare_workspace

WRAPPER = Path(__file__).parents[1] / "prompts/wrapper.md"


@pytest.fixture
def csv(tmp_path):
    p = tmp_path / "week.csv"
    p.write_text("trip_id,fare\nA,1.0\n")
    return p


def test_signin_prefers_plan_token():
    assert signin_env({"CLAUDE_CODE_OAUTH_TOKEN": "a", "ANTHROPIC_API_KEY": "b"}) == ("CLAUDE_CODE_OAUTH_TOKEN", "a")
    assert signin_env({"ANTHROPIC_API_KEY": "b"}) == ("ANTHROPIC_API_KEY", "b")
    with pytest.raises(SystemExit, match="CLAUDE_CODE_OAUTH_TOKEN.*ANTHROPIC_API_KEY"):
        signin_env({})


def test_skill_md_is_the_plugin_copy():
    assert SKILL_MD.parts[-5:] == ("plugins", "iterative-data-science", "skills",
                                   "iterative-data-science", "SKILL.md")
    assert SKILL_MD.exists()


def test_workspaces_differ_only_by_skill(csv):
    c = prepare_workspace("control", csv, SKILL_MD)
    s = prepare_workspace("skill", csv, SKILL_MD)
    try:
        assert "iterative" not in str(c) and "iterative" not in str(s)
        assert not (c / ".claude").exists()
        assert (s / ".claude/skills/iterative-data-science/SKILL.md").read_bytes() == SKILL_MD.read_bytes()
        assert (c / "trips.csv").read_bytes() == (s / "trips.csv").read_bytes() == csv.read_bytes()
        assert sorted(p.name for p in c.iterdir()) == ["trips.csv"]
    finally:
        shutil.rmtree(c), shutil.rmtree(s)


def test_workspace_without_csv_holds_only_the_given_files():
    w = prepare_workspace("control", None, SKILL_MD, files={"dataset.md": "# D\n"})
    try:
        assert sorted(p.name for p in w.iterdir()) == ["dataset.md"]
        assert (w / "dataset.md").read_text() == "# D\n"
    finally:
        shutil.rmtree(w)


def test_prompts_differ_only_by_prefix():
    assert build_prompt("control", "W", "B") == "W\n\nB"
    assert build_prompt("skill", "W", "B") == "/iterative-data-science W\n\nB"


def test_wrapper_is_verbatim():
    assert WRAPPER.read_text() == ("The data is in `trips.csv` in this folder. Do the analysis in a "
                                   "Jupyter notebook named `analysis.ipynb` in this folder.")


def test_scrub_redacts_token_in_logs_and_notebooks(tmp_path):
    (tmp_path / "messages.jsonl").write_text('{"x": "TOKEN=sk-secret"}\n')
    (tmp_path / "ws").mkdir()
    (tmp_path / "ws/analysis.ipynb").write_text('{"o": "sk-secret sk-secret"}')
    (tmp_path / "ws/fig.png").write_bytes(b"\x89PNG\x00sk-secret\xff")
    assert scrub_tree(tmp_path, "sk-secret") == 4
    assert all(b"sk-secret" not in p.read_bytes() for p in tmp_path.rglob("*") if p.is_file())
    assert "[REDACTED]" in (tmp_path / "messages.jsonl").read_text()


def test_scrub_refuses_an_empty_secret(tmp_path):
    with pytest.raises(ValueError):
        scrub_tree(tmp_path, "")


def test_docker_args_never_carry_the_secret_value(tmp_path):
    args = docker_run_args("img", tmp_path / "ws", tmp_path / "out", ["--model", "m"],
                           ("CLAUDE_CODE_OAUTH_TOKEN", "sk-secret"))
    assert "sk-secret" not in " ".join(args)
    assert args[:3] == ["docker", "run", "-d"] and "--init" in args
    assert ["-e", "CLAUDE_CODE_OAUTH_TOKEN"] == args[args.index("-e"):args.index("-e") + 2]
    assert f"{tmp_path / 'ws'}:/home/analyst/work" in args and f"{tmp_path / 'out'}:/out" in args
    assert args[-5:] == ["img", "--prompt-file", "/out/prompt.md", "--model", "m"]


def docker_image_present() -> bool:
    return shutil.which("docker") is not None and subprocess.run(
        ["docker", "image", "inspect", "ids-experiment"], capture_output=True).returncode == 0


@pytest.mark.skipif(not docker_image_present(), reason="needs docker and the ids-experiment image")
def test_wait_all_reports_exit_codes_and_stops_on_timeout():
    run = lambda *cmd: subprocess.run(["docker", "run", "-d", "--entrypoint", cmd[0], "ids-experiment",
                                       *cmd[1:]],
                                      capture_output=True, text=True, check=True).stdout.strip()
    done, slow = run("sh", "-c", "exit 3"), run("sleep", "60")
    try:
        assert wait_all([done, slow], timeout_s=5, stop_grace_s=1) == {done: "exit:3", slow: "timeout"}
    finally:
        subprocess.run(["docker", "rm", "-f", done, slow], capture_output=True)


def test_collect_side_scrubs_before_copying_and_drops_the_data(tmp_path):
    from launch.collect import collect_side
    out, ws, dest = tmp_path / "out", tmp_path / "ws", tmp_path / "runs/x/skill"
    (out / "private/bodies").mkdir(parents=True)
    (out / "messages.jsonl").write_text('{"env": "sk-secret"}\n')
    (out / "private/bodies/1.json").write_text('{"h": "sk-secret"}')
    ws.mkdir()
    (ws / "trips.csv").write_text("a\n")
    (ws / "analysis.ipynb").write_text("{}")
    assert collect_side(out, ws, dest, "sk-secret") == 2
    assert not (dest / "workspace/trips.csv").exists()
    assert (dest / "workspace/analysis.ipynb").exists() and (dest / "private/bodies/1.json").exists()
    assert all(b"sk-secret" not in p.read_bytes() for p in dest.rglob("*") if p.is_file())


def test_collect_side_keeps_symlinks_as_links(tmp_path):
    from launch.collect import collect_side
    out, ws, dest = tmp_path / "out", tmp_path / "ws", tmp_path / "runs/x/control"
    out.mkdir()
    ws.mkdir()
    (ws / "dangling").symlink_to("/home/analyst/work/.venv/bin/python")
    (ws / "env").symlink_to("/proc/self/environ")
    collect_side(out, ws, dest, "sk-secret")
    assert (dest / "workspace/dangling").is_symlink() and (dest / "workspace/env").is_symlink()


def test_scrub_redacts_partial_and_token_shaped_strings(tmp_path):
    secret = "sk-ant-oat01-" + "abcdefghij" * 9
    (tmp_path / "a.txt").write_text(f"prefix {secret[:40]}... and {secret[30:70]} end")
    (tmp_path / "b.txt").write_text("other sk-ant-api03-ZZZZZZZZZZZZZZZZ here")
    assert scrub_tree(tmp_path, secret) >= 3
    a, b = (tmp_path / "a.txt").read_text(), (tmp_path / "b.txt").read_text()
    for i in range(len(secret) - 15):
        assert secret[i:i + 16] not in a
    assert "sk-ant-api03-ZZZZ" not in b and "other" in b and "end" in a


def test_data_files_and_large_files_are_held_back(tmp_path):
    from launch.collect import hold_back
    run = tmp_path / "run"
    (run / "skill/workspace").mkdir(parents=True)
    (run / "skill/workspace/trips_clean.parquet").write_bytes(b"x" * 10)
    (run / "skill/workspace/fig.png").write_bytes(b"x" * 10)
    (run / "skill/messages.jsonl").write_bytes(b"x" * 30)
    held = hold_back(run, max_bytes=20)
    assert [h["path"] for h in held] == ["skill/messages.jsonl", "skill/workspace/trips_clean.parquet"]
    assert all(len(h["sha256"]) == 64 and h["bytes"] > 0 for h in held)
    assert (run / ".gitignore").read_text().splitlines() == ["/skill/messages.jsonl",
                                                             "/skill/workspace/trips_clean.parquet"]


def test_check_prompts_have_the_pairs_shape():
    import run_pair
    prompts = {side: build_prompt(side, *run_pair.CHECK_PARTS) for side in ("control", "skill")}
    assert "\n\n" in prompts["control"] and prompts["skill"] == "/iterative-data-science " + prompts["control"]


def test_both_sides_get_the_same_dataset_md(tmp_path, monkeypatch, csv):
    import run_pair
    (tmp_path / "dataset.md").write_text("# Columns\n")
    monkeypatch.setattr(run_pair, "TASK", tmp_path)
    workspaces = run_pair.make_workspaces(csv)
    try:
        for side in ("control", "skill"):
            assert (workspaces[side] / "dataset.md").read_text() == "# Columns\n"
            assert (workspaces[side] / "trips.csv").exists()
    finally:
        for w in workspaces.values():
            shutil.rmtree(w)
