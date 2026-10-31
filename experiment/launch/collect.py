"""Move one side's outputs into runs/, scrubbed of the sign-in value first."""
import hashlib
import shutil
from pathlib import Path

from launch.scrub import scrub_tree

DATA_SUFFIXES = {".csv", ".tsv", ".parquet", ".pkl", ".pickle", ".feather", ".arrow", ".h5", ".hdf5",
                 ".zip", ".gz", ".bz2", ".xz", ".db", ".sqlite", ".npy", ".npz", ".xlsx"}
MAX_BYTES = 25_000_000


def collect_side(out_dir: Path, workspace: Path, dest: Path, secret: str) -> int:
    """Copy /out and the workspace (without trips.csv) to dest; return the redaction count."""
    (workspace / "trips.csv").unlink(missing_ok=True)
    redacted = scrub_tree(out_dir, secret) + scrub_tree(workspace, secret)
    # symlinks stay links: following one could copy a file from outside the run
    shutil.copytree(out_dir, dest, symlinks=True)
    shutil.copytree(workspace, dest / "workspace", symlinks=True)
    return redacted


def hold_back(run_dir: Path, max_bytes: int = MAX_BYTES) -> list[dict]:
    """Keep data files and very large files out of git via a .gitignore in run_dir.

    The taxi data is never committed, and a cleaned copy an agent saved is still the data.
    """
    held = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and not path.is_symlink():
            rel = path.relative_to(run_dir)
            if "private" in rel.parts:
                continue
            size = path.stat().st_size
            if path.suffix.lower() in DATA_SUFFIXES or size > max_bytes:
                held.append({"path": str(rel), "bytes": size,
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    if held:
        (run_dir / ".gitignore").write_text("".join(f"/{h['path']}\n" for h in held))
    return held
