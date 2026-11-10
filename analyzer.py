"""Основной координатор пунктуационных правил."""
import re
from preprocessor import tokenize_and_tag
from rules.existing import check_adverbial_participles, check_participial_phrases
from rules.introductory import check_introductory_words
from rules.homogeneous import check_homogeneous_members
from rules.appeals import check_appeals
from rules.compound import check_compound_sentences
from rules.comparative import check_comparative_phrases
from rules.clarifying import check_clarifying_members
from rules.contrastive import check_contrastive_conjunctions
from rules.base import deduplicate_findings
from syntax_parser import SyntaxParser

try:
    import nltk
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        # Не загружаем данные из сети при запуске приложения.
        nltk = None
except ImportError:
    nltk = None

def split_sentences(text):
    if nltk is not None:
        try:
            return [s for s in nltk.sent_tokenize(text, language="russian") if s.strip()]
        except (LookupError, ValueError):
            pass
    # Резервное разделение, сохраняющее завершающий знак предложения.
    return [m.group().strip() for m in re.finditer(r"[^.!?]+(?:[.!?]+|$)", text)
            if m.group().strip()]

class SyntaxAnalyzer:
    def __init__(self):
        self.syntax_parser = SyntaxParser()
        self.rules = [
            check_adverbial_participles,
            check_participial_phrases,
            check_introductory_words,
            check_homogeneous_members,
            check_appeals,
            check_compound_sentences,
            check_comparative_phrases,
            check_clarifying_members,
            check_contrastive_conjunctions,
        ]

    def analyze_sentence(self, sentence):
        tokens = tokenize_and_tag(sentence)
        if not tokens:
            return {"status": "empty", "color": None, "msg": "", "findings": [],
                    "syntax": self.syntax_parser.analyze_tokens(tokens)}

        # CFG-разбор строит синтаксическое дерево независимо от проверки запятых.
        # Отсутствие дерева не считается пунктуационной ошибкой.
        syntax_result = self.syntax_parser.analyze_tokens(tokens)

        findings = []
        for rule in self.rules:
            findings.extend(rule(sentence, tokens))

        # Убираем только полностью одинаковые замечания. Рекомендации
        # перед/после обращения должны оставаться отдельными ошибками.
        findings = deduplicate_findings(findings)

        if findings:
            return {
                "status": "error", "color": "#d94848",
                "msg": "; ".join(f.message for f in findings),
                "findings": [f.__dict__ for f in findings],
                "syntax": syntax_result,
            }
        return {"status": "ok", "color": None, "msg": None, "findings": [],
                "syntax": syntax_result}

    def analyze_full_text(self, text):
        return [{"text": sentence, **self.analyze_sentence(sentence)}
                for sentence in split_sentences(text)]
