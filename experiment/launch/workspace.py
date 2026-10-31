"""Build each side's workspace and prompt. The two sides differ only by the skill."""
import shutil
import tempfile
from pathlib import Path
from typing import Literal

REPO = Path(__file__).resolve().parents[2]
SKILL_MD = REPO / "plugins/iterative-data-science/skills/iterative-data-science/SKILL.md"
SKILL_COMMAND = "/iterative-data-science"

Side = Literal["control", "skill"]


def prepare_workspace(side: Side, csv: Path | None, skill_md: Path,
                      files: dict[str, str] | None = None) -> Path:
    """A fresh folder with a neutral name, outside the repository."""
    ws = Path(tempfile.mkdtemp(prefix="run-"))
    if csv is not None:
        shutil.copyfile(csv, ws / "trips.csv")
    if side == "skill":
        dest = ws / ".claude/skills/iterative-data-science/SKILL.md"
        dest.parent.mkdir(parents=True)
        shutil.copyfile(skill_md, dest)
    for name, text in (files or {}).items():
        (ws / name).write_text(text)
    return ws


def build_prompt(side: Side, wrapper: str, brief: str) -> str:
    prompt = f"{wrapper}\n\n{brief}"
    return f"{SKILL_COMMAND} {prompt}" if side == "skill" else prompt
