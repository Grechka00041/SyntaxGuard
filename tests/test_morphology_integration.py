"""Интеграционные тесты реального pymorphy3 + всех пунктуационных правил.

В отличие от модульных тестов с искусственными токенами, здесь анализируются
непосредственно исходные русские предложения. Если pymorphy3 не установлен,
тесты пропускаются с понятным сообщением; установите requirements.txt и повторите.
"""
import importlib.util
import unittest

HAS_PYMORPHY3 = importlib.util.find_spec("pymorphy3") is not None


@unittest.skipUnless(HAS_PYMORPHY3, "Для интеграционных тестов установите pymorphy3 из requirements.txt")
class RealMorphologyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from analyzer import SyntaxAnalyzer
        from preprocessor import tokenize_and_tag
        cls.analyzer = SyntaxAnalyzer()
        cls.tokenize_and_tag = staticmethod(tokenize_and_tag)

    def findings(self, sentence):
        return self.analyzer.analyze_sentence(sentence)["findings"]

    def test_morphology_recognizes_gerund(self):
        tokens = self.tokenize_and_tag("Улыбаясь, она вошла.")
        self.assertEqual(tokens[0].pos, "DEEPR")

    def test_morphology_recognizes_full_participle(self):
        tokens = self.tokenize_and_tag("Дом, построенный недавно, красив.")
        participles = [token for token in tokens if token.text.lower() == "построенный"]
        self.assertEqual(len(participles), 1)
        self.assertEqual(participles[0].pos, "PART")

    def test_morphology_keeps_short_participle_separate(self):
        tokens = self.tokenize_and_tag("Дом построен недавно.")
        participles = [token for token in tokens if token.text.lower() == "построен"]
        self.assertEqual(len(participles), 1)
        self.assertEqual(participles[0].pos, "PART_SHORT")

    def test_morphology_recognizes_imperative(self):
        tokens = self.tokenize_and_tag("Маша, закрой окно.")
        imperative = next(token for token in tokens if token.text.lower() == "закрой")
        self.assertIn("impr", imperative.morph_tag.lower())

    def test_morphology_recognizes_proper_name(self):
        tokens = self.tokenize_and_tag("Маша пришла домой.")
        name = next(token for token in tokens if token.text.lower() == "маша")
        self.assertIn("name", name.morph_tag.lower())

    def test_correct_sentence_set_has_no_findings(self):
        sentences = [
            "Она, улыбаясь, вошла в комнату.",
            "Построенный недавно дом выглядел красиво.",
            "Я, к счастью, успела.",
            "Купил хлеб, молоко и сыр.",
            "Маша, закрой окно.",
            "Дождь закончился, но ветер усилился.",
            "Он работает как учитель.",
            "Он, как учитель, объяснил материал.",
            "Он, как и брат, любит спорт.",
            "Там, у реки, стоял дом.",
            "Спасибо, мама!",
            "Увидев друга, девушка улыбнулась.",
            "Прочитав письмо, Анна задумалась.",
            "Не заметив ошибки, редактор отправил текст.",
            "Здесь, у старого моста, начиналась тропа.",
            "Там, около старого парка, стоял киоск.",
            "Он, как учитель, объяснил материал.",
            "Он, как и брат, любит спорт.",
            "Маша, закрой окно и позови папу.",
        ]
        for sentence in sentences:
            with self.subTest(sentence=sentence):
                self.assertEqual(self.findings(sentence), [])

    def test_missing_comma_examples_are_detected(self):
        examples = [
            ("К сожалению я опоздала.", "Вводное слово"),
            ("Маша закрой окно.", "Обращение"),
            ("Анализируя данные студент нашёл ошибку.", "Деепричастный оборот"),
            ("Студент решивший задачу получил пятёрку.", "Причастный оборот"),
            ("Купил хлеб молоко и сыр.", "Однородные члены предложения"),
            ("Дождь закончился но ветер усилился.", "Сложносочинённое предложение"),
            ("Он был упрям как осёл.", "Сравнительный оборот"),
            ("Там у реки стоял дом.", "Уточняющий член предложения"),
            ("Не красный а синий.", "Противительный союз"),
            ("Коллеги обратите внимание.", "Обращение"),
            ("Дорога ведущая к озеру была пустой.", "Причастный оборот"),
            ("День был пасмурным а вечер солнечным.", "Противительный союз"),
            ("Я позвонил тебе и ты сразу ответил.", "Сложносочинённое предложение"),
        ]
        for sentence, expected_rule in examples:
            with self.subTest(sentence=sentence):
                rules = {finding["rule"] for finding in self.findings(sentence)}
                self.assertIn(expected_rule, rules)

    def test_interaction_introductory_and_participial(self):
        sentence = "К сожалению студент решивший задачу опоздал."
        rules = [finding["rule"] for finding in self.findings(sentence)]
        self.assertIn("Вводное слово", rules)
        self.assertIn("Причастный оборот", rules)

    def test_interaction_address_and_other_clause(self):
        self.assertEqual(self.findings("Маша, закрой окно и позови папу."), [])
        self.assertEqual(self.findings("Позови маму."), [])

    def test_full_text_preserves_all_lines_as_sentences(self):
        text = "Маша, закрой окно. Он работает как учитель. Спасибо, мама!"
        results = self.analyzer.analyze_full_text(text)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(item["status"] == "ok" for item in results))


    def test_pronoun_npro_is_mapped_for_compound_sentence(self):
        tokens = self.tokenize_and_tag("Я позвонил тебе и ты сразу ответил.")
        pronoun = next(token for token in tokens if token.text.lower() == "ты")
        self.assertEqual(pronoun.pos, "PRON")

    def test_participle_like_postpositive_word_is_detected(self):
        result = self.analyzer.analyze_sentence("Дорога ведущая к озеру была пустой.")
        self.assertIn("Причастный оборот", {item["rule"] for item in result["findings"]})

    def test_initial_negative_gerund_phrase_with_existing_comma_is_clean(self):
        self.assertEqual(self.findings("Не заметив ошибки, редактор отправил текст."), [])

    def test_colleagues_address_before_imperative_is_detected(self):
        rules = {item["rule"] for item in self.findings("Коллеги обратите внимание.")}
        self.assertIn("Обращение", rules)

    def test_missing_contrastive_a_between_predicative_parts_is_detected(self):
        rules = {item["rule"] for item in self.findings("День был пасмурным а вечер солнечным.")}
        self.assertIn("Противительный союз", rules)

    def test_missing_compound_comma_with_pronoun_subject_is_detected(self):
        rules = {item["rule"] for item in self.findings("Я позвонил тебе и ты сразу ответил.")}
        self.assertIn("Сложносочинённое предложение", rules)


if __name__ == "__main__":
    unittest.main()
