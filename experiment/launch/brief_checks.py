"""Acceptance checks for the clean-room brief (design spec, section 5).

They check form only. Nobody judges whether a passing brief is good.
"""
import json
import re
from pathlib import Path

MAX_WORDS = 400
NUMBERED = re.compile(r"^\d+\.\s")
HEADED_QUESTION = re.compile(r"^#+ .*\?\s*$")
BACKTICKED = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
SNAKE_CASE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
DATA_ENDPOINTS = ("data.cityofchicago.org/resource/", "/api/views/wrvz-psew/rows")


def count_questions(text: str) -> int:
    return sum(1 for line in text.splitlines()
               if NUMBERED.match(line) or HEADED_QUESTION.match(line))


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
                for endpoint in DATA_ENDPOINTS:
                    if endpoint in call:
                        reasons.append(f"{block.get('name')} call reached {endpoint}")
    return reasons
