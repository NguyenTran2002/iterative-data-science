"""Move one side's outputs into runs/, scrubbed of the sign-in value first."""
import shutil
from pathlib import Path

from launch.scrub import scrub_tree


def collect_side(out_dir: Path, workspace: Path, dest: Path, secret: str) -> int:
    """Copy /out and the workspace (without trips.csv) to dest; return the redaction count."""
    (workspace / "trips.csv").unlink(missing_ok=True)
    redacted = scrub_tree(out_dir, secret) + scrub_tree(workspace, secret)
    shutil.copytree(out_dir, dest)
    shutil.copytree(workspace, dest / "workspace")
    return redacted
