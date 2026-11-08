import unittest
from dataclasses import dataclass
from rules.comparative import check_comparative_phrases
from rules.clarifying import check_clarifying_members
from rules.contrastive import check_contrastive_conjunctions

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
            lemma, tag = text.lower(), ""
        elif len(item) == 3:
            text, pos, lemma = item
            tag = ""
        else:
            text, pos, lemma, tag = item
        result.append(Token(text, cursor, cursor + len(text), pos, lemma, tag))
        cursor += len(text) + 1
    return result

def sentence(items):
    return " ".join(item[0] for item in items)

class ComparativeTests(unittest.TestCase):
    def test_missing_comma_before_comparison(self):
        items = [("Он", "PRON"), ("был", "VERB", "быть"), ("упрям", "ADJ", "упрямый"),
                 ("как", "CONJ"), ("осёл", "NOUN"), (".", "PUNCT")]
        result = check_comparative_phrases(sentence(items), make_tokens(items))
        self.assertEqual(len(result), 1)
        self.assertIn("перед", result[0].suggestion)

    def test_correct_comparison(self):
        items = [("Он", "PRON"), ("был", "VERB", "быть"), ("упрям", "ADJ", "упрямый"),
                 (",", "PUNCT"), ("как", "CONJ"), ("осёл", "NOUN"), (".", "PUNCT")]
        self.assertEqual(check_comparative_phrases(sentence(items), make_tokens(items)), [])

    def test_role_meaning_without_comma(self):
        items = [("Он", "PRON"), ("работает", "VERB", "работать"), ("как", "CONJ"),
                 ("учитель", "NOUN"), (".", "PUNCT")]
        self.assertEqual(check_comparative_phrases(sentence(items), make_tokens(items)), [])

    def test_initial_as_and_construction_closes_with_comma(self):
        items = [("Как", "CONJ"), ("и", "CONJ"), ("брат", "NOUN"), ("он", "PRON"),
                 ("любит", "VERB"), ("спорт", "NOUN"), (".", "PUNCT")]
        result = check_comparative_phrases(sentence(items), make_tokens(items))
        self.assertEqual(len(result), 1)
        self.assertIn("после", result[0].suggestion)

    def test_missing_two_commas_around_parenthetical_comparison(self):
        items = [("Она", "PRON"), ("как", "CONJ"), ("мать", "NOUN"),
                 ("заботилась", "VERB"), ("о", "PREP"), ("сыне", "NOUN"), (".", "PUNCT")]
        result = check_comparative_phrases(sentence(items), make_tokens(items))
        self.assertEqual(len(result), 2)
        self.assertTrue(any("перед" in f.suggestion for f in result))
        self.assertTrue(any("после" in f.suggestion for f in result))

class ClarifyingTests(unittest.TestCase):
    def test_missing_two_commas_around_location_clarification(self):
        items = [("Там", "ADV"), ("у", "PREP"), ("реки", "NOUN"), ("стоял", "VERB"),
                 ("дом", "NOUN"), (".", "PUNCT")]
        result = check_clarifying_members(sentence(items), make_tokens(items))
        self.assertEqual(len(result), 2)
        self.assertTrue(any("после слова" in f.suggestion for f in result))
        self.assertTrue(any("после уточняющего" in f.suggestion for f in result))

    def test_correct_location_clarification(self):
        items = [("Там", "ADV"), (",", "PUNCT"), ("у", "PREP"), ("реки", "NOUN"),
                 (",", "PUNCT"), ("стоял", "VERB"), ("дом", "NOUN"), (".", "PUNCT")]
        self.assertEqual(check_clarifying_members(sentence(items), make_tokens(items)), [])

    def test_final_time_clarification_needs_one_comma(self):
        items = [("Мы", "PRON"), ("встретились", "VERB"), ("вечером", "NOUN"),
                 ("около", "PREP"), ("семи", "NUMR"), (".", "PUNCT")]
        result = check_clarifying_members(sentence(items), make_tokens(items))
        self.assertEqual(len(result), 1)
        self.assertIn("после слова", result[0].suggestion)

    def test_unrelated_time_word_not_flagged(self):
        items = [("Вчера", "ADV"), ("мы", "PRON"), ("гуляли", "VERB"), (".", "PUNCT")]
        self.assertEqual(check_clarifying_members(sentence(items), make_tokens(items)), [])

class ContrastiveTests(unittest.TestCase):
    def test_missing_comma_before_a_between_adjectives(self):
        items = [("Не", "PART"), ("красный", "ADJ"), ("а", "CONJ"), ("синий", "ADJ"), (".", "PUNCT")]
        result = check_contrastive_conjunctions(sentence(items), make_tokens(items))
        self.assertEqual(len(result), 1)

    def test_missing_comma_before_no_between_verbs(self):
        items = [("Хотел", "VERB"), ("прийти", "VERB"), ("но", "CONJ"), ("заболел", "VERB"), (".", "PUNCT")]
        result = check_contrastive_conjunctions(sentence(items), make_tokens(items))
        self.assertEqual(len(result), 1)

    def test_existing_comma_before_but(self):
        items = [("Не", "PART"), ("красный", "ADJ"), (",", "PUNCT"), ("а", "CONJ"), ("синий", "ADJ"), (".", "PUNCT")]
        self.assertEqual(check_contrastive_conjunctions(sentence(items), make_tokens(items)), [])

    def test_da_in_meaning_of_but_with_hint(self):
        items = [("мал", "ADJ", "малый"), ("золотник", "NOUN"), ("да", "CONJ"),
                 ("дорог", "ADJ"), (".", "PUNCT")]
        result = check_contrastive_conjunctions(sentence(items), make_tokens(items))
        self.assertEqual(len(result), 1)

    def test_da_as_joining_conjunction_is_not_flagged(self):
        items = [("Быстро", "ADV"), ("да", "CONJ"), ("аккуратно", "ADV"), (".", "PUNCT")]
        self.assertEqual(check_contrastive_conjunctions(sentence(items), make_tokens(items)), [])


    def test_already_punctuated_clarification_with_long_modifier(self):
        items = [("Здесь", "ADV"), (",", "PUNCT"), ("у", "PREP"),
                 ("старого", "ADJ"), ("моста", "NOUN"), (",", "PUNCT"),
                 ("начиналась", "VERB"), ("тропа", "NOUN"), (".", "PUNCT")]
        self.assertEqual(check_clarifying_members(sentence(items), make_tokens(items)), [])

    def test_already_punctuated_clarification_near_park(self):
        items = [("Там", "ADV"), (",", "PUNCT"), ("около", "PREP"),
                 ("старого", "ADJ"), ("парка", "NOUN"), (",", "PUNCT"),
                 ("стоял", "VERB"), ("киоск", "NOUN"), (".", "PUNCT")]
        self.assertEqual(check_clarifying_members(sentence(items), make_tokens(items)), [])

    def test_contrastive_a_between_predicative_parts_with_different_pos(self):
        items = [("День", "NOUN"), ("был", "VERB"), ("пасмурным", "ADJ"),
                 ("а", "CONJ"), ("вечер", "NOUN"), ("солнечным", "ADJ"), (".", "PUNCT")]
        self.assertEqual(len(check_contrastive_conjunctions(sentence(items), make_tokens(items))), 1)

if __name__ == "__main__":
    unittest.main()
