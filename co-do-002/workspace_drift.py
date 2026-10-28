"""Opt-in Git workspace drift detector for agent resume, without mutating the repo.

Reference implementation for https://github.com/OpenHands/OpenHands/issues/18981
This is deliberately framework-independent and has not been integrated into
OpenHands. Snapshots store hashes and branch/HEAD, not repository file content.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
from typing import TypedDict


class Snapshot(TypedDict):
    branch: str | None
    head: str
    staged_digest: str
    unstaged_digest: str
    untracked_digest: str


def _git(repo: Path, *args: str, timeout: int = 20) -> bytes:
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if p.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {p.stderr.decode('utf-8', 'replace').strip()}")
    return p.stdout


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _untracked_fingerprint(repo: Path) -> bytes:
    # NUL-safe filenames. Do not include ignored files; follow regular Git semantics.
    names = _git(repo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\x00")
    root = Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip())
    h = hashlib.sha256()
    for raw in filter(None, names):
        rel = raw.decode("utf-8", "surrogateescape")
        item = root / rel
        if item.is_symlink():
            data = item.readlink().as_posix().encode("utf-8", "surrogateescape")
        elif item.is_file():
            # Content digests detect modifications to an existing untracked file.
            content_hash = hashlib.sha256()
            with item.open("rb") as fd:
                for block in iter(lambda: fd.read(1024 * 1024), b""):
                    content_hash.update(block)
            data = content_hash.digest()
        else:
            data = b"other"
        h.update(len(raw).to_bytes(8, "big") + raw)
        h.update(len(data).to_bytes(8, "big") + data)
    return h.digest()


def snapshot(repo: str | Path) -> Snapshot:
    """Capture HEAD, branch, and staged/unstaged/untracked content fingerprints.

    Note: like git diff, this does not record changes in ignored files. The
    untracked pass hashes content, so it can be expensive with huge new files.
    """
    path = Path(repo)
    head = _git(path, "rev-parse", "HEAD").decode().strip()
    branch_proc = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "-q", "--short", "HEAD"],
        capture_output=True,
        check=False,
        timeout=20,
    )
    if branch_proc.returncode not in (0, 1):
        raise RuntimeError(branch_proc.stderr.decode("utf-8", "replace").strip())
    branch = branch_proc.stdout.decode().strip() if branch_proc.returncode == 0 else None

    # --no-ext-diff is important: do not execute user-defined external diff commands.
    staged = _git(path, "diff", "--cached", "--no-ext-diff", "--binary", "--full-index")
    unstaged = _git(path, "diff", "--no-ext-diff", "--binary", "--full-index")
    return {
        "branch": branch,
        "head": head,
        "staged_digest": _digest(staged),
        "unstaged_digest": _digest(unstaged),
        "untracked_digest": _digest(_untracked_fingerprint(path)),
    }


def compare(before: Snapshot, after: Snapshot) -> list[str]:
    """Summarize drift categories; does not reset, checkout, modify, or block."""
    labels = {
        "branch": "branch_changed",
        "head": "head_changed",
        "staged_digest": "staged_changes_changed",
        "unstaged_digest": "unstaged_changes_changed",
        "untracked_digest": "untracked_files_changed",
    }
    return [label for key, label in labels.items() if before[key] != after[key]]
