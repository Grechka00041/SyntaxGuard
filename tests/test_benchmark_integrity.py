import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "benchmark.json"


class BenchmarkIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(CORPUS.read_text(encoding="utf-8"))

    def test_corpus_has_216_records(self):
        self.assertEqual(len(self.records), 216)

    def test_classes_are_balanced(self):
        positive = sum(bool(row["has_punctuation_error"]) for row in self.records)
        self.assertEqual(positive, 108)
        self.assertEqual(len(self.records) - positive, 108)

    def test_ids_and_sentences_are_unique(self):
        ids = [row["id"] for row in self.records]
        sentences = [row["sentence"].casefold() for row in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(sentences), len(set(sentences)))

    def test_each_group_has_12_positive_and_12_negative(self):
        counts = Counter((row["rule_group"], bool(row["has_punctuation_error"])) for row in self.records)
        groups = {row["rule_group"] for row in self.records}
        self.assertEqual(len(groups), 9)
        for group in groups:
            self.assertEqual(counts[(group, True)], 12, group)
            self.assertEqual(counts[(group, False)], 12, group)

    def test_expected_rules_match_binary_label(self):
        for row in self.records:
            if row["has_punctuation_error"]:
                self.assertEqual(row["expected_rules"], [row["rule_group"]], row["id"])
            else:
                self.assertEqual(row["expected_rules"], [], row["id"])

    def test_pairs_are_complete(self):
        pair_roles = {}
        for row in self.records:
            pair_roles.setdefault(row["pair_id"], set()).add(row["pair_role"])
        self.assertEqual(len(pair_roles), 108)
        self.assertTrue(all(roles == {"missing_comma", "correct_control"} for roles in pair_roles.values()))

    def test_development_and_holdout_are_balanced(self):
        development = [row for row in self.records if row["split"] == "development"]
        holdout = [row for row in self.records if row["split"] == "holdout"]
        self.assertEqual(len(development), 108)
        self.assertEqual(len(holdout), 108)
        self.assertEqual(sum(row["has_punctuation_error"] for row in holdout), 54)


if __name__ == "__main__":
    unittest.main()
