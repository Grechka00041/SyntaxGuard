import unittest
from evaluation import calculate_metrics, evaluate_records


class EvaluationMetricTests(unittest.TestCase):
    def test_perfect_classifier(self):
        result = calculate_metrics([1, 1, 0, 0], [1, 1, 0, 0])
        self.assertEqual((result["tp"], result["fp"], result["tn"], result["fn"]), (2, 0, 2, 0))
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["f1"], 1.0)

    def test_false_positive_and_false_negative(self):
        result = calculate_metrics([1, 0, 1, 0], [1, 1, 0, 0])
        self.assertEqual((result["tp"], result["fp"], result["tn"], result["fn"]), (1, 1, 1, 1))
        self.assertAlmostEqual(result["precision"], 0.5)
        self.assertAlmostEqual(result["recall"], 0.5)
        self.assertAlmostEqual(result["f1"], 0.5)

    def test_zero_division_returns_zero(self):
        result = calculate_metrics([0, 0], [0, 0])
        self.assertEqual(result["precision"], 0.0)
        self.assertEqual(result["recall"], 0.0)
        self.assertEqual(result["f1"], 0.0)

    def test_mismatched_lengths_raise_error(self):
        with self.assertRaises(ValueError):
            calculate_metrics([1], [1, 0])

    def test_rule_level_exact_match_and_unexpected_rule(self):
        class FakeAnalyzer:
            def analyze_sentence(self, sentence):
                rules = {"bad intro": [{"rule": "Вводное слово"}],
                         "clean": [],
                         "bad wrong": [{"rule": "Обращение"}]}[sentence]
                return {"status": "error" if rules else "ok", "findings": rules}
        records = [
            {"sentence": "bad intro", "has_punctuation_error": True,
             "expected_rules": ["Вводное слово"], "rule_group": "Вводное слово"},
            {"sentence": "clean", "has_punctuation_error": False,
             "expected_rules": [], "rule_group": "Вводное слово"},
            {"sentence": "bad wrong", "has_punctuation_error": True,
             "expected_rules": ["Вводное слово"], "rule_group": "Вводное слово"},
        ]
        report = evaluate_records(records, FakeAnalyzer())
        self.assertEqual(report["metrics"]["tp"], 2)
        self.assertEqual(report["rule_level_metrics"]["Вводное слово"]["fn"], 1)
        self.assertEqual(report["rule_level_metrics"]["Обращение"]["fp"], 1)
        self.assertEqual(report["exact_rule_matches"], 2)


if __name__ == "__main__":
    unittest.main()
