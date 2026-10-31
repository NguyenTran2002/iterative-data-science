"""Start runner containers and wait for them with a wall-clock limit."""
import os
import subprocess
import time
from pathlib import Path


def docker_run_args(image: str, workspace: Path, out_dir: Path, run_args: list[str],
                    signin: tuple[str, str]) -> list[str]:
    # `-e NAME` without a value: docker reads it from the launcher's environment,
    # so the secret never appears on a command line
    # --init: a real PID 1 forwards `docker stop`'s SIGTERM to the runner, which records it
    return ["docker", "run", "-d", "--init",
            "-v", f"{workspace}:/home/analyst/work",
            "-v", f"{out_dir}:/out",
            "-e", signin[0],
            image, "--prompt-file", "/out/prompt.md", *run_args]


def start(image: str, workspace: Path, out_dir: Path, prompt: str, run_args: list[str],
          signin: tuple[str, str]) -> str:
    (out_dir / "prompt.md").write_text(prompt)
    env = {**os.environ, signin[0]: signin[1]}
    done = subprocess.run(docker_run_args(image, workspace, out_dir, run_args, signin),
                          env=env, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _state(cid: str) -> tuple[bool, int]:
    out = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}} {{.State.ExitCode}}", cid],
                         capture_output=True, text=True, check=True).stdout.split()
    return out[0] == "true", int(out[1])


def wait_all(ids: list[str], timeout_s: int, poll_s: float = 1.0,
             stop_grace_s: int = 120) -> dict[str, str]:
    deadline = time.monotonic() + timeout_s
    outcome: dict[str, str] = {}
    while len(outcome) < len(ids):
        for cid in ids:
            if cid not in outcome:
                running, code = _state(cid)
                if not running:
                    outcome[cid] = f"exit:{code}"
        if len(outcome) < len(ids) and time.monotonic() >= deadline:
            for cid in ids:
                if cid not in outcome:
                    subprocess.run(["docker", "stop", "-t", str(stop_grace_s), cid], capture_output=True)
                    outcome[cid] = "timeout"
        elif len(outcome) < len(ids):
            time.sleep(poll_s)
    return {cid: outcome[cid] for cid in ids}
