import asyncio
import json
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ResultMessage, SystemMessage, TextBlock
from claude_agent_sdk import ResultError

from runner.options import RunConfig, build_options
from runner.run import run, serialize
from runner.watcher import NotebookWatcher


def cfg_with_out(tmp_path: Path) -> RunConfig:
    (tmp_path / "ws").mkdir(exist_ok=True)
    return RunConfig("claude-sonnet-5-5", "high", "p", 1000, 100.0, False,
                     workspace=tmp_path / "ws", out_dir=tmp_path)


INIT = SystemMessage(subtype="init", data={"type": "system", "subtype": "init",
                                          "claude_code_version": "2.1.316", "skills": []})
REPLY = AssistantMessage(content=[TextBlock(text="hi")], model="claude-sonnet-5-5")


async def fake_query_hitting_cap(prompt, options):
    yield INIT
    yield REPLY
    raise ResultError("Reached maximum number of turns",
                      data={"subtype": "error_max_turns", "num_turns": 2, "terminal_reason": "max_turns"})


async def fake_query_success(prompt, options):
    yield INIT
    yield REPLY
    yield ResultMessage(subtype="success", duration_ms=1200, duration_api_ms=900, is_error=False,
                        num_turns=1, session_id="s", total_cost_usd=0.01,
                        usage={"input_tokens": 10, "output_tokens": 5})


async def fake_query_crashing(prompt, options):
    yield INIT
    raise RuntimeError("CLI exited")


def test_options_match_the_spec(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    o = build_options(RunConfig("claude-sonnet-5-5", "high", "p", 1000, 100.0, False))
    assert o.model == "claude-sonnet-5-5" and str(o.cwd) == "/home/analyst/work"
    assert o.system_prompt == {"type": "preset", "preset": "claude_code"}
    assert o.setting_sources == ["project"] and o.permission_mode == "bypassPermissions"
    assert o.max_turns == 1000 and o.max_budget_usd == 100.0 and o.effort == "high"
    assert o.env["CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT"] == "1" and o.env["DISABLE_AUTOUPDATER"] == "1"
    assert o.env["CLAUDE_CODE_ENABLE_TELEMETRY"] == "1"
    assert o.env["OTEL_LOGS_EXPORTER"] == "none" and o.env["OTEL_METRICS_EXPORTER"] == "none"
    assert o.env["OTEL_LOG_RAW_API_BODIES"] == "file:/out/private/bodies"
    assert o.env["PATH"].startswith("/opt/venv/bin:")
    assert o.env["HOME"] == "/home/analyst"
    assert o.disallowed_tools == []


def test_options_pass_only_the_signin_variable_present(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "tok")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    o = build_options(RunConfig("claude-sonnet-5-5", "high", "p", 1000, 100.0, False))
    assert o.env["CLAUDE_CODE_OAUTH_TOKEN"] == "tok" and "ANTHROPIC_API_KEY" not in o.env


def test_task_writer_has_no_web_tools():
    o = build_options(RunConfig("claude-opus-5-5", "high", "p", 1000, 100.0, True))
    assert set(o.disallowed_tools) == {"WebSearch", "WebFetch"}


def test_cap_mid_stream_keeps_log_and_status(tmp_path):
    result = asyncio.run(run(cfg_with_out(tmp_path), query_fn=fake_query_hitting_cap))
    assert result["status"] == "error_max_turns"
    assert len((tmp_path / "messages.jsonl").read_text().splitlines()) == 2
    assert json.loads((tmp_path / "result.json").read_text())["status"] == "error_max_turns"
    assert json.loads((tmp_path / "init.json").read_text())["claude_code_version"] == "2.1.316"


def test_success_records_cost_turns_and_signin_name_only(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-secret")
    result = asyncio.run(run(cfg_with_out(tmp_path), query_fn=fake_query_success))
    assert result["status"] == "success" and result["num_turns"] == 1
    assert result["total_cost_usd"] == 0.01 and result["usage"]["output_tokens"] == 5
    assert result["signin_method"] == "CLAUDE_CODE_OAUTH_TOKEN"
    assert "sk-secret" not in (tmp_path / "result.json").read_text()


def test_crash_is_recorded_as_error(tmp_path):
    result = asyncio.run(run(cfg_with_out(tmp_path), query_fn=fake_query_crashing))
    assert result["status"] == "error" and "CLI exited" in result["error"]
    assert len((tmp_path / "messages.jsonl").read_text().splitlines()) == 1


def test_serialize_adds_type_and_nests_blocks():
    d = serialize(REPLY)
    assert d["_type"] == "AssistantMessage" and d["content"][0]["text"] == "hi"


def test_watcher_snapshots_only_valid_changed_json(tmp_path):
    nb = tmp_path / "analysis.ipynb"
    w = NotebookWatcher(nb, tmp_path / "snaps")
    assert w.poll_once() is False                      # no file yet
    nb.write_text('{"cells": [], "nbformat": 4')
    assert w.poll_once() is False                      # half-written
    nb.write_text('{"cells": [], "nbformat": 4, "nbformat_minor": 5, "metadata": {}}')
    assert w.poll_once() is True
    assert w.poll_once() is False                      # unchanged
    assert sorted(p.name for p in (tmp_path / "snaps").glob("*.ipynb")) == ["snap-0001.ipynb"]
    line = json.loads((tmp_path / "snaps/snapshots.jsonl").read_text())
    assert line["seq"] == 1 and line["seen_at"].endswith("Z")


def test_run_snapshots_the_notebook_written_during_the_run(tmp_path):
    cfg = cfg_with_out(tmp_path)

    async def writes_notebook(prompt, options):
        yield INIT
        (cfg.workspace / "analysis.ipynb").write_text('{"cells": [], "metadata": {}}')
        yield REPLY

    asyncio.run(run(cfg, query_fn=writes_notebook))
    assert (tmp_path / "snapshots/snap-0001.ipynb").exists()


def test_wall_clock_cap_is_enforced_by_the_runner(tmp_path):
    cfg = cfg_with_out(tmp_path)
    cfg.wall_clock_s = 1

    async def never_ends(prompt, options):
        yield INIT
        await asyncio.sleep(3600)
        yield REPLY

    result = asyncio.run(run(cfg, query_fn=never_ends))
    assert result["status"] == "error_wall_clock"
    assert json.loads((tmp_path / "result.json").read_text())["status"] == "error_wall_clock"
    assert len((tmp_path / "messages.jsonl").read_text().splitlines()) == 1


def test_wall_clock_defaults_to_four_hours():
    assert RunConfig("m", "high", "p", 1, 1.0, False).wall_clock_s == 14400


def test_termination_signal_still_writes_result(tmp_path):
    cfg = cfg_with_out(tmp_path)

    async def never_ends(prompt, options):
        yield INIT
        await asyncio.sleep(3600)
        yield REPLY

    async def cancel_soon():
        task = asyncio.create_task(run(cfg, query_fn=never_ends))
        await asyncio.sleep(0.3)
        task.cancel()  # what the SIGTERM handler does
        return await task

    assert asyncio.run(cancel_soon())["status"] == "error_terminated"
    assert json.loads((tmp_path / "result.json").read_text())["status"] == "error_terminated"


def test_workspace_watcher_follows_every_notebook(tmp_path):
    from runner.watcher import WorkspaceWatcher
    ws, snaps = tmp_path / "ws", tmp_path / "snaps"
    (ws / "sub").mkdir(parents=True)
    (ws / ".ipynb_checkpoints").mkdir()
    nb = '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}'
    for name in ("analysis.ipynb", "analysis.nbconvert.ipynb", "sub/Other.ipynb",
                 ".ipynb_checkpoints/analysis-checkpoint.ipynb"):
        (ws / name).write_text(nb)
    w = WorkspaceWatcher(ws, snaps)
    w.poll_once()
    found = sorted(str(p.relative_to(snaps)) for p in snaps.rglob("snap-*.ipynb"))
    assert found == ["other/analysis.nbconvert.ipynb/snap-0001.ipynb",
                     "other/sub/Other.ipynb/snap-0001.ipynb", "snap-0001.ipynb"]
