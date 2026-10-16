import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from trace_object.core import render, source_url, validate


ROOT = Path(__file__).resolve().parent.parent


def example(name="known-object"):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text(encoding="utf-8"))


class Records(unittest.TestCase):
    def test_known_and_insufficient_demonstrations(self):
        for name in ("known-object", "insufficient-data"):
            data = example(name)
            self.assertEqual(validate(data), [])
            self.assertIn("DEMO", render(data))
        self.assertIn("недостаточно данных", render(example("insufficient-data")))

    def test_real_official_link_is_structural_only(self):
        data = example("insufficient-data")
        data.update(demo=False, object_id="C34012025", official_url="https://www.europol.europa.eu/stopchildabuse/6309")
        self.assertEqual(validate(data), [])
        for url in ("https://www.europol.europa.eu.evil.test/stopchildabuse/6309", "http://www.europol.europa.eu/stopchildabuse/6309", "https://user" + chr(64) + "www.europol.europa.eu/stopchildabuse/6309", "https://www.europol.europa.eu/stopchildabuse/6309?token=demo"):
            data["official_url"] = url
            self.assertTrue(validate(data))

    def test_source_urls_do_not_accept_credentials_local_or_tokens(self):
        for url in ("http://catalog.example.org/item", "https://user:pass" + chr(64) + "catalog.example.org/item", "https://127.0.0.1/item", "https://[::1]/item", "https://localhost/item", "https://catalog.local/item", "https://catalog.example.org:443/item", "https://catalog.example.org/item?token=x", "https://catalog.example.org/item#data", "https://example.invalid/item", "https://catalog.example.org\\@localhost/item"):
            self.assertFalse(source_url(url, False), url)
        self.assertTrue(source_url("https://catalog.example.org/item", False))

    def test_unknown_fields_and_invalid_states_fail(self):
        base = example()
        changes = [dict(extra="x"), dict(schema_version=True), dict(demo=1), dict(leads=[]), dict(outcome="confirmed"), dict(observations=[]), dict(description="\x1bunsafe")]
        for change in changes:
            data = copy.deepcopy(base)
            data.update(change)
            self.assertTrue(validate(data), change)
        data = example("insufficient-data")
        data["leads"] = base["leads"]
        self.assertTrue(validate(data))

    def test_candidate_requires_sources_contradictions_next_checks(self):
        for field, value in (("sources", []), ("contradictions", []), ("next_checks", []), ("confidence", 0.99)):
            data = example()
            data["leads"][0][field] = value
            self.assertTrue(validate(data))

    def test_malformed_types_do_not_crash_or_echo_input(self):
        for value in (None, [], "private-input", 1):
            self.assertTrue(validate(value))
        for field in example():
            for value in (None, [], {}, True, 1):
                data = example()
                data[field] = value
                result = validate(data)
                self.assertIsInstance(result, list)
                self.assertNotIn("private-input", " ".join(result))

    def test_cli_demo_and_validate(self):
        for args in (("demo",), ("validate", "examples/known-object.json"), ("validate", "examples/insufficient-data.json")):
            p = subprocess.run([sys.executable, "-m", "trace_object", *args], cwd=ROOT, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
