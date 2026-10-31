"""Write the task brief in a clean room.

A fresh container runs Opus with no skill, no web tools and no data: its folder
holds only dataset.md (the portal's public description and columns). The first
draft that passes the acceptance checks is final. A failing draft is kept under
task/rejected/ with its reasons, and the script exits non-zero so it can be run
again from scratch.

    uv run python run_task_writer.py
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from data.dataset_md import fetch_metadata, render
from data.draw_week import WEEK_JSON
from launch.brief_checks import check_brief, check_no_data_access
from launch.collect import collect_side
from launch.docker import finish, start, wait_all
from launch.signin import signin_env
from launch.workspace import SKILL_MD, prepare_workspace
from run_pair import BACKSTOP_S, IMAGE, WALL_CLOCK_S, build_image, utc_now

HERE = Path(__file__).resolve().parent
TASK = HERE / "task"
RUN_ARGS = ["--model", "claude-opus-5-5", "--effort", "high", "--wall-clock-s", str(WALL_CLOCK_S),
            "--max-turns", "200", "--max-budget-usd", "100", "--disallow-web"]


def main() -> None:
    if (TASK / "brief.md").exists():
        raise SystemExit("task/brief.md is already accepted; the first passing draft is final.")
    signin = signin_env(os.environ)
    metadata = fetch_metadata()
    columns = {c["fieldName"] for c in metadata["columns"] if not c["fieldName"].startswith(":")}
    dataset_md = render(metadata, json.loads(WEEK_JSON.read_text()))
    image_id = build_image()

    run_id = utc_now("%Y-%m-%dT%H%MZ")
    environment_md = (HERE / "prompts/environment.md").read_text()
    instructions = (HERE / "prompts/task_writer.md").read_text()
    workspace = prepare_workspace("control", None, SKILL_MD,
                                  files={"dataset.md": dataset_md, "environment.md": environment_md})
    out = Path(tempfile.mkdtemp(prefix="out-"))
    started = utc_now()
    cid = start(IMAGE, workspace, out, instructions, RUN_ARGS, signin)
    print(f"Started task writer {run_id}: {cid[:12]}", flush=True)
    outcome = wait_all([cid], BACKSTOP_S)[cid]
    finish(cid, out)

    dest = TASK / "runs" / run_id
    redacted = collect_side(out, workspace, dest, signin[1])
    brief = dest / "workspace/brief.md"
    reasons = (check_brief(brief.read_text(), columns) if brief.exists()
               else ["brief.md was not written"])
    reasons += check_no_data_access(dest / "messages.jsonl")
    verdict = {"run_id": run_id, "started": started, "ended": utc_now(), "outcome": outcome,
               "image_id": image_id, "run_args": RUN_ARGS, "signin_method": signin[0],
               "redactions": redacted, "passed": not reasons, "reasons": reasons,
               "instructions_sha256": hashlib.sha256(instructions.encode()).hexdigest(),
               "environment_md_sha256": hashlib.sha256(environment_md.encode()).hexdigest()}
    (dest / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")

    if reasons:
        rejected = TASK / "rejected" / run_id
        rejected.mkdir(parents=True)
        if brief.exists():
            shutil.copyfile(brief, rejected / "brief.md")
        (rejected / "reasons.json").write_text(json.dumps(reasons, indent=2) + "\n")
        sys.exit("Rejected: " + "; ".join(reasons))
    shutil.copyfile(brief, TASK / "brief.md")
    shutil.copyfile(dest / "workspace/dataset.md", TASK / "dataset.md")  # the pair gets the same file
    print(f"Accepted: task/brief.md (run record in {dest})")


if __name__ == "__main__":
    main()
