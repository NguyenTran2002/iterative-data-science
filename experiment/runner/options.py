"""Agent SDK options for one run, as fixed by the design spec (section 4)."""
import os
from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions

SIGNIN_VARS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")


@dataclass
class RunConfig:
    model: str
    effort: str
    prompt: str
    max_turns: int
    max_budget_usd: float
    disallow_web: bool
    workspace: Path = Path("/home/analyst/work")
    out_dir: Path = Path("/out")
    wall_clock_s: int = 14400


def signin_method() -> str | None:
    """The name of the sign-in variable this run uses, never its value."""
    return next((name for name in SIGNIN_VARS if os.environ.get(name)), None)


def build_options(cfg: RunConfig) -> ClaudeAgentOptions:
    env = {
        "CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT": "1",
        "DISABLE_AUTOUPDATER": "1",
        "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
        "OTEL_LOGS_EXPORTER": "none",
        "OTEL_METRICS_EXPORTER": "none",
        "OTEL_LOG_RAW_API_BODIES": f"file:{cfg.out_dir}/private/bodies",
        "PATH": "/opt/venv/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": "/home/analyst",
    }
    if name := signin_method():
        env[name] = os.environ[name]
    return ClaudeAgentOptions(
        model=cfg.model,
        effort=cfg.effort,
        system_prompt={"type": "preset", "preset": "claude_code"},
        setting_sources=["project"],
        permission_mode="bypassPermissions",  # the container is the confinement
        cwd=cfg.workspace,
        max_turns=cfg.max_turns,
        max_budget_usd=cfg.max_budget_usd,
        disallowed_tools=["WebSearch", "WebFetch"] if cfg.disallow_web else [],
        env=env,
        stderr=lambda line: _append(cfg.out_dir / "stderr.txt", line),
    )


def _append(path: Path, line: str) -> None:
    with path.open("a") as f:
        f.write(line + "\n")
