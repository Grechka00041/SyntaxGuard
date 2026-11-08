"""Тесты базовой проверки перечислений однородных членов."""
import unittest
from dataclasses import dataclass
from rules.homogeneous import check_homogeneous_members

@dataclass
class Token:
    text: str
    start: int
    end: int
    pos: str
    lemma: str = ""

    @property
    def is_punctuation(self):
        return self.text in ",.!?;:—–()-"


def make_tokens(items):
    tokens = []
    cursor = 0
    for text, pos in items:
        tokens.append(Token(text, cursor, cursor + len(text), pos, text.lower()))
        cursor += len(text) + 1
    return tokens


class HomogeneousMemberTests(unittest.TestCase):
    def check(self, items):
        sentence = " ".join(text for text, _ in items)
        return check_homogeneous_members(sentence, make_tokens(items))

    def test_missing_comma_in_noun_list(self):
        result = self.check([
            ("Купил", "VERB"), ("хлеб", "NOUN"), ("молоко", "NOUN"),
            ("и", "CONJ"), ("сыр", "NOUN"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 1)
        self.assertIn("хлеб", result[0].suggestion)

    def test_correct_noun_list(self):
        self.assertEqual(self.check([
            ("Купил", "VERB"), ("хлеб", "NOUN"), (",", "PUNCT"),
            ("молоко", "NOUN"), ("и", "CONJ"), ("сыр", "NOUN"), (".", "PUNCT")
        ]), [])

    def test_two_homogeneous_members_with_i_need_no_comma(self):
        self.assertEqual(self.check([
            ("Купил", "VERB"), ("хлеб", "NOUN"), ("и", "CONJ"),
            ("молоко", "NOUN"), (".", "PUNCT")
        ]), [])

    def test_missing_comma_in_adjective_list(self):
        result = self.check([
            ("Выбрал", "VERB"), ("красные", "ADJ"), ("синие", "ADJ"),
            ("и", "CONJ"), ("зелёные", "ADJ"), ("карандаши", "NOUN"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 1)

    def test_more_than_two_items_flags_each_unseparated_boundary(self):
        result = self.check([
            ("Купил", "VERB"), ("хлеб", "NOUN"), ("молоко", "NOUN"),
            ("сыр", "NOUN"), ("и", "CONJ"), ("масло", "NOUN"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 2)

    def test_uses_or_conjunction(self):
        result = self.check([
            ("Выбери", "VERB"), ("чай", "NOUN"), ("кофе", "NOUN"),
            ("или", "CONJ"), ("сок", "NOUN"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 1)

    def test_does_not_flag_unrelated_nouns(self):
        self.assertEqual(self.check([
            ("Студент", "NOUN"), ("решил", "VERB"), ("задачу", "NOUN"),
            ("и", "CONJ"), ("ушёл", "VERB"), (".", "PUNCT")
        ]), [])


if __name__ == "__main__":
    unittest.main()
