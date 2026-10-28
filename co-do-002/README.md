# 共做 #002 — Git workspace drift detection on agent resume

External problem: [OpenHands issue #18981](https://github.com/OpenHands/OpenHands/issues/18981).

An agent resuming an old conversation may mistakenly assume the repository is unchanged. This standalone reference implementation captures a lightweight, **read-only** Git snapshot at turn completion and compares it before another turn begins. It does not reset the workspace, block execution, or touch user files.

## What is implemented

- Current branch (including detached HEAD) and HEAD commit ID.
- SHA-256 digests of staged and unstaged Git diffs (no file content stored in the snapshot).
- SHA-256 fingerprint of paths and contents of non-ignored untracked files.
- Human-readable drift categories: branch, HEAD, staged, unstaged, untracked.
- 13 real-Git tests in temporary repositories, covering no change, new commits, branch switching, detached head, staged/unstaged edits, untracked additions/removal/content changes and ignored files.

## Run locally

```bash
python -m unittest -v test_workspace_drift.py
```

## Usage sketch (not an OpenHands integration)

```python
from workspace_drift import snapshot, compare

saved = snapshot('/workspace')  # store after a completed agent turn
# On resume:
changes = compare(saved, snapshot('/workspace'))
if changes:
    print('Workspace changed since the last turn:', changes)
```

## Scope and limitations

This is a **tested independent component**, not an OpenHands fix or upstream PR. There are no OpenHands integration tests or maintainer acceptance claims. Users or maintainers need to decide where to persist the snapshot and where to display a non-blocking notice and inject context safely. It intentionally ignores files excluded by `.gitignore`. The untracked-file pass hashes complete file contents, so it may require limits or caching in very large working trees. Git's configured diff mechanisms and symlinks need review for hostile untrusted repositories before production deployment. It does not preserve or publish the contents of project files.

No new license grant or endorsement of the upstream project is asserted by this experiment.