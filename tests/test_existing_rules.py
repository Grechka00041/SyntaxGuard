"""Регрессионные тесты для двух базовых правил SyntaxGuard.

Тесты используют искусственные морфологические токены, чтобы проверять
именно пунктуационную логику независимо от версии словаря pymorphy3.
Запуск из корня проекта: python -m unittest discover -s tests -v
"""
import unittest
from dataclasses import dataclass

@dataclass
class Token:
    text: str
    start: int
    end: int
    pos: str
    lemma: str = ""
    possible_pos: tuple = ()

    @property
    def is_punctuation(self):
        return self.text in ",.!?;:—–()-"
from rules.existing import (
    check_adverbial_participles,
    check_participial_phrases,
)
from rules.introductory import check_introductory_words


def make_tokens(items):
    tokens = []
    cursor = 0
    # Позиции последовательно рассчитываются по длине элементов;
    # фактический текст нужен только для проверок запятых по токенам.
    for text, pos in items:
        tokens.append(Token(text, cursor, cursor + len(text), pos, text.lower()))
        cursor += len(text) + 1
    return tokens


class AdverbialTests(unittest.TestCase):
    def check(self, items):
        return check_adverbial_participles(" ".join(x[0] for x in items), make_tokens(items))

    def test_missing_comma_at_sentence_start(self):
        items = [("Улыбаясь", "DEEPR"), ("она", "PRON"), ("вошла", "VERB"), (".", "PUNCT")]
        result = self.check(items)
        self.assertEqual(len(result), 1)
        self.assertIn("после", result[0].suggestion)

    def test_missing_comma_before_phrase_in_middle(self):
        items = [("Она", "PRON"), ("улыбалась", "VERB"), ("читая", "DEEPR"),
                 ("интересную", "ADJ"), ("книгу", "NOUN"), (".", "PUNCT")]
        result = self.check(items)
        self.assertEqual(len(result), 1)
        self.assertIn("перед", result[0].suggestion)

    def test_initial_phrase_with_dependent_noun(self):
        items = [("Анализируя", "DEEPR"), ("данные", "NOUN"), (",", "PUNCT"),
                 ("студент", "NOUN"), ("нашёл", "VERB"), ("ошибку", "NOUN"), (".", "PUNCT")]
        self.assertEqual(self.check(items), [])

    def test_correct_phrase_with_two_commas(self):
        items = [("Она", "PRON"), (",", "PUNCT"), ("улыбаясь", "DEEPR"),
                 (",", "PUNCT"), ("вошла", "VERB"), ("в", "PREP"),
                 ("комнату", "NOUN"), (".", "PUNCT")]
        self.assertEqual(self.check(items), [])


    def test_initial_negative_particle_is_part_of_gerund_phrase(self):
        items = [("Не", "PARTICLE"), ("заметив", "DEEPR"), ("ошибки", "NOUN"),
                 (",", "PUNCT"), ("редактор", "NOUN"), ("отправил", "VERB"),
                 ("текст", "NOUN"), (".", "PUNCT")]
        self.assertEqual(self.check(items), [])


class ParticipialTests(unittest.TestCase):
    def check(self, items):
        return check_participial_phrases(" ".join(x[0] for x in items), make_tokens(items))

    def test_missing_both_commas(self):
        items = [("Студент", "NOUN"), ("решивший", "PART"),
                 ("задачу", "NOUN"), ("получил", "VERB"), ("пятёрку", "NOUN"), (".", "PUNCT")]
        result = self.check(items)
        self.assertEqual(len(result), 2)
        self.assertTrue(any("перед" in f.suggestion for f in result))
        self.assertTrue(any("после" in f.suggestion for f in result))

    def test_correct_both_commas(self):
        items = [("Студент", "NOUN"), (",", "PUNCT"), ("решивший", "PART"),
                 ("задачу", "NOUN"), (",", "PUNCT"), ("получил", "VERB"),
                 ("пятёрку", "NOUN"), (".", "PUNCT")]
        self.assertEqual(self.check(items), [])

    def test_prepositive_participle_is_not_flagged(self):
        items = [("Построенный", "PART"), ("недавно", "ADV"),
                 ("дом", "NOUN"), ("выглядел", "VERB"), ("красиво", "ADV"), (".", "PUNCT")]
        self.assertEqual(self.check(items), [])

    def test_short_participle_predicate_is_not_flagged(self):
        items = [("Дом", "NOUN"), ("построен", "PART_SHORT"),
                 ("недавно", "ADV"), (".", "PUNCT")]
        self.assertEqual(self.check(items), [])


    def test_postpositive_participle_adjective_form_is_recognized(self):
        items = [("Дорога", "NOUN"), ("ведущая", "ADJ"), ("к", "PREP"),
                 ("озеру", "NOUN"), ("была", "VERB"), ("пустой", "ADJ"), (".", "PUNCT")]
        result = self.check(items)
        self.assertEqual(len(result), 2)
        self.assertTrue(any("перед" in f.suggestion for f in result))
        self.assertTrue(any("после" in f.suggestion for f in result))


class IntroductoryWordTests(unittest.TestCase):
    def check(self, words):
        sentence = " ".join(text for text, _ in words)
        return check_introductory_words(sentence, make_tokens(words))

    def test_missing_comma_after_introductory_phrase_at_start(self):
        result = self.check([
            ("К", "PREP"), ("сожалению", "NOUN"), ("я", "PRON"),
            ("опоздал", "VERB"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 1)
        self.assertIn("после", result[0].suggestion)

    def test_correct_introductory_phrase_at_start(self):
        self.assertEqual(self.check([
            ("К", "PREP"), ("сожалению", "NOUN"), (",", "PUNCT"),
            ("я", "PRON"), ("опоздал", "VERB"), (".", "PUNCT")
        ]), [])

    def test_missing_commas_around_introductory_word_in_middle(self):
        result = self.check([
            ("Он", "PRON"), ("конечно", "ADV"), ("придёт", "VERB"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 2)
        self.assertTrue(any("перед" in item.suggestion for item in result))
        self.assertTrue(any("после" in item.suggestion for item in result))

    def test_correct_introductory_word_in_middle(self):
        self.assertEqual(self.check([
            ("Он", "PRON"), (",", "PUNCT"), ("конечно", "ADV"),
            (",", "PUNCT"), ("придёт", "VERB"), (".", "PUNCT")
        ]), [])

    def test_missing_commas_around_multiword_introductory_phrase(self):
        result = self.check([
            ("Мне", "PRON"), ("к", "PREP"), ("сожалению", "NOUN"),
            ("пришлось", "VERB"), ("уйти", "VERB"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 2)

    def test_correct_multiword_introductory_phrase_in_middle(self):
        self.assertEqual(self.check([
            ("Мне", "PRON"), (",", "PUNCT"), ("к", "PREP"),
            ("сожалению", "NOUN"), (",", "PUNCT"), ("пришлось", "VERB"),
            ("уйти", "VERB"), (".", "PUNCT")
        ]), [])

    def test_introductory_word_at_sentence_end(self):
        result = self.check([
            ("Он", "PRON"), ("придёт", "VERB"), (",", "PUNCT"),
            ("вероятно", "ADV"), (".", "PUNCT")
        ])
        self.assertEqual(result, [])

    def test_hyphenated_introductory_word(self):
        result = self.check([
            ("Во-первых", "ADV"), ("надо", "PRED"),
            ("подготовиться", "VERB"), (".", "PUNCT")
        ])
        self.assertEqual(len(result), 1)
        self.assertIn("после", result[0].suggestion)

    def test_ambiguous_word_odnako_is_not_checked_yet(self):
        self.assertEqual(self.check([
            ("Он", "PRON"), ("однако", "CONJ"), ("пришёл", "VERB"), (".", "PUNCT")
        ]), [])


if __name__ == "__main__":
    unittest.main()
