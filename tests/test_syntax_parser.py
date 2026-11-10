"""Тесты КС-грамматики без зависимости от pymorphy3.

Используются синтетические токены, чтобы отдельно проверять грамматику и
построение дерева. Реальная морфология покрывается интеграционными тестами.
"""
import unittest
from dataclasses import dataclass

from syntax_parser import SyntaxParser


@dataclass
class FakeToken:
    text: str
    pos: str
    morph_tag: str = ""
    possible_pos: tuple = ()

    @property
    def is_punctuation(self):
        return self.pos == "PUNCT"


class ContextFreeGrammarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = SyntaxParser(max_trees=3)

    def parse(self, items):
        return self.parser.analyze_tokens([FakeToken(*item) for item in items])

    def test_simple_subject_predicate_object(self):
        result = self.parse([
            ("Студент", "NOUN"), ("читает", "VERB"), ("книгу", "NOUN"),
            (".", "PUNCT"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("S", result["trees"][0])
        self.assertIn("Студент", result["trees"][0])
        self.assertIn("читает", result["trees"][0])
        self.assertIn("книгу", result["trees"][0])
        self.assertEqual(len(result["tree_data"]), result["tree_count"])
        self.assertEqual(result["tree_data"][0]["label"], "S")

    def test_adjective_inside_noun_phrase(self):
        result = self.parse([
            ("Девушка", "NOUN"), ("читает", "VERB"),
            ("интересную", "ADJ"), ("книгу", "NOUN"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("NP", result["trees"][0])

    def test_compound_sentence(self):
        result = self.parse([
            ("Дождь", "NOUN"), ("закончился", "VERB"), ("и", "CONJ"),
            ("ветер", "NOUN"), ("усилился", "VERB"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("CONJ", result["tags"])

    def test_participial_phrase(self):
        result = self.parse([
            ("Студент", "NOUN"), ("решивший", "PART"),
            ("задачу", "NOUN"), ("получил", "VERB"), ("пятёрку", "NOUN"),
        ])
        self.assertEqual(result["status"], "parsed")

    def test_adjective_with_alternative_participle_analysis(self):
        result = self.parse([
            ("Дорога", "NOUN"), ("ведущая", "ADJ", "ADJF", ("PART",)),
            ("к", "PREP"), ("озеру", "NOUN"), ("была", "VERB"),
            ("пустой", "ADJ"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("PART", result["tags"])

    def test_punctuation_is_not_part_of_cfg_input(self):
        result = self.parse([
            ("Студент", "NOUN"), (",", "PUNCT"),
            ("читает", "VERB"), ("книгу", "NOUN"), (".", "PUNCT"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertNotIn("PUNCT", result["tags"])

    def test_unsupported_sequence_does_not_mean_punctuation_error(self):
        result = self.parse([
            ("неизвестное", "UNKN"), ("слово", "NOUN"),
        ])
        self.assertEqual(result["status"], "not_parsed")
        self.assertEqual(result["trees"], [])
        self.assertEqual(result["tree_data"], [])
        self.assertIn("не означает пунктуационную ошибку", result["message"])

    def test_initial_address_before_imperative_is_a_separate_cfg_node(self):
        result = self.parse([
            ("Маша", "PROPN", "NOUN,Name"),
            ("закрой", "VERB", "VERB,impr"),
            ("окно", "NOUN", "NOUN,inan,neut sing,accs"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["tags"], ["ADDR", "VERB", "NOUN"])
        self.assertIn("ADDR Маша", result["trees"][0])
        self.assertIn("NP (NOUN окно)", result["trees"][0])

    def test_middle_address_after_imperative_is_a_separate_cfg_node(self):
        result = self.parse([
            ("Скажи", "VERB", "VERB,impr"),
            ("Маша", "PROPN", "NOUN,Name"),
            ("правду", "NOUN"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["tags"][1], "ADDR")

    def test_short_participle_is_mapped(self):
        result = self.parse([
            ("Дом", "NOUN"), ("построен", "PART_SHORT"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("SHORT_PART", result["tags"])

    def test_greeting_after_proper_name(self):
        result = self.parse([
            ("Дима", "PROPN", "NOUN,Name sing,nomn"),
            ("привет", "NOUN", "NOUN,inan,neut sing,accs"),
            ("!", "PUNCT"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["tags"], ["ADDR", "GREETING"])
        self.assertIn("Дима", result["trees"][0])
        self.assertIn("привет", result["trees"][0])

    def test_greeting_before_proper_name(self):
        result = self.parse([
            ("Привет", "INTJ"),
            ("Дима", "PROPN", "NOUN,Name sing,nomn"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["tags"], ["GREETING", "ADDR"])

    def test_standalone_greeting(self):
        result = self.parse([("Здравствуйте", "INTJ")])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["tags"], ["GREETING"])

    def test_greeting_phrase_with_address(self):
        result = self.parse([
            ("Дима", "PROPN", "NOUN,Name sing,nomn"),
            ("доброе", "ADJ", "ADJF,neut,sing,nomn"),
            ("утро", "NOUN", "NOUN,inan,neut,sing,nomn"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["tags"][0], "ADDR")
        self.assertIn("GREETING_PHRASE", result["trees"][0])

    def test_word_privet_as_object_is_not_forced_to_greeting(self):
        result = self.parse([
            ("передай", "VERB", "VERB,impr"),
            ("привет", "NOUN", "NOUN,inan,masc,sing,accs"),
        ])
        # This two-word sequence should be parsed as a verb with object,
        # not as a standalone greeting.
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["tags"], ["VERB", "NOUN"])

    def test_greeting_phrase_before_address(self):
        result = self.parse([
            ("доброе", "ADJ", "ADJF,neut,sing,nomn"),
            ("утро", "NOUN", "NOUN,inan,neut,sing,nomn"),
            ("Дима", "PROPN", "NOUN,Name sing,nomn"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["tags"][-1], "ADDR")
        self.assertIn("GREETING_PHRASE", result["trees"][0])

    def test_verb_plus_infinitive(self):
        result = self.parse([
            ("Пошли", "VERB", "VERB,past,plur"),
            ("гулять", "VERB", "INFN,impf,intr"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["tags"], ["VERB", "INFN"])
        self.assertIn("INFN", result["trees"][0])

    def test_verb_infinitive_with_object(self):
        result = self.parse([
            ("Хочу", "VERB", "VERB,1per,sing"),
            ("читать", "VERB", "INFN,impf,tran"),
            ("книгу", "NOUN", "NOUN,inan,femn,sing,accs"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("NP (NOUN книгу)", result["trees"][0])

    def test_homogeneous_nouns(self):
        result = self.parse([
            ("Купил", "VERB"), ("хлеб", "NOUN"), ("молоко", "NOUN"),
            ("и", "CONJ"), ("сыр", "NOUN"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("HOMOG_NP", result["trees"][0])

    def test_homogeneous_adjectives_before_noun(self):
        result = self.parse([
            ("Выбрал", "VERB"), ("красные", "ADJ"), ("синие", "ADJ"),
            ("и", "CONJ"), ("зелёные", "ADJ"), ("карандаши", "NOUN"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("HOMOG_NP", result["trees"][0])

    def test_adverbial_modifier_before_clause(self):
        result = self.parse([
            ("Утром", "ADV"), ("студент", "NOUN"),
            ("прочитал", "VERB"), ("книгу", "NOUN"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("ADV", result["tags"])

    def test_prepositional_phrase_inside_noun_group(self):
        result = self.parse([
            ("Студент", "NOUN"), ("с", "PREP"), ("книгой", "NOUN"),
            ("читает", "VERB"), ("текст", "NOUN"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertIn("PP", result["trees"][0])

    def test_graphviz_representation_is_returned_for_parsed_tree(self):
        result = self.parse([
            ("Студент", "NOUN"), ("читает", "VERB"), ("книгу", "NOUN"),
        ])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(len(result["graphs"]), result["tree_count"])
        dot = result["graphs"][0]
        self.assertIn("digraph SyntaxTree", dot)
        self.assertIn('label="S"', dot)
        self.assertIn('label="Студент"', dot)
        self.assertIn('label="читает"', dot)
        self.assertIn('label="книгу"', dot)

    def test_graphviz_representation_is_empty_when_parse_fails(self):
        result = self.parse([
            ("неизвестное", "UNKN"), ("слово", "NOUN"),
        ])
        self.assertEqual(result["status"], "not_parsed")
        self.assertEqual(result["graphs"], [])

    def test_graphviz_escapes_quotes_in_word_labels(self):
        dot = self.parser.tree_to_graphviz("(S (NOUN \"слово\"))")
        self.assertIn('\\"слово\\"', dot)



if __name__ == "__main__":
    unittest.main()
