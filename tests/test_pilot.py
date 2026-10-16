import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from trace_object.pilot import fingerprint, render_pilot, validate_pilot


ROOT = Path(__file__).resolve().parent.parent
SAMPLE = b"Synthetic fixture only. Not a case image.\n"


def fixture():
    return {
        "format_version": 1,
        "record": json.loads((ROOT / "examples" / "insufficient-data.json").read_text(encoding="utf-8")),
        "provenance": {
            "image_url": "https://example.invalid/synthetic-fixture",
            "retrieved_at": "2026-10-16T00:00:00Z",
            "sha256": hashlib.sha256(SAMPLE).hexdigest(), "byte_length": len(SAMPLE),
            "rights_note": "DEMO: original synthetic bytes, no third-party or case material.",
            "processing": ["DEMO: no image processing; not an image recognition test."]
        },
        "searches": [{"query": "DEMO invented query, not executed on the internet", "kind": "web_search", "executed_on": "2026-10-16", "result_note": "DEMO mock log for structural testing only.", "sources": []}],
        "comparisons": [{"name": "DEMO fictional candidate", "sources": ["https://example.invalid/catalog/mock"], "matches": ["DEMO shared colour"], "contradictions": ["DEMO different pattern"], "decision": "rejected", "reason": "DEMO pattern does not match", "next_checks": ["DEMO none; no actual lead"]}],
        "conclusion": "DEMO: insufficient data; this is a synthetic contract example."
    }


class Pilot(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".local" / "test-tmp"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temp.name)
        if not self.root.resolve().is_relative_to(base.resolve()):
            raise RuntimeError("Test output outside intended root")
        self.addCleanup(self.temp.cleanup)
        self.image = self.root / "synthetic.bin"
        self.image.write_bytes(SAMPLE)

    def test_hash_matches_independent_known_digest(self):
        actual = fingerprint(self.image)
        self.assertEqual(actual["byte_length"], len(SAMPLE))
        self.assertEqual(actual["sha256"], hashlib.sha256(self.image.read_bytes()).hexdigest())
        self.assertEqual(validate_pilot(fixture(), self.image), [])

    def test_changed_bytes_and_length_are_rejected(self):
        self.image.write_bytes(SAMPLE + b"changed")
        self.assertIn("provenance: supplied image bytes do not match recorded evidence", validate_pilot(fixture(), self.image))
        with self.assertRaises(ValueError):
            render_pilot(fixture(), self.image)

    def test_rejected_candidates_remain_in_insufficient_report(self):
        report = render_pilot(fixture(), self.image)
        self.assertIn("DEMO fictional candidate", report)
        self.assertIn("rejected", report)
        self.assertIn("DEMO invented query", report)
        self.assertIn("недостаточно данных", report)

    def test_invalid_provenance_and_log(self):
        for field, value in (("sha256", "0"), ("byte_length", True), ("retrieved_at", "2026-10-16"), ("retrieved_at", "2026-10-16T03:00:00+03:00"), ("rights_note", ""), ("processing", [])):
            data = fixture()
            data["provenance"][field] = value
            self.assertTrue(validate_pilot(data))
        for field in ("provenance", "searches", "comparisons", "record", "conclusion"):
            data = fixture()
            data[field] = None
            self.assertTrue(validate_pilot(data))
        for field in ("query", "kind", "executed_on", "result_note", "sources"):
            data = fixture()
            data["searches"][0][field] = None
            self.assertTrue(validate_pilot(data))

    def test_retained_candidate_cannot_hide_under_insufficient_data(self):
        data = fixture()
        data["comparisons"][0]["decision"] = "retained"
        self.assertTrue(validate_pilot(data))

    def test_official_image_source_cannot_spoof_host(self):
        data = fixture()
        data["record"].update(demo=False, object_id="C34012025", official_url="https://www.europol.europa.eu/stopchildabuse/6309")
        data["provenance"]["image_url"] = "https://www.europol.europa.eu.evil.test/cms/sites/default/files/demo.webp"
        data["comparisons"][0]["sources"] = ["https://catalog.example.org/item"]
        self.assertTrue(validate_pilot(data))
        data["provenance"]["image_url"] = "https://www.europol.europa.eu/cms/sites/default/files/demo.webp?itok=public-demo"
        self.assertEqual(validate_pilot(data), [])

    def test_cli_and_public_synthetic_example(self):
        data = json.loads((ROOT / "examples" / "pilot-insufficient.json").read_text(encoding="utf-8"))
        self.assertEqual(data, fixture())
        record = self.root / "pilot.json"
        record.write_text(json.dumps(data), encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "trace_object", "pilot-check", str(record), str(self.image)], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.image.write_bytes(b"altered")
        result = subprocess.run([sys.executable, "-m", "trace_object", "pilot-check", str(record), str(self.image)], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
