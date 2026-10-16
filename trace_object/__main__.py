"""Run from the repository root with python -m trace_object."""

import argparse
import json
from pathlib import Path
import sys
import uuid

from .core import render, validate


ROOT = Path(__file__).resolve().parent.parent


def load(path):
    # Reject huge files before parsing; never echo file contents on failure.
    path = Path(path)
    if path.stat().st_size > 256_000:
        raise ValueError("record exceeds 256 KB")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Offline object records; human review required")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo")
    for name in ("validate", "report"):
        sub.add_parser(name).add_argument("file")
    args = parser.parse_args()
    try:
        if args.command == "demo":
            for name in ("known-object", "insufficient-data"):
                print(render(load(ROOT / "examples" / (name + ".json"))))
            return 0
        record = load(args.file)
        errors = validate(record)
        if errors:
            print("INVALID: " + "; ".join(errors), file=sys.stderr)
            return 2
        if args.command == "validate":
            print("VALID STRUCTURE; facts, rights and privacy require human review")
        else:
            target = ROOT / ".local" / "reports"
            target.mkdir(parents=True, exist_ok=True)
            output = target / (uuid.uuid4().hex + ".txt")
            with output.open("x", encoding="utf-8") as stream:
                stream.write(render(record))
            print("Local report: " + str(output.relative_to(ROOT)))
        return 0
    except (OSError, ValueError, RecursionError):
        print("ERROR: cannot read or process record; no input contents printed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
