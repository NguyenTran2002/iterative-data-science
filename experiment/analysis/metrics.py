"""Behavior counts for each side of a run, as defined in the design spec (section 7).

    uv run python -m analysis.metrics runs/<run-id> [--no-reexecute]

Writes runs/<run-id>/metrics.json and system_prompts.json, and each side's
system_prompt.txt. The definitions were fixed before any run.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import nbformat

from analysis.system_prompt import extract_system_prompt, first_request_has
from data.fetch_week import CSV

SIDES = ("control", "skill")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
INSTALL = re.compile(r"\b(pip3?|uv pip|uv add|conda|mamba)\s+install\b|\buv add\b")
SKILL_MARKER = "# Iterative Data Science Workflow"


# --- notebook helpers -------------------------------------------------------

def _code_cells(nb) -> dict[str, dict]:
    """Code cells keyed by cell ID, or by position when IDs are missing."""
    return {c.get("id") or f"pos{i}": c for i, c in enumerate(nb.cells) if c.cell_type == "code"}


def _run_state(cell) -> tuple:
    return cell.get("execution_count"), json.dumps(cell.get("outputs", []), sort_keys=True)


def _is_image(output) -> bool:
    return any(k.startswith("image/") for k in output.get("data", {}))


def _is_text(output) -> bool:
    if output.get("output_type") == "stream":
        return True
    return output.get("output_type") in ("execute_result", "display_data") and not _is_image(output)


def _read(path: Path):
    return nbformat.read(path, as_version=4)


def notebook_history(snapshots: list[Path]) -> dict:
    """Executions, batch sizes and rework from the runner's snapshots, in order."""
    executions, batch_sizes, reworked = 0, [], set()
    prev: dict[str, dict] = {}
    at_last_execution: dict[str, str] = {}
    had_outputs: set[str] = set()
    for path in snapshots:
        try:
            cells = _code_cells(_read(path))
        except Exception:  # valid JSON that is not a notebook: nothing to compare
            continue
        changed_run = any(cid not in prev and (c.get("outputs") or c.get("execution_count") is not None)
                          or cid in prev and _run_state(c) != _run_state(prev[cid])
                          for cid, c in cells.items())
        for cid, c in cells.items():
            if cid in had_outputs and cid in prev and c.source != prev[cid].source:
                reworked.add(cid)
        if changed_run:
            executions += 1
            batch_sizes.append(sum(1 for cid, c in cells.items() if at_last_execution.get(cid) != c.source))
            at_last_execution = {cid: c.source for cid, c in cells.items()}
        had_outputs |= {cid for cid, c in cells.items() if c.get("outputs")}
        prev = cells
    return {"executions": executions, "batch_sizes": batch_sizes, "rework_cells": len(reworked)}


def final_notebook(path: Path) -> dict:
    cells = _code_cells(_read(path)).values()
    outputs = [o for c in cells for o in c.get("outputs", [])]
    return {
        "mixed_output_cells": sum(1 for c in cells if any(map(_is_text, c.outputs)) and any(map(_is_image, c.outputs))),
        "inline_images": sum(1 for o in outputs if _is_image(o)),
        "cell_errors": sum(1 for c in cells if any(o.get("output_type") == "error" for o in c.outputs)),
    }


# --- log helpers ------------------------------------------------------------

def _messages(side_dir: Path) -> list[dict]:
    path = side_dir / "messages.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def _blocks(messages: list[dict]):
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            yield from (b for b in content if isinstance(b, dict))


def log_counts(messages: list[dict]) -> dict:
    tool_uses = [b for b in _blocks(messages) if "name" in b and "input" in b]
    tool_results = [b for b in _blocks(messages) if "tool_use_id" in b]
    opened = {b["input"].get("file_path") for b in tool_uses
              if b["name"] == "Read" and Path(str(b["input"].get("file_path", ""))).suffix.lower() in IMAGE_EXTS}
    outside = []
    for b in tool_uses:
        if b["name"] in ("WebSearch", "WebFetch"):
            outside.append({"tool": b["name"], "input": b["input"]})
        elif b["name"] == "Bash" and INSTALL.search(b["input"].get("command", "")):
            outside.append({"tool": "Bash", "input": {"command": b["input"]["command"]}})
    return {
        "tool_errors": sum(1 for b in tool_results if b.get("is_error") is True),
        "figures_opened": len(opened),
        "web_searches": sum(1 for a in outside if a["tool"] == "WebSearch"),
        "web_fetches": sum(1 for a in outside if a["tool"] == "WebFetch"),
        "package_installs": sum(1 for a in outside if a["tool"] == "Bash"),
        "outside_activity": outside,
        "tool_inputs_naming_the_skill": sum(1 for b in tool_uses
                                            if "iterative-data-science" in json.dumps(b["input"]).lower()),
    }


def compute(side_dir: Path) -> dict:
    workspace = side_dir / "workspace"
    notebook = workspace / "analysis.ipynb"
    snapshots = sorted((side_dir / "snapshots").glob("snap-*.ipynb"))
    result = json.loads((side_dir / "result.json").read_text()) if (side_dir / "result.json").exists() else {}
    usage = result.get("usage") or {}
    figures = [p for p in workspace.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS
               and ".claude" not in p.relative_to(workspace).parts] if workspace.exists() else []
    m = {"notebook_present": notebook.exists(), "status": result.get("status")}
    m |= notebook_history(snapshots)
    m |= final_notebook(notebook) if notebook.exists() else {
        "mixed_output_cells": 0, "inline_images": 0, "cell_errors": 0}
    m["figures_created"] = len(figures)
    m |= log_counts(_messages(side_dir))
    m |= {
        "turns": result.get("num_turns"),
        "duration_s": result["duration_ms"] / 1000 if result.get("duration_ms") is not None else None,
        "cost_usd": result.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
    }
    return m


def reexecute(notebook: Path, image: str, csv: Path = CSV) -> bool:
    """Run the final notebook top to bottom in a fresh container, next to the data."""
    with tempfile.TemporaryDirectory(prefix="rerun-") as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(notebook.parent, work)
        shutil.copyfile(csv, work / "trips.csv")
        done = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{work}:/home/analyst/work", "-w", "/home/analyst/work",
             "--entrypoint", "/opt/venv/bin/jupyter", image,
             "nbconvert", "--to", "notebook", "--execute", "--output", "/tmp/rerun.ipynb",
             "--ExecutePreprocessor.timeout=1800", notebook.name],
            capture_output=True, text=True, timeout=4 * 3600)
        return done.returncode == 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("run_dir", type=Path)
    p.add_argument("--no-reexecute", action="store_true")
    p.add_argument("--image", default="ids-experiment")
    a = p.parse_args()

    metrics = {}
    for side in SIDES:
        metrics[side] = compute(a.run_dir / side)
        notebook = a.run_dir / side / "workspace/analysis.ipynb"
        if not a.no_reexecute:
            metrics[side]["fresh_reexecution"] = notebook.exists() and reexecute(notebook, a.image)
    (a.run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

    prompts = {}
    for side in SIDES:
        bodies = a.run_dir / side / "private/bodies"
        text = extract_system_prompt(bodies)
        (a.run_dir / side / "system_prompt.txt").write_text(text)
        prompts[side] = {"sha256": hashlib.sha256(text.encode()).hexdigest(), "chars": len(text),
                         "skill_text_in_first_request": first_request_has(bodies, SKILL_MARKER)}
    prompts["match"] = prompts["control"]["sha256"] == prompts["skill"]["sha256"]
    (a.run_dir / "system_prompts.json").write_text(json.dumps(prompts, indent=2) + "\n")
    print(json.dumps(prompts, indent=2))
    sys.exit(0 if prompts["match"] else 1)


if __name__ == "__main__":
    main()
