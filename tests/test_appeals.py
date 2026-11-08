"""Тесты проверки обращений на синтетических морфологических токенах."""
import unittest
from dataclasses import dataclass
from rules.appeals import check_appeals

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


class AppealTests(unittest.TestCase):
    def check(self, items):
        return check_appeals(" ".join(item[0] for item in items), make_tokens(items))

    def test_missing_comma_after_name_at_start_before_imperative(self):
        result = self.check([
            ("Маша", "NOUN", "NOUN,anim,femn,Name,sing,nomn"),
            ("закрой", "VERB", "VERB,perf,tran,sing,impr"),
            ("дверь", "NOUN"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 1)
        self.assertIn("после", result[0].suggestion)

    def test_correct_comma_after_name_at_start(self):
        self.assertEqual(self.check([
            ("Маша", "NOUN", "NOUN,anim,femn,Name,sing,nomn"),
            (",", "PUNCT"), ("закрой", "VERB", "VERB,impr"),
            ("дверь", "NOUN"), (".", "PUNCT")
        ]), [])

    def test_missing_both_commas_around_middle_address(self):
        result = self.check([
            ("Скажи", "VERB", "VERB,impr"),
            ("Маша", "NOUN", "NOUN,anim,femn,Name,sing,nomn"),
            ("правду", "NOUN"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 2)
        self.assertTrue(any("перед" in f.suggestion for f in result))
        self.assertTrue(any("после" in f.suggestion for f in result))

    def test_correct_middle_address(self):
        self.assertEqual(self.check([
            ("Скажи", "VERB", "VERB,impr"), (",", "PUNCT"),
            ("Маша", "NOUN", "NOUN,Name"), (",", "PUNCT"),
            ("правду", "NOUN"), (".", "PUNCT")
        ]), [])

    def test_subject_at_sentence_start_is_not_address(self):
        self.assertEqual(self.check([
            ("Маша", "NOUN", "NOUN,Name"), ("пришла", "VERB", "VERB,past"),
            ("домой", "ADV"), (".", "PUNCT")
        ]), [])

    def test_subject_after_predicate_is_not_address(self):
        self.assertEqual(self.check([
            ("Пришла", "VERB", "VERB,past"), ("Маша", "NOUN", "NOUN,Name"),
            (".", "PUNCT")
        ]), [])

    def test_missing_comma_before_address_at_end(self):
        result = self.check([
            ("Спасибо", "INTJ"), ("Маша", "NOUN", "NOUN,Name"),
            ("!", "PUNCT")
        ])
        self.assertEqual(len(result), 1)
        self.assertIn("перед", result[0].suggestion)

    def test_role_phrase_as_teacher_is_not_misclassified_as_address(self):
        self.assertEqual(self.check([
            ("Он", "PRON"), ("работает", "VERB", "VERB,impf,intr"),
            ("как", "CONJ"), ("учитель", "NOUN"), (".", "PUNCT")
        ]), [])

    def test_noun_after_preposition_is_not_misclassified_as_address(self):
        self.assertEqual(self.check([
            ("Он", "PRON"), ("работает", "VERB"), ("в", "PREP"),
            ("качестве", "NOUN"), ("учителя", "NOUN"), (".", "PUNCT")
        ]), [])

    def test_comparative_phrase_in_middle_is_not_misclassified_as_address(self):
        self.assertEqual(self.check([
            ("Он", "PRON"), (",", "PUNCT"), ("как", "CONJ"),
            ("учитель", "NOUN", "NOUN,anim,masc,sing,nomn"),
            (",", "PUNCT"), ("объяснил", "VERB"),
            ("материал", "NOUN"), (".", "PUNCT")
        ]), [])

    def test_comparative_as_and_phrase_is_not_misclassified_as_address(self):
        self.assertEqual(self.check([
            ("Он", "PRON"), (",", "PUNCT"), ("как", "CONJ"),
            ("и", "CONJ"), ("брат", "NOUN", "NOUN,anim,masc,sing,nomn"),
            (",", "PUNCT"), ("любит", "VERB"), ("спорт", "NOUN"),
            (".", "PUNCT")
        ]), [])

    def test_role_phrase_in_middle_is_not_misclassified_as_address(self):
        self.assertEqual(self.check([
            ("Она", "PRON"), (",", "PUNCT"), ("в", "PREP"),
            ("качестве", "NOUN", "NOUN,loct"),
            ("докладчика", "NOUN", "NOUN,gen2"),
            (",", "PUNCT"), ("выступила", "VERB"), ("отлично", "ADV"),
            (".", "PUNCT")
        ]), [])

    def test_correct_comma_before_address_at_end(self):
        self.assertEqual(self.check([
            ("Спасибо", "INTJ"), (",", "PUNCT"),
            ("Маша", "NOUN", "NOUN,Name"), ("!", "PUNCT")
        ]), [])

    def test_accusative_direct_object_is_not_misclassified_as_address(self):
        self.assertEqual(self.check([
            ("Маша", "NOUN", "NOUN,Name"), (",", "PUNCT"),
            ("закрой", "VERB", "VERB,impr"), ("окно", "NOUN"),
            ("и", "CONJ"), ("позови", "VERB", "VERB,impr"),
            ("папу", "NOUN", "NOUN,anim,masc,accs,sing"), (".", "PUNCT")
        ]), [])


    def test_subject_after_initial_gerund_is_not_address(self):
        self.assertEqual(self.check([
            ("Увидев", "DEEPR"), ("друга", "NOUN"), (",", "PUNCT"),
            ("девушка", "NOUN"), ("улыбнулась", "VERB"), (".", "PUNCT")
        ]), [])

    def test_proper_name_subject_after_gerund_is_not_address(self):
        self.assertEqual(self.check([
            ("Прочитав", "DEEPR"), ("письмо", "NOUN"), (",", "PUNCT"),
            ("Анна", "NOUN", "NOUN,Name"), ("задумалась", "VERB"), (".", "PUNCT")
        ]), [])

    def test_colleagues_before_imperative_is_address(self):
        result = self.check([
            ("Коллеги", "NOUN"), ("обратите", "VERB", "VERB,impr"),
            ("внимание", "NOUN"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 1)
        self.assertIn("после", result[0].suggestion)

if __name__ == "__main__":
    unittest.main()
