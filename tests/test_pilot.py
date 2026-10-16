import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from trace_object import __main__ as cli
from trace_object.core import validate
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


def candidate_fixture():
    data = fixture()
    data.update(format_version=2, lead_links=[{"lead_index": 0, "comparison_id": "CMP-001"}])
    data["record"] = json.loads((ROOT / "examples" / "known-object.json").read_text(encoding="utf-8"))
    lead = data["record"]["leads"][0]
    data["comparisons"] = [{
        "comparison_id": "CMP-001",
        "name": lead["hypothesis"], "sources": lead["sources"].copy(),
        "matches": lead["matches"].copy(), "contradictions": lead["contradictions"].copy(),
        "decision": "retained", "reason": "DEMO retained as the record hypothesis, not verified.",
        "next_checks": lead["next_checks"].copy(),
    }]
    data["conclusion"] = "DEMO: unconfirmed candidate based on the retained comparison."
    return data


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
        self.assertIn("comparisons: retained hypothesis requires candidate record outcome", validate_pilot(data))
        with self.assertRaises(ValueError):
            render_pilot(data, self.image)

    def test_candidate_with_all_rejected_is_invalid_and_cannot_report(self):
        data = candidate_fixture()
        data["comparisons"][0]["decision"] = "rejected"
        self.assertIn("comparisons: candidate outcome requires a retained comparison", validate_pilot(data, self.image))
        with self.assertRaises(ValueError):
            render_pilot(data, self.image)
        record = self.root / "inconsistent-candidate.json"
        record.write_text(json.dumps(data), encoding="utf-8")
        reports = ROOT / ".local" / "reports"
        before = set(reports.glob("*.txt"))
        for command in ("pilot-check", "pilot-report"):
            result = subprocess.run([sys.executable, "-m", "trace_object", command, str(record), str(self.image)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn(b"candidate outcome requires a retained comparison", result.stderr)
        self.assertEqual(set(reports.glob("*.txt")), before)

    def test_candidate_with_only_inconclusive_is_invalid(self):
        data = candidate_fixture()
        data["comparisons"][0]["decision"] = "inconclusive"
        self.assertIn("comparisons: candidate outcome requires a retained comparison", validate_pilot(data, self.image))

    def test_candidate_with_linked_retained_comparison_is_valid(self):
        data = candidate_fixture()
        # Other rejected alternatives must not invalidate a supported candidate.
        data["comparisons"].append({**fixture()["comparisons"][0], "comparison_id": "CMP-002"})
        self.assertEqual(validate_pilot(data, self.image), [])
        report = render_pilot(data, self.image)
        self.assertIn("неподтверждённый кандидат", report)
        self.assertIn("retained", report)
        self.assertIn(data["record"]["leads"][0]["hypothesis"], report)

    def test_each_lead_sources_belong_to_its_explicit_comparison(self):
        for lead_index in (0, 1):
            with self.subTest(lead_index=lead_index):
                data = candidate_fixture()
                lead = copy.deepcopy(data["record"]["leads"][0])
                lead.update(hypothesis="DEMO candidate B", sources=["https://example.invalid/catalog/b"])
                data["record"]["leads"].append(lead)
                data["comparisons"].append({**copy.deepcopy(data["comparisons"][0]), "comparison_id": "CMP-002", "name": lead["hypothesis"], "sources": lead["sources"].copy()})
                data["lead_links"].append({"lead_index": 1, "comparison_id": "CMP-002"})
                self.assertEqual(validate_pilot(data), [])
                data["record"]["leads"][lead_index]["sources"] = ["https://example.invalid/catalog/unrelated"]
                self.assertIn("lead_links: lead sources must belong to its referenced comparison", validate_pilot(data, self.image))

    def test_duplicate_comparison_id_is_rejected(self):
        data = candidate_fixture()
        data["comparisons"].append({**copy.deepcopy(data["comparisons"][0]), "name": "DEMO other variant", "decision": "rejected"})
        self.assertIn("comparisons: duplicate comparison_id", validate_pilot(data, self.image))
        with self.assertRaises(ValueError):
            render_pilot(data, self.image)

    def test_same_candidate_cannot_have_opposite_decisions_under_different_ids(self):
        for version in (1, 2):
            with self.subTest(version=version):
                data = candidate_fixture() if version == 2 else fixture()
                data["comparisons"][0]["sources"].append("https://example.invalid/catalog/second-view")
                item = copy.deepcopy(data["comparisons"][0])
                item.update(name="  " + item["name"].upper() + "  ", decision="rejected" if version == 2 else "inconclusive")
                item["sources"] = list(reversed(item["sources"]))
                if version == 2:
                    item["comparison_id"] = "CMP-002"
                data["comparisons"].append(item)
                self.assertIn("comparisons: duplicate candidate name and sources", validate_pilot(data, self.image))

    def test_common_source_cannot_link_a_rejected_candidate(self):
        data = candidate_fixture()
        data["comparisons"][0]["decision"] = "rejected"
        data["comparisons"].append({**copy.deepcopy(data["comparisons"][0]), "comparison_id": "CMP-002", "name": "DEMO other candidate on same page", "decision": "retained"})
        self.assertIn("lead_links: a lead must reference a retained comparison", validate_pilot(data, self.image))

    def test_distinct_candidates_can_share_a_catalog_source(self):
        data = candidate_fixture()
        lead = copy.deepcopy(data["record"]["leads"][0])
        lead["hypothesis"] = "DEMO distinct candidate B on same catalog page"
        data["record"]["leads"].append(lead)
        data["comparisons"].append({**copy.deepcopy(data["comparisons"][0]), "comparison_id": "CMP-002", "name": lead["hypothesis"]})
        data["lead_links"].append({"lead_index": 1, "comparison_id": "CMP-002"})
        self.assertEqual(validate_pilot(data, self.image), [])

    def test_retained_comparison_cannot_be_absent_from_leads(self):
        data = candidate_fixture()
        data["comparisons"].append({**copy.deepcopy(data["comparisons"][0]), "comparison_id": "CMP-002", "name": "DEMO unreferenced candidate"})
        self.assertIn("lead_links: every retained comparison requires a lead", validate_pilot(data))

    def test_links_must_be_complete_unique_and_well_formed(self):
        cases = [None, {}, [], [{"lead_index": True, "comparison_id": "CMP-001"}],
                 [{"lead_index": -1, "comparison_id": "CMP-001"}],
                 [{"lead_index": 1, "comparison_id": "CMP-001"}],
                 [{"lead_index": 0, "comparison_id": "MISSING"}],
                 [{"lead_index": 0, "comparison_id": []}],
                 [{"lead_index": 0}], [None]]
        for links in cases:
            with self.subTest(links=links):
                data = candidate_fixture()
                data["lead_links"] = links
                self.assertTrue(validate_pilot(data))
        data = candidate_fixture()
        data["lead_links"] *= 2
        self.assertIn("lead_links: each lead must have exactly one link", validate_pilot(data))
        data = candidate_fixture()
        data["record"]["leads"].append(copy.deepcopy(data["record"]["leads"][0]))
        data["lead_links"].append({"lead_index": 1, "comparison_id": "CMP-001"})
        self.assertIn("lead_links: a comparison cannot support multiple leads", validate_pilot(data))

    def test_version_and_comparison_ids_are_strict(self):
        for value in (None, True, 0, 3, "2", []):
            data = candidate_fixture()
            data["format_version"] = value
            self.assertTrue(validate_pilot(data))
        for value in (None, [], True, "", "with spaces", "x" * 65):
            data = candidate_fixture()
            data["comparisons"][0]["comparison_id"] = value
            self.assertIn("comparisons: invalid comparison_id", validate_pilot(data))
        data = candidate_fixture()
        del data["lead_links"]
        self.assertTrue(validate_pilot(data))
        data = candidate_fixture()
        del data["comparisons"][0]["comparison_id"]
        self.assertTrue(validate_pilot(data))

    def test_legacy_candidate_requires_explicit_v2_migration(self):
        data = candidate_fixture()
        data["format_version"] = 1
        del data["lead_links"]
        del data["comparisons"][0]["comparison_id"]
        self.assertIn("format_version: candidate pilots require version 2 with explicit lead_links", validate_pilot(data))
        # The standalone schema_version: 1 record remains supported.
        self.assertEqual(validate(data["record"]), [])

    def test_v2_insufficient_data_without_candidates_is_valid(self):
        data = fixture()
        data.update(format_version=2, comparisons=[], lead_links=[])
        self.assertEqual(validate_pilot(data, self.image), [])
        self.assertIn("РЕЗУЛЬТАТ ПО OUTCOME: недостаточно данных", render_pilot(data, self.image))
        data["comparisons"] = [{**fixture()["comparisons"][0], "comparison_id": "CMP-001", "decision": "retained"}]
        self.assertIn("comparisons: retained hypothesis requires candidate record outcome", validate_pilot(data))

    def test_report_status_comes_from_outcome_not_operator_conclusion(self):
        for data, expected in ((fixture(), "недостаточно данных"), (candidate_fixture(), "неподтверждённый кандидат")):
            with self.subTest(outcome=data["record"]["outcome"]):
                data["conclusion"] = "DEMO contradictory claim: confirmed exact match.\nВЫВОД: DEMO confirmed"
                self.assertEqual(validate_pilot(data, self.image), [])
                lines = render_pilot(data, self.image).splitlines()
                self.assertEqual(lines[1], "РЕЗУЛЬТАТ ПО OUTCOME: " + expected)
                self.assertIn("ИТОГ ПО OUTCOME: " + expected, lines)
                self.assertIn("КОММЕНТАРИЙ ОПЕРАТОРА — НЕ ПРОВЕРЕН ПРОГРАММОЙ:", lines)
                self.assertIn("> ВЫВОД: DEMO confirmed", lines)
                self.assertNotIn("ВЫВОД: DEMO confirmed", lines)
                self.assertGreater(lines.index("> ВЫВОД: DEMO confirmed"), lines.index("СРАВНЕНИЯ:"))

    def test_render_without_image_is_rejected_before_hash_claim(self):
        data = fixture()
        data["provenance"]["sha256"] = "0" * 64
        self.assertEqual(validate_pilot(data), [])  # Explicit structural-only validation.
        with patch("trace_object.pilot.fingerprint") as hash_file:
            with self.assertRaisesRegex(ValueError, "local file is required"):
                render_pilot(data, None)
            hash_file.assert_not_called()

    def test_v2_candidate_example_and_cli_report(self):
        data = json.loads((ROOT / "examples" / "pilot-candidate.json").read_text(encoding="utf-8"))
        self.assertEqual(data, candidate_fixture())
        record = self.root / "candidate.json"
        record.write_text(json.dumps(data), encoding="utf-8")
        checked = subprocess.run([sys.executable, "-m", "trace_object", "pilot-check", str(record), str(self.image)], cwd=ROOT, capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["trace_object", "pilot-report", str(record), str(self.image)]), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(), 0)
        reports = list((self.root / ".local" / "reports").glob("*.txt"))
        self.assertEqual(len(reports), 1)
        report = reports[0].read_text(encoding="utf-8")
        self.assertIn("leads[0] -> CMP-001", report)
        self.assertIn("Предоставленные локальные байты совпадают с записью: ДА", report)

    def test_logged_search_with_no_candidates_is_valid_and_reproducible(self):
        data = fixture()
        data["comparisons"] = []
        data["searches"][0]["result_note"] = "DEMO completed mock search; no candidate found."
        self.assertEqual(validate_pilot(data, self.image), [])
        report = render_pilot(data, self.image)
        self.assertIn("Кандидаты не найдены", report)
        self.assertNotIn("DEMO fictional candidate", report)
        record = self.root / "no-candidates.json"
        record.write_text(json.dumps(data), encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "trace_object", "pilot-check", str(record), str(self.image)], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_candidates_does_not_allow_an_unexecuted_search(self):
        data = fixture()
        data.update(comparisons=[], searches=[])
        self.assertTrue(validate_pilot(data, self.image))

    def test_candidate_outcome_requires_a_comparison(self):
        data = fixture()
        data["record"] = json.loads((ROOT / "examples" / "known-object.json").read_text(encoding="utf-8"))
        data["comparisons"] = []
        self.assertIn("comparisons: empty list requires insufficient_data after a logged search", validate_pilot(data, self.image))

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
