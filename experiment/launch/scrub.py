"""Redact the sign-in value from every file before anything is written into runs/.

Catches the whole value, any 16-character piece of it (a truncated print), and
anything shaped like an Anthropic key or token.
"""
import re
from pathlib import Path

REDACTED = b"[REDACTED]"
PIECE = 16
TOKEN_SHAPED = re.compile(rb"sk-ant-[A-Za-z0-9_\-]{8,}")


def scrub_bytes(data: bytes, secret: bytes) -> tuple[bytes, int]:
    count = data.count(secret)
    data = data.replace(secret, REDACTED)
    data, n = TOKEN_SHAPED.subn(REDACTED, data)
    count += n
    pieces = {secret[i:i + PIECE] for i in range(len(secret) - PIECE + 1)}
    while True:  # each pass shortens what is left of a partial copy
        found = [p for p in pieces if p in data]
        if not found:
            return data, count
        for p in found:
            count += data.count(p)
            data = data.replace(p, REDACTED)


def scrub_tree(root: Path, secret: str) -> int:
    if not secret:
        raise ValueError("refusing to scrub with an empty secret")
    needle, count = secret.encode(), 0
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            scrubbed, n = scrub_bytes(data, needle)
            if n:
                path.write_bytes(scrubbed)
                count += n
    return count
