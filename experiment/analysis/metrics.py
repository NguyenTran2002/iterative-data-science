"""Behavior counts for each side of a run, as defined in section 7 of the design spec
(docs/design/2026-10-31-experiment-design.md).

    uv run python -m analysis.metrics ../runs/<run-id> [--no-reexecute] [--image NAME]

Writes runs/<run-id>/metrics.json and system_prompts.json, and each side's
system_prompt.txt. The system prompt check reads each side's private/bodies/, which
is not committed, so it needs a run made on this machine. The top-level counts were
fixed before any run; those under "added_after_runs" were not.
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

from analysis.system_prompt import extract_system_prompt, first_request_has, texts
from data.fetch_week import CSV

SIDES = ("control", "skill")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
INSTALL = re.compile(r"\b(pip3?|uv pip|uv add|conda|mamba)\s+install\b|\buv add\b")
SKILL_MARKER = "# Iterative Data Science Workflow"
PINS = Path(__file__).resolve().parents[1] / "requirements/analysis.txt"
NOTEBOOK_INSTALL = re.compile(r"^\s*[%!]\s*(pip3?|uv|conda|mamba)\b.*\binstall\b", re.MULTILINE)
DOWNLOAD = re.compile(r"\b(curl|wget)\b")
OUT_PATH = re.compile(r"(?<![\w.~-])/out(?:/|\b)")


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


# --- measures added after the runs ---------------------------------------------
# These were defined after the runs had been seen. They are kept under
# "added_after_runs" so they are never mistaken for the counts the spec fixed in advance.

def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def pinned_packages(path: Path = PINS) -> dict[str, str]:
    pins = {}
    for line in path.read_text().splitlines():
        if m := re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;]+)", line):
            pins[_norm(m.group(1))] = m.group(2)
    return pins


def batch_sizes_by_source(snapshots: list[Path]) -> list[int]:
    """Batch sizes with cells matched by their code text instead of their ID.

    An agent that regenerates the notebook from a script gives every cell a new ID on
    each pass, so the ID-matched count treats the whole notebook as new each time.
    """
    sizes: list[int] = []
    prev: dict[str, dict] = {}
    at_last_execution: set[str] = set()
    for path in snapshots:
        try:
            cells = list(_code_cells(_load(path)).values())
        except ValueError:
            continue
        if any(_executed(c, prev.get(_source(c))) for c in cells):
            sizes.append(sum(1 for c in cells if _source(c) not in at_last_execution))
            at_last_execution = {_source(c) for c in cells}
        prev = {_source(c): c for c in cells}
    return sizes


def added_after_runs(side_dir: Path, messages: list[dict], snapshots: list[Path],
                     pinned: dict[str, str]) -> dict:
    packages = side_dir / "packages.txt"
    not_in_image = []
    if packages.exists():
        for line in packages.read_text().splitlines():
            if (m := re.match(r"^([A-Za-z0-9_.\-]+)==(\S+)", line)) and pinned.get(_norm(m.group(1))) != m.group(2):
                not_in_image.append(line)

    install_cells = set()
    for path in [*snapshots, side_dir / "workspace/analysis.ipynb"]:
        try:
            cells = _code_cells(_load(path)).values()
        except (OSError, ValueError):
            continue
        install_cells |= {_source(c) for c in cells if NOTEBOOK_INSTALL.search(_source(c))}

    tool_uses = {b["id"]: b for b in _blocks(messages) if "name" in b and "input" in b and "id" in b}
    seen = {}
    skill_text = False
    for result in (b for b in _blocks(messages) if "tool_use_id" in b):
        content = result.get("content")
        items = content if isinstance(content, list) else []
        if any(SKILL_MARKER in t for t in texts(content)):
            skill_text = True
        n_images = sum(1 for i in items if isinstance(i, dict) and i.get("type") == "image")
        if n_images:
            use = tool_uses.get(result["tool_use_id"], {})
            suffix = Path(str(use.get("input", {}).get("file_path", ""))).suffix.lower()
            kind = "notebook" if suffix == ".ipynb" else "image_file" if suffix in IMAGE_EXTS else "other"
            seen[kind] = seen.get(kind, 0) + n_images

    inputs = [json.dumps(b["input"]) for b in tool_uses.values()]
    return {
        "batch_sizes_by_source": batch_sizes_by_source(snapshots),
        "packages_not_in_image": not_in_image,
        "notebook_install_cells": len(install_cells),
        "download_commands": sum(1 for b in tool_uses.values()
                                 if b["name"] == "Bash" and DOWNLOAD.search(b["input"].get("command", ""))),
        "images_seen_by_source": dict(sorted(seen.items())),
        "tool_calls_touching_out": sum(1 for i in inputs if OUT_PATH.search(i)),
        "skill_text_in_tool_results": skill_text,
    }


def compute(side_dir: Path, pinned: dict[str, str] | None = None) -> dict:
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
    messages = _messages(side_dir)
    m |= log_counts(messages)
    m |= {
        "turns": result.get("num_turns"),
        "duration_s": result["duration_ms"] / 1000 if result.get("duration_ms") is not None else None,
        "cost_usd": result.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
    }
    m["added_after_runs"] = added_after_runs(side_dir, messages, snapshots,
                                             pinned if pinned is not None else pinned_packages())
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
