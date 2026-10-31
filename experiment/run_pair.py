"""Run one pair: the same task with and without the skill, in two fresh containers.

    uv run python run_pair.py           the pair (needs experiment/task/brief.md)
    uv run python run_pair.py --check   a trivial prompt per side, to compare system prompts

Sign-in comes from CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY in this shell. The
value is passed to the containers by name and redacted from every output file.
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from data.draw_week import WEEK_JSON
from data.fetch_week import CSV, verify
from launch.collect import collect_side
from launch.docker import start, wait_all
from launch.signin import signin_env
from launch.workspace import REPO, SKILL_COMMAND, SKILL_MD, build_prompt, prepare_workspace

HERE = Path(__file__).resolve().parent
IMAGE = "ids-experiment"
MODEL, EFFORT = "claude-sonnet-5-5", "high"
MAX_TURNS, MAX_BUDGET_USD, WALL_CLOCK_S = 1000, 100.0, 14400
CHECK_PROMPT = "Reply with exactly: OK"
SIDES = ("control", "skill")


def utc_now(fmt: str = "%Y-%m-%dT%H:%M:%S.%fZ") -> str:
    s = datetime.now(timezone.utc).strftime(fmt)
    return s[:-4] + "Z" if fmt.endswith(".%fZ") else s


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_image() -> str:
    subprocess.run(["docker", "build", "-q", "-t", IMAGE, str(HERE)], check=True,
                   stdout=subprocess.DEVNULL)
    return subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}}", IMAGE],
                          capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="trivial prompt, to compare system prompts")
    check = p.parse_args().check

    week = json.loads(WEEK_JSON.read_text())
    verify(CSV, week["sha256"])
    signin = signin_env(os.environ)
    if check:
        prompts = {"control": CHECK_PROMPT, "skill": f"{SKILL_COMMAND} {CHECK_PROMPT}"}
        run_args = ["--max-turns", "2", "--max-budget-usd", "1"]
    else:
        brief = (HERE / "task/brief.md").read_text()
        wrapper = (HERE / "prompts/wrapper.md").read_text()
        prompts = {side: build_prompt(side, wrapper, brief) for side in SIDES}
        run_args = ["--max-turns", str(MAX_TURNS), "--max-budget-usd", str(MAX_BUDGET_USD)]
    run_args = ["--model", MODEL, "--effort", EFFORT, *run_args]

    image_id = build_image()
    run_id = ("check-" if check else "") + utc_now("%Y-%m-%dT%H%MZ")
    run_dir = REPO / "runs" / run_id
    if run_dir.exists():
        raise SystemExit(f"{run_dir} already exists")

    workspaces = {side: prepare_workspace(side, CSV, SKILL_MD) for side in SIDES}
    outs = {side: Path(tempfile.mkdtemp(prefix="out-")) for side in SIDES}
    ids, started = {}, {}
    for side in SIDES:  # back to back, so both start within a second
        started[side] = utc_now()
        ids[side] = start(IMAGE, workspaces[side], outs[side], prompts[side], run_args, signin)
    print(f"Started {run_id}: " + ", ".join(f"{s} {ids[s][:12]}" for s in SIDES), flush=True)

    outcome = wait_all([ids[s] for s in SIDES], WALL_CLOCK_S)
    ended = utc_now()
    redacted = {}
    for side in SIDES:
        logs = subprocess.run(["docker", "logs", ids[side]], capture_output=True, text=True)
        (outs[side] / "container.log").write_text(logs.stdout + logs.stderr)
        subprocess.run(["docker", "rm", ids[side]], capture_output=True)
        redacted[side] = collect_side(outs[side], workspaces[side], run_dir / side, signin[1])

    init = {s: json.loads(p.read_text()) if (p := run_dir / s / "init.json").exists() else {}
            for s in SIDES}
    pair = {
        "run_id": run_id, "kind": "check" if check else "pair",
        "model": MODEL, "effort": EFFORT, "run_args": run_args, "wall_clock_s": WALL_CLOCK_S,
        "started": started, "ended": ended,
        "outcome": {s: outcome[ids[s]] for s in SIDES},
        "image_id": image_id, "chip": platform.machine(),
        "claude_code_version": {s: init[s].get("claude_code_version") for s in SIDES},
        "data": {k: week[k] for k in ("monday", "sunday", "rows", "sha256")},
        "skill_sha256": sha256(SKILL_MD),
        "signin_method": signin[0],
        "redactions": redacted,
    }
    (run_dir / "pair.json").write_text(json.dumps(pair, indent=2) + "\n")
    print(f"Done: {run_dir} " + json.dumps(pair["outcome"]))


if __name__ == "__main__":
    main()
