"""Тесты начальной эвристики сложносочинённых предложений."""
import unittest
from dataclasses import dataclass
from rules.compound import check_compound_sentences

@dataclass
class Token:
    text: str
    start: int
    end: int
    pos: str
    lemma: str = ""
    morph_tag: str = ""

    @property
    def is_punctuation(self):
        return self.text in ",.!?;:—–()-"


def make_tokens(items):
    result, cursor = [], 0
    for item in items:
        if len(item) == 2:
            text, pos = item
            tag = ""
        else:
            text, pos, tag = item
        result.append(Token(text, cursor, cursor + len(text), pos, text.lower(), tag))
        cursor += len(text) + 1
    return result


class CompoundSentenceTests(unittest.TestCase):
    def check(self, items):
        return check_compound_sentences(" ".join(item[0] for item in items), make_tokens(items))

    def test_missing_comma_before_i_with_new_subject(self):
        result = self.check([
            ("Солнце", "NOUN"), ("село", "VERB"), ("и", "CONJ"),
            ("ветер", "NOUN"), ("поднялся", "VERB"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 1)
        self.assertIn("перед союзом", result[0].suggestion)

    def test_correct_comma_before_i_with_new_subject(self):
        self.assertEqual(self.check([
            ("Солнце", "NOUN"), ("село", "VERB"), (",", "PUNCT"),
            ("и", "CONJ"), ("ветер", "NOUN"), ("поднялся", "VERB"), (".", "PUNCT")
        ]), [])

    def test_missing_comma_before_impersonal_second_clause(self):
        self.assertEqual(len(self.check([
            ("Солнце", "NOUN"), ("село", "VERB"), ("и", "CONJ"),
            ("стало", "VERB"), ("холодно", "PRED"), (".", "PUNCT")
        ])), 1)

    def test_same_subject_homogeneous_predicates_need_no_comma(self):
        self.assertEqual(self.check([
            ("Маша", "NOUN"), ("пришла", "VERB"), ("и", "CONJ"),
            ("села", "VERB"), (".", "PUNCT")
        ]), [])

    def test_same_subject_with_adverb_does_not_need_comma(self):
        self.assertEqual(self.check([
            ("Маша", "NOUN"), ("пришла", "VERB"), ("и", "CONJ"),
            ("быстро", "ADV"), ("села", "VERB"), (".", "PUNCT")
        ]), [])

    def test_missing_comma_before_but_with_new_subject(self):
        self.assertEqual(len(self.check([
            ("Дождь", "NOUN"), ("закончился", "VERB"), ("но", "CONJ"),
            ("ветер", "NOUN"), ("усилился", "VERB"), (".", "PUNCT")
        ])), 1)

    def test_does_not_flag_conjunction_without_two_predicates(self):
        self.assertEqual(self.check([
            ("Купил", "VERB"), ("хлеб", "NOUN"), ("и", "CONJ"),
            ("молоко", "NOUN"), (".", "PUNCT")
        ]), [])

    def test_incorrect_comma_is_not_reported_as_missing(self):
        self.assertEqual(self.check([
            ("Дождь", "NOUN"), ("закончился", "VERB"), (",", "PUNCT"),
            ("но", "CONJ"), ("ветер", "NOUN"), ("усилился", "VERB"), (".", "PUNCT")
        ]), [])


    def test_missing_comma_before_i_with_pronoun_subject(self):
        result = self.check([
            ("Я", "PRON"), ("позвонил", "VERB"), ("тебе", "PRON"),
            ("и", "CONJ"), ("ты", "PRON"), ("сразу", "ADV"),
            ("ответил", "VERB"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 1)

if __name__ == "__main__":
    unittest.main()
