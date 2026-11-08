import unittest
from ui_helpers import build_location_marker


class LocationMarkerTests(unittest.TestCase):
    def test_before_finding_points_to_start(self):
        sentence = "Он был упрям как осёл."
        finding = {"start": 12, "end": 21, "suggestion": "Поставьте запятую перед сравнительным оборотом."}
        excerpt, pointer, label = build_location_marker(sentence, finding)
        self.assertIn("^", pointer)
        self.assertIn("перед", label)

    def test_after_named_word_points_after_that_word(self):
        sentence = "Там у реки стоял дом."
        finding = {"start": 4, "end": 11, "suggestion": "Поставьте запятую после слова «Там»."}
        excerpt, pointer, label = build_location_marker(sentence, finding)
        self.assertIn("после слова «там»", label)
        self.assertEqual(pointer.index("^"), len("Там"))

    def test_after_phrase_points_to_end(self):
        sentence = "К сожалению я опоздала."
        finding = {"start": 0, "end": 11, "suggestion": "Поставьте запятую после вводного слова или сочетания."}
        excerpt, pointer, label = build_location_marker(sentence, finding)
        self.assertEqual(pointer.index("^"), 11)


if __name__ == "__main__":
    unittest.main()
