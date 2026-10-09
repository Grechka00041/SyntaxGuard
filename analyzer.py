import nltk
from nltk import CFG, ChartParser
from preprocessor import sentence_to_tags

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

# ГРАММАТИКА ВНУТРИ КОДА
GRAMMAR_TEXT = """
S -> NP VP
S -> NP VP AdvP_Modifier
S -> AdvP PUNCT S
S -> S PUNCT AdvP
S -> Intro PUNCT S
S -> S PP
S -> S AdvP_Modifier
S -> AdvP_Modifier S
S -> AdvP_Modifier VP

NP -> NOUN
NP -> ADJ NOUN
NP -> PRON
NP -> NUMR
NP -> NOUN RelClause
NP -> RelClause NOUN
NP -> NP PP
NP -> NP CONJ NP
NP -> NOUN CONJ NOUN
NP -> NOUN NOUN
NP -> NOUN AdvP_Modifier

VP -> VERB
VP -> VERB NP
VP -> VERB NP NP
VP -> VERB AdvP_Modifier
VP -> VP PP
VP -> AdvP_Modifier VP

AdvP -> DEEPR
AdvP -> DEEPR NP
AdvP_Modifier -> ADV

RelClause -> PART
RelClause -> PART NP
RelClause -> PART PP
RelClause -> PRON VP
RelClause -> PRON AdvP_Modifier VP
RelClause -> ADJ VP
RelClause -> ADJ AdvP_Modifier VP

Intro -> INTRO
PP -> PREP NP

NOUN -> "NOUN"
VERB -> "VERB"
ADJ -> "ADJ"
DEEPR -> "DEEPR"
PART -> "PART"
PREP -> "PREP"
CONJ -> "CONJ"
INTRO -> "INTRO"
PRON -> "PRON"
NUMR -> "NUMR"
ADV -> "ADV"
UNKN -> "UNKN"
PUNCT -> ","
"""


class SyntaxAnalyzer:
    def __init__(self):
        try:
            self.grammar = CFG.fromstring(GRAMMAR_TEXT)
            self.parser = ChartParser(self.grammar)
            print("✅ Грамматика успешно создана")
        except Exception as e:
            raise RuntimeError(f"Ошибка создания грамматики: {e}")

    def _check_punctuation_error(self, tokens):
        """Проверяет ТОЛЬКО наличие запятой после DEEPR и PART."""

        # 1. Деепричастный оборот
        if 'DEEPR' in tokens:
            idx = tokens.index('DEEPR')
            has_punct = False
            for i in range(idx + 1, min(idx + 5, len(tokens))):
                if tokens[i] == 'PUNCT':
                    has_punct = True
                    break
                # Если встретили глагол или существительное до запятой — ошибка
                if tokens[i] in ['VERB', 'NOUN', 'PRON']:
                    break

            if not has_punct:
                return "❌ Пропущена запятая после деепричастного оборота."

        # 2. Причастный оборот
        if 'PART' in tokens:
            idx = tokens.index('PART')
            has_punct_after = False
            # Ищем запятую ПОСЛЕ причастия и его зависимых слов
            for i in range(idx + 1, min(idx + 6, len(tokens))):
                if tokens[i] == 'PUNCT':
                    has_punct_after = True
                    break

            if not has_punct_after:
                return "❌ Пропущена запятая при причастном обороте."

        return None

    def analyze_sentence(self, sentence):
        tags_str = sentence_to_tags(sentence)
        tokens = [t.strip() for t in tags_str.split() if t.strip()]

        if not tokens:
            return {"status": "empty", "color": None, "msg": ""}

        # ШАГ 1: ВСЕГДА проверяем пунктуацию первым делом
        punct_error = self._check_punctuation_error(tokens)
        if punct_error:
            # Если нашли ошибку пунктуации — сразу возвращаем красный,
            # даже если парсер мог бы построить дерево
            return {"status": "error", "color": "#ff4d4d", "msg": punct_error}

        # ШАГ 2: Если пунктуация в порядке, пробуем построить дерево
        try:
            trees = list(self.parser.parse(tokens))
        except Exception as e:
            return {"status": "error", "color": "#ff4d4d", "msg": f"Ошибка парсера: {str(e)}"}

        # Если деревьев нет — значит структурная ошибка
        if len(trees) == 0:
            return {"status": "error", "color": "#ff4d4d",
                    "msg": "❌ Синтаксическая ошибка: не удалось построить дерево разбора."}

        # Если деревья есть (одно или много) — всё ОК
        return {"status": "ok", "color": None, "msg": None}

    def analyze_full_text(self, text):
        results = []
        sentences = nltk.sent_tokenize(text)

        for sent in sentences:
            result = self.analyze_sentence(sent)
            results.append({"text": sent, **result})
        return results