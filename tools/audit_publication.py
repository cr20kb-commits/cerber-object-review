"""Fail on unexpected indexed/history paths or common secrets. Not a PII guarantee."""

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
ROOT_FILES = {".gitignore", ".gitattributes", "LICENSE", "README.md", "README.en.md", "CONTRIBUTING.md", "SECURITY.md", "VOLUNTEER_TASKS.md"}
DIRS = {".github", "docs", "examples", "trace_object", "tests", "tools"}
SUFFIXES = {".md", ".py", ".json", ".yml"}
DENIED_PARTS = {".local", "reports", "cases", "private", "uploads", "downloads", "__pycache__"}
PATTERNS = [
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})",
    rb"(?:AKIA|ASIA)[A-Z0-9]{16}",
    rb"sk-(?:proj-)?[A-Za-z0-9_-]{20,}",
    rb"(?i)(?:password|passwd|api_key|api-key|access_token|oauth_token)\s*[=:]\s*[\"']?[^\s\"']{8,}",
    rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    rb"[A-Za-z]:[\\/]Users[\\/][^\s]+",
]


def allowed(path):
    p = Path(path)
    return (path in ROOT_FILES or (len(p.parts) > 1 and p.parts[0] in DIRS and p.suffix in SUFFIXES)) and not any(x in DENIED_PARTS for x in p.parts)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def inspect_blob(path, data, where):
    errors = []
    if not allowed(path):
        errors.append(where + ": disallowed path " + path)
    if len(data) > 256_000 or b"\0" in data:
        errors.append(where + ": oversized/binary file " + path)
    try:
        data.decode("utf-8")
    except UnicodeError:
        errors.append(where + ": not UTF-8 " + path)
    # Print only path and rule number, never a matching secret or personal value.
    for n, pattern in enumerate(PATTERNS, 1):
        if re.search(pattern, data):
            errors.append(where + ": sensitive-content rule " + str(n) + " in " + path)
    return errors


def main():
    errors = []
    indexed = git("ls-files", "--stage", "-z").split(b"\0")
    count = 0
    for entry in filter(None, indexed):
        metadata, raw_path = entry.split(b"\t", 1)
        mode, oid, stage = metadata.decode().split()
        path = raw_path.decode("utf-8")
        count += 1
        if mode != "100644" or stage != "0":
            errors.append("index: unsupported file mode or conflict: " + path)
        data = git("cat-file", "blob", oid)
        errors += inspect_blob(path, data, "index")
        local = ROOT / path
        if not local.is_file() or local.read_bytes().replace(b"\r\n", b"\n") != data.replace(b"\r\n", b"\n"):
            errors.append("index differs from worktree: " + path)
    if not count:
        errors.append("index: empty; stage exact reviewed paths first")
    # Include all refs and reflogs, including deleted or superseded commits.
    history = git("rev-list", "--all", "--reflog").decode().splitlines()
    seen = set()
    for commit in history:
        for entry in filter(None, git("ls-tree", "-r", "-z", commit).split(b"\0")):
            metadata, raw_path = entry.split(b"\t", 1)
            mode, kind, oid = metadata.decode().split()
            path = raw_path.decode("utf-8")
            if kind != "blob" or mode != "100644":
                errors.append("history: unsupported mode: " + path)
                continue
            if (path, oid) not in seen:
                errors += inspect_blob(path, git("cat-file", "blob", oid), "history")
                seen.add((path, oid))
        # Scan authors and commit messages too; no personal email is required to contribute.
        meta = git("show", "-s", "--format=%an%n%ae%n%cn%n%ce%n%B", commit)
        meta = re.sub(rb"[A-Za-z0-9+_.-]+@users\.noreply\.github\.com", b"NOREPLY", meta)
        for n, pattern in enumerate(PATTERNS, 1):
            if re.search(pattern, meta):
                errors.append("history: commit metadata sensitive-content rule " + str(n))
    if errors:
        print("FAIL\n" + "\n".join(errors))
        return 1
    print("PASS: " + str(count) + " indexed files; " + str(len(history)) + " commits; common-secret/path checks only. Human content review required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
