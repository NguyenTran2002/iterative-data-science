"""Read the system prompt and first user turn from the raw API request bodies.

Claude Code logs each request under private/bodies/ with an index.jsonl. The main
thread's requests have query_source "sdk"; title generation and subagents do not.
"""
import json
from pathlib import Path

BILLING_PREFIX = "x-anthropic-billing-header"


def _first_main_request(bodies: Path) -> dict:
    for line in (bodies / "index.jsonl").read_text().splitlines():
        entry = json.loads(line)
        if entry["query_source"] == "sdk":
            return json.loads((bodies / entry["request_file"]).read_text())
    raise ValueError(f"no main-thread request in {bodies}")


def extract_system_prompt(bodies: Path) -> str:
    """The main thread's system prompt, minus the per-request billing line."""
    system = _first_main_request(bodies)["system"]
    blocks = [system] if isinstance(system, str) else [b["text"] for b in system]
    return "\n\n".join(b for b in blocks if not b.startswith(BILLING_PREFIX))


def _texts(content) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [t for item in content for t in _texts(item)]
    if isinstance(content, dict):
        return [t for key in ("text", "content") if key in content for t in _texts(content[key])]
    return []


def first_request_has(bodies: Path, marker: str) -> bool:
    """Whether the first main-thread request's messages contain `marker`."""
    return any(marker in t for t in _texts(_first_main_request(bodies)["messages"]))
