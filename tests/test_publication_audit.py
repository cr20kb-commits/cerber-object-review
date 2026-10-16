"""Independent integration checks of the publication gate in disposable repositories."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parent.parent / "tools" / "audit_publication.py"


class PublicationAudit(unittest.TestCase):
    def setUp(self):
        base = SOURCE.parent.parent / ".local" / "test-tmp"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temp.name)
        if not self.root.resolve().is_relative_to(base.resolve()):
            raise RuntimeError("Temporary repository must remain under the test directory")
        self.addCleanup(self.temp.cleanup)
        (self.root / "tools").mkdir()
        shutil.copyfile(SOURCE, self.root / "tools" / SOURCE.name)
        self.git("init", "-b", "main")
        (self.root / "README.md").write_text("Synthetic fixture only.\n", encoding="utf-8")
        self.git("add", "--", "README.md", "tools/audit_publication.py")

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test" + chr(64) + "users.noreply.github.com", "-c", "commit.gpgsign=false", *args], cwd=self.root, check=True, capture_output=True)

    def audit(self):
        return subprocess.run([sys.executable, "tools/audit_publication.py"], cwd=self.root, capture_output=True)

    def test_clean_new_repository_passes(self):
        self.assertEqual(self.audit().returncode, 0)
        self.git("commit", "-m", "Synthetic initial fixture")
        self.assertEqual(self.audit().returncode, 0)

    def test_unstaged_change_and_forced_report_fail(self):
        (self.root / "README.md").write_text("Unreviewed change", encoding="utf-8")
        self.assertNotEqual(self.audit().returncode, 0)
        self.git("add", "--", "README.md")
        (self.root / "reports").mkdir()
        (self.root / "reports" / "case.txt").write_text("Synthetic only", encoding="utf-8")
        self.git("add", "-f", "--", "reports/case.txt")
        self.assertNotEqual(self.audit().returncode, 0)

    def test_removed_historical_secret_still_fails_without_echo(self):
        synthetic = "gh" + "p_" + "A" * 30
        (self.root / "README.md").write_text(synthetic, encoding="utf-8")
        self.git("add", "--", "README.md")
        self.git("commit", "-m", "Synthetic secret fixture")
        (self.root / "README.md").write_text("Removed synthetic value", encoding="utf-8")
        self.git("add", "--", "README.md")
        self.git("commit", "-m", "Remove fixture")
        result = self.audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"history", result.stdout)
        self.assertNotIn(synthetic.encode(), result.stdout + result.stderr)

    def test_commit_metadata_is_checked(self):
        synthetic = "gh" + "p_" + "B" * 30
        self.git("commit", "-m", synthetic)
        result = self.audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"metadata", result.stdout)
        self.assertNotIn(synthetic.encode(), result.stdout + result.stderr)
