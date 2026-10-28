"""Run real Git operations on isolated temporary repositories; no network."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from workspace_drift import snapshot, compare


class GitDriftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        (self.root / "tracked.txt").write_text("first\n")
        self.git("add", "tracked.txt")
        self.git("commit", "-qm", "init")
        self.base = snapshot(self.root)

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def diff(self):
        return compare(self.base, snapshot(self.root))

    def test_unchanged(self):
        self.assertEqual(self.diff(), [])

    def test_new_commit_same_branch(self):
        (self.root / "tracked.txt").write_text("second\n")
        self.git("add", "tracked.txt")
        self.git("commit", "-qm", "change")
        self.assertEqual(self.diff(), ["head_changed"])

    def test_switch_branch(self):
        self.git("switch", "-qc", "alternate")
        self.assertIn("branch_changed", self.diff())

    def test_detached_head(self):
        self.git("switch", "-q", "--detach", "HEAD")
        self.assertIn("branch_changed", self.diff())

    def test_staged_change(self):
        (self.root / "tracked.txt").write_text("staged\n")
        self.git("add", "tracked.txt")
        self.assertEqual(self.diff(), ["staged_changes_changed"])

    def test_unstaged_change(self):
        (self.root / "tracked.txt").write_text("unstaged\n")
        self.assertEqual(self.diff(), ["unstaged_changes_changed"])

    def test_untracked_added(self):
        (self.root / "new.txt").write_text("new")
        self.assertEqual(self.diff(), ["untracked_files_changed"])

    def test_untracked_edited_without_filename_change(self):
        p = self.root / "new.txt"
        p.write_text("one")
        later = snapshot(self.root)
        p.write_text("two")
        self.assertEqual(compare(later, snapshot(self.root)), ["untracked_files_changed"])

    def test_untracked_deleted(self):
        p = self.root / "new.txt"
        p.write_text("new")
        old = snapshot(self.root)
        p.unlink()
        self.assertEqual(compare(old, snapshot(self.root)), ["untracked_files_changed"])

    def test_dirty_tracked_file_modified_again(self):
        p = self.root / "tracked.txt"
        p.write_text("alpha")
        prev = snapshot(self.root)
        p.write_text("beta")
        self.assertEqual(compare(prev, snapshot(self.root)), ["unstaged_changes_changed"])

    def test_dirty_staged_file_modified_again(self):
        p = self.root / "tracked.txt"
        p.write_text("alpha")
        self.git("add", "tracked.txt")
        prev = snapshot(self.root)
        p.write_text("beta")
        self.git("add", "tracked.txt")
        self.assertEqual(compare(prev, snapshot(self.root)), ["staged_changes_changed"])

    def test_linked_worktree_changes_do_not_change_main_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            linked = Path(temp) / "linked"
            self.git("worktree", "add", "-b", "linked", str(linked))
            linked_before = snapshot(linked)
            (linked / "tracked.txt").write_text("linked edit")
            self.assertEqual(compare(self.base, snapshot(self.root)), [])
            self.assertEqual(compare(linked_before, snapshot(linked)),
                             ["unstaged_changes_changed"])

    def test_unborn_repository_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(["git", "init", "-q", temp], check=True)
            with self.assertRaises(RuntimeError):
                snapshot(temp)

    def test_ignored_files_not_reported(self):
        (self.root / ".gitignore").write_text("secret.tmp\n")
        self.git("add", ".gitignore")
        self.git("commit", "-qm", "ignore")
        baseline = snapshot(self.root)
        (self.root / "secret.tmp").write_text("ignored")
        self.assertEqual(compare(baseline, snapshot(self.root)), [])

    def test_non_git_directory_rejected(self):
        other = self.root / "other"
        other.mkdir()
        # A subdirectory remains in the same repo; truly outside is another temp dir.
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):
                snapshot(temp)

    def test_read_only_snapshot(self):
        a = snapshot(self.root)
        b = snapshot(self.root)
        self.assertEqual(a, b)
        self.assertEqual(self.git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
