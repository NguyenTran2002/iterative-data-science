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

from analysis.system_prompt import extract_system_prompt, first_request_has
from data.fetch_week import CSV

SIDES = ("control", "skill")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
INSTALL = re.compile(r"\b(pip3?|uv pip|uv add|conda|mamba)\s+install\b|\buv add\b")
SKILL_MARKER = "# Iterative Data Science Workflow"


# --- notebook helpers -------------------------------------------------------
# Notebooks are read as raw JSON, not through nbformat: nbformat invents a fresh
# random ID for every cell that lacks one, which would make each snapshot look new.

def _load(path: Path) -> dict:
    nb = json.loads(path.read_text())
    if not isinstance(nb, dict) or not isinstance(nb.get("cells"), list):
        raise ValueError(f"{path} is not a notebook")
    return nb


def _source(cell: dict) -> str:
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else str(src)


def _outputs(cell: dict) -> list:
    outputs = cell.get("outputs")
    return outputs if isinstance(outputs, list) else []


def _code_cells(nb: dict) -> dict[str, dict]:
    """Code cells keyed by the file's own cell ID, or by position when it has none."""
    return {c.get("id") or f"pos{i}": c for i, c in enumerate(nb["cells"])
            if isinstance(c, dict) and c.get("cell_type") == "code"}


def _executed(cell: dict, before: dict | None) -> bool:
    """New outputs or a new execution count. Clearing them (as NotebookEdit does) is not running."""
    outputs, count = _outputs(cell), cell.get("execution_count")
    old_outputs = _outputs(before) if before else []
    old_count = before.get("execution_count") if before else None
    return bool(outputs) and outputs != old_outputs or count is not None and count != old_count


def _is_image(output) -> bool:
    data = output.get("data") if isinstance(output, dict) else None
    return isinstance(data, dict) and any(k.startswith("image/") for k in data)


def _is_text(output) -> bool:
    kind = output.get("output_type") if isinstance(output, dict) else None
    return kind == "stream" or kind in ("execute_result", "display_data") and not _is_image(output)


def notebook_history(snapshots: list[Path]) -> dict:
    """Executions, batch sizes and rework from the runner's snapshots, in order."""
    executions, batch_sizes, reworked = 0, [], set()
    prev: dict[str, dict] = {}
    at_last_execution: dict[str, str] = {}
    had_outputs: set[str] = set()
    for path in snapshots:
        try:
            cells = _code_cells(_load(path))
        except ValueError:  # JSON that is not a notebook: nothing to compare
            continue
        for cid, c in cells.items():
            if cid in had_outputs and cid in prev and _source(c) != _source(prev[cid]):
                reworked.add(cid)
        if any(_executed(c, prev.get(cid)) for cid, c in cells.items()):
            executions += 1
            batch_sizes.append(sum(1 for cid, c in cells.items() if at_last_execution.get(cid) != _source(c)))
            at_last_execution = {cid: _source(c) for cid, c in cells.items()}
        had_outputs |= {cid for cid, c in cells.items() if _outputs(c)}
        prev = cells
    return {"executions": executions, "batch_sizes": batch_sizes, "rework_cells": len(reworked)}


EMPTY_FINAL = {"mixed_output_cells": 0, "inline_images": 0, "cell_errors": 0}


def final_notebook(path: Path) -> dict:
    try:
        cells = list(_code_cells(_load(path)).values())
    except ValueError:
        return {"notebook_valid": False, **EMPTY_FINAL}
    outputs = [o for c in cells for o in _outputs(c)]
    return {
        "notebook_valid": True,
        "mixed_output_cells": sum(1 for c in cells if any(map(_is_text, _outputs(c)))
                                  and any(map(_is_image, _outputs(c)))),
        "inline_images": sum(1 for o in outputs if _is_image(o)),
        "cell_errors": sum(1 for c in cells
                           if any(isinstance(o, dict) and o.get("output_type") == "error" for o in _outputs(c))),
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


def other_notebooks(side_dir: Path) -> list[str]:
    """Notebooks besides analysis.ipynb: snapshotted during the run or left in the workspace."""
    other = side_dir / "snapshots/other"
    seen = {str(p.parent.relative_to(other)) for p in other.rglob("snap-*.ipynb")} if other.exists() else set()
    workspace = side_dir / "workspace"
    if workspace.exists():
        seen |= {str(p.relative_to(workspace)) for p in workspace.rglob("*.ipynb")
                 if not any(part.startswith(".") for part in p.relative_to(workspace).parts)}
    return sorted(seen - {"analysis.ipynb"})


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
    m |= final_notebook(notebook) if notebook.exists() else {"notebook_valid": False, **EMPTY_FINAL}
    m["figures_created"] = len(figures)
    m["other_notebooks"] = other_notebooks(side_dir)
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
