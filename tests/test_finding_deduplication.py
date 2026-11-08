import unittest
from rules.base import Finding, deduplicate_findings

class FindingDeduplicationTests(unittest.TestCase):
    def test_keeps_both_missing_commas_around_middle_address(self):
        before = Finding(
            "Обращение",
            "Обращение в середине предложения выделяется запятыми с двух сторон.",
            6, 11,
            "Поставьте запятую перед обращением.",
        )
        after = Finding(
            "Обращение",
            "Обращение в середине предложения выделяется запятыми с двух сторон.",
            6, 11,
            "Поставьте запятую после обращения.",
        )
        result = deduplicate_findings([before, after])
        self.assertEqual(len(result), 2)
        suggestions = {item.suggestion for item in result}
        self.assertIn("Поставьте запятую перед обращением.", suggestions)
        self.assertIn("Поставьте запятую после обращения.", suggestions)

    def test_removes_exact_duplicate(self):
        finding = Finding("Правило", "Ошибка", 1, 2, "Поставьте запятую.")
        self.assertEqual(deduplicate_findings([finding, finding]), [finding])

if __name__ == "__main__":
    unittest.main()
