from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


generator = module("generator", "src/generate_cases.py")
evaluator = module("evaluator", "src/evaluate.py")
mutator = module("mutator", "src/mutate_expectation.py")


class FixtureTests(unittest.TestCase):
    def test_generator_is_deterministic(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            generator.write_cases(Path(first) / "fixtures")
            generator.write_cases(Path(second) / "fixtures")
            left = {p.name: p.read_bytes() for p in (Path(first) / "fixtures").iterdir()}
            right = {p.name: p.read_bytes() for p in (Path(second) / "fixtures").iterdir()}
            self.assertEqual(left, right)

    def test_case_ids_match_expectations(self):
        expected = json.loads((ROOT / "expectations.json").read_text(encoding="utf-8"))
        self.assertEqual({case["id"] for case in generator.CASES}, set(expected["expected"]["cases"]))

    def test_unique_pairs_are_equivalent(self):
        case = next(item for item in generator.CASES if item["id"] == "legacy-unique-pairs")
        observed, migrated, _ = evaluator.classify(generator.document(case["environmentVars"], case["id"]), case["shape"])
        self.assertEqual("EQUIVALENT_NORMALIZATION", observed)
        self.assertIsNotNone(migrated)

    def test_duplicate_names_are_unverifiable(self):
        case = next(item for item in generator.CASES if item["id"] == "legacy-conflicting-name")
        observed, migrated, _ = evaluator.classify(generator.document(case["environmentVars"], case["id"]), case["shape"])
        self.assertEqual("UNVERIFIABLE", observed)
        self.assertIsNone(migrated)

    def test_null_is_unverifiable_backwards(self):
        case = next(item for item in generator.CASES if item["id"] == "candidate-null-unset")
        observed, migrated, _ = evaluator.classify(generator.document(case["environmentVars"], case["id"]), case["shape"])
        self.assertEqual("UNVERIFIABLE", observed)
        self.assertIsNone(migrated)


if __name__ == "__main__":
    unittest.main()
