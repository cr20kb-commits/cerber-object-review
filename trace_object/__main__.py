"""Run from the repository root with python -m trace_object."""

import argparse
import json
from pathlib import Path
import sys
import uuid

from .core import render, validate
from .pilot import fingerprint, render_pilot, validate_pilot


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
    sub.add_parser("fingerprint").add_argument("image")
    for name in ("pilot-check", "pilot-report"):
        command = sub.add_parser(name)
        command.add_argument("file")
        command.add_argument("image")
    args = parser.parse_args()
    try:
        if args.command == "fingerprint":
            print(json.dumps(fingerprint(args.image), indent=2))
            return 0
        if args.command == "demo":
            for name in ("known-object", "insufficient-data"):
                print(render(load(ROOT / "examples" / (name + ".json"))))
            return 0
        record = load(args.file)
        is_pilot = args.command in ("pilot-check", "pilot-report")
        errors = validate_pilot(record, args.image) if is_pilot else validate(record)
        if errors:
            print("INVALID: " + "; ".join(errors), file=sys.stderr)
            return 2
        if args.command in ("validate", "pilot-check"):
            print("VALID STRUCTURE; facts, rights and privacy require human review")
            if is_pilot:
                print("LOCAL IMAGE HASH AND SIZE MATCH; this does not authenticate the source or conclusions")
        else:
            target = ROOT / ".local" / "reports"
            target.mkdir(parents=True, exist_ok=True)
            output = target / (uuid.uuid4().hex + ".txt")
            with output.open("x", encoding="utf-8") as stream:
                stream.write(render_pilot(record, args.image) if is_pilot else render(record))
            print("Local report: " + str(output.relative_to(ROOT)))
        return 0
    except (OSError, ValueError, RecursionError):
        print("ERROR: cannot read or process record; no input contents printed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
