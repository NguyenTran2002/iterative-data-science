"""Redact the sign-in value from every file before anything is written into runs/."""
from pathlib import Path

REDACTED = b"[REDACTED]"


def scrub_tree(root: Path, secret: str) -> int:
    if not secret:
        raise ValueError("refusing to scrub with an empty secret")
    needle, count = secret.encode(), 0
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            if (n := data.count(needle)):
                path.write_bytes(data.replace(needle, REDACTED))
                count += n
    return count
