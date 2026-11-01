"""Acceptance checks for the clean-room brief (section 5 of the design spec,
docs/design/2026-10-31-experiment-design.md).

They check form only. Nobody judges whether a passing brief is good.
"""
import json
import re
from pathlib import Path

MAX_WORDS = 500
NUMBERED = re.compile(r"^\d+\.\s")
TOP_LEVEL_ITEM = re.compile(r"^(?:[-*]\s|\*\*)")
BACKTICKED = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
SNAKE_CASE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
# The writer may only read dataset.md, so any mention of the portal or the dataset ID in
# a tool call is flagged: a false alarm costs a rerun of the writer, a miss breaks the clean room.
DATA_MARKERS = ("cityofchicago.org", "wrvz-psew")


def count_questions(text: str) -> int:
    """Numbered items or headings that ask something; a numbered deliverable is not a question.

    A brief with none of those may write its questions as top-level bullets or bold lines.
    """
    lines = text.splitlines()
    n = sum(1 for line in lines if (NUMBERED.match(line) or line.startswith("#")) and "?" in line)
    return n or sum(1 for line in lines if TOP_LEVEL_ITEM.match(line) and "?" in line)


def check_brief(text: str, columns: set[str]) -> list[str]:
    reasons = []
    if (n := count_questions(text)) not in (3, 4):
        reasons.append(f"has {n} questions, not three or four")
    if (words := len(text.split())) >= MAX_WORDS:
        reasons.append(f"has {words} words, not under {MAX_WORDS}")
    named = set(BACKTICKED.findall(text)) | set(SNAKE_CASE.findall(text))
    if unknown := sorted(named - columns):
        reasons.append(f"names columns not in dataset.md: {', '.join(unknown)}")
    return reasons


def check_no_data_access(messages_jsonl: Path) -> list[str]:
    reasons = []
    for line in messages_jsonl.read_text().splitlines():
        message = json.loads(line)
        for block in message.get("content") or []:
            if isinstance(block, dict) and "input" in block:
                call = json.dumps(block["input"])
                for marker in DATA_MARKERS:
                    if marker in call.lower():
                        reasons.append(f"{block.get('name')} call mentions {marker}")
    return reasons
