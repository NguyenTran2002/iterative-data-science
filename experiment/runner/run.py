"""Run one autonomous Claude Code session through the Agent SDK and keep everything.

Writes to the output folder: messages.jsonl (appended as each message arrives),
init.json, result.json, stderr.txt, snapshots/ and, inside the image, packages.txt.
A cap or a crash is recorded as the run's status; the log stays intact.
"""
import argparse
import asyncio
import dataclasses
import contextlib
import json
import signal
import subprocess
import sys
from pathlib import Path

from claude_agent_sdk import ResultError, ResultMessage, SystemMessage, query

from runner.options import RunConfig, build_options, signin_method
from runner.watcher import NotebookWatcher

CAPS = ("error_max_turns", "error_max_budget_usd")
ANALYSIS_PIP = Path("/opt/venv/bin/pip")


def serialize(message) -> dict:
    d = dataclasses.asdict(message) if dataclasses.is_dataclass(message) else {"repr": repr(message)}
    d["_type"] = type(message).__name__
    return d


def status_of(subtype: str | None, is_error: bool) -> str:
    if subtype in CAPS:
        return subtype
    return "success" if subtype == "success" and not is_error else "error"


async def run(cfg: RunConfig, query_fn=query) -> dict:
    out = cfg.out_dir
    (out / "private/bodies").mkdir(parents=True, exist_ok=True)
    result = {"status": "error", "num_turns": None, "duration_ms": None, "total_cost_usd": None,
              "usage": None, "signin_method": signin_method()}
    watcher = NotebookWatcher(cfg.workspace / "analysis.ipynb", out / "snapshots")
    watcher.start()
    stream = query_fn(prompt=cfg.prompt, options=build_options(cfg))
    log = (out / "messages.jsonl").open("a")
    try:
        async with asyncio.timeout(cfg.wall_clock_s):
            async for message in stream:
                log.write(json.dumps(serialize(message), default=str) + "\n")
                log.flush()
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    (out / "init.json").write_text(json.dumps(message.data, indent=2, default=str))
                elif isinstance(message, ResultMessage):
                    result |= {"status": status_of(message.subtype, message.is_error),
                               "subtype": message.subtype, "num_turns": message.num_turns,
                               "duration_ms": message.duration_ms,
                               "total_cost_usd": message.total_cost_usd, "usage": message.usage,
                               "model_usage": message.model_usage}
    except ResultError as e:
        data = e.data
        result |= {"status": status_of(e.subtype, True), "subtype": e.subtype,
                   "terminal_reason": e.terminal_reason, "errors": e.errors, "error": str(e)}
        for key in ("num_turns", "duration_ms", "total_cost_usd", "usage"):
            if data.get(key) is not None:
                result[key] = data[key]
    except TimeoutError:
        result |= {"status": "error_wall_clock", "error": f"wall clock of {cfg.wall_clock_s} s reached"}
    except asyncio.CancelledError:  # SIGTERM from `docker stop`
        result |= {"status": "error_terminated", "error": "terminated by signal"}
    except Exception as e:  # a crash is a result too; keep what was logged
        result |= {"status": "error", "error": f"{type(e).__name__}: {e}"}
    finally:
        log.close()
        (out / "result.json").write_text(json.dumps(result, indent=2, default=str))
        with contextlib.suppress(BaseException):
            await asyncio.wait_for(stream.aclose(), 30)
        watcher.stop()
    return result


async def _run_until_signalled(cfg: RunConfig) -> dict:
    """Run, turning SIGTERM into a cancellation so result.json is still written."""
    task = asyncio.current_task()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    return await run(cfg)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--effort", required=True)
    p.add_argument("--prompt-file", required=True, type=Path)
    p.add_argument("--max-turns", required=True, type=int)
    p.add_argument("--max-budget-usd", required=True, type=float)
    p.add_argument("--wall-clock-s", type=int, default=14400)
    p.add_argument("--disallow-web", action="store_true")
    a = p.parse_args()
    cfg = RunConfig(a.model, a.effort, a.prompt_file.read_text(), a.max_turns, a.max_budget_usd,
                    a.disallow_web, wall_clock_s=a.wall_clock_s)
    result = asyncio.run(_run_until_signalled(cfg))
    if ANALYSIS_PIP.exists():
        freeze = subprocess.run([ANALYSIS_PIP, "freeze"], capture_output=True, text=True)
        (cfg.out_dir / "packages.txt").write_text(freeze.stdout)
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
