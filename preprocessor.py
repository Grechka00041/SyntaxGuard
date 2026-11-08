"""Токенизация и морфологический анализ текста SyntaxGuard."""
from dataclasses import dataclass
import re
import pymorphy3

morph = pymorphy3.MorphAnalyzer()

TAG_MAPPING = {
    "NOUN": "NOUN", "VERB": "VERB", "INFN": "VERB",
    "ADJF": "ADJ", "ADJS": "ADJ", "COMP": "ADJ",
    "GRND": "DEEPR", "PRTF": "PART", "PRTS": "PART_SHORT",
    "PREP": "PREP", "CONJ": "CONJ", "INTJ": "INTJ",
    "PRON": "PRON", "NPRO": "PRON", "NUMR": "NUMR", "ADVB": "ADV",
    "PRED": "PRED", "PRCL": "PARTICLE",
}

TOKEN_RE = re.compile(r"\w+(?:[-’'][\w]+)*|[,.!?;:—–()-]", re.UNICODE)

@dataclass
class Token:
    text: str
    start: int
    end: int
    pos: str
    lemma: str = ""
    morph_tag: str = ""
    possible_pos: tuple = ()

    @property
    def is_punctuation(self):
        return self.text in ",.!?;:—–()-"

def analyze_word(word):
    parses = morph.parse(word)
    if not parses:
        return "UNKN", word.lower(), "", ()
    # Основная часть речи берётся из наиболее вероятного разбора.
    parse = parses[0]
    possible_pos = set()
    # Сохраняем достаточно вероятные альтернативы. Это помогает распознавать
    # отглагольные прилагательные, у которых есть причастный разбор
    # (например, «ведущая» в «дорога, ведущая к озеру»).
    for alternative in parses:
        alternative_pos = TAG_MAPPING.get(alternative.tag.POS, "UNKN")
        if alternative.score >= 0.20 and alternative_pos in {"PART", "PART_SHORT"}:
            possible_pos.add(alternative_pos)
    return (TAG_MAPPING.get(parse.tag.POS, "UNKN"), parse.normal_form,
            str(parse.tag), tuple(sorted(possible_pos)))


def get_pos_tag(word):
    """Совместимость с прежним интерфейсом: часть речи и лемма."""
    pos, lemma, _, _ = analyze_word(word)
    return pos, lemma

def tokenize_and_tag(sentence):
    result = []
    for match in TOKEN_RE.finditer(sentence):
        word = match.group()
        if word in ",.!?;:—–()-":
            result.append(Token(word, match.start(), match.end(), "PUNCT", word, ""))
        else:
            pos, lemma, morph_tag, possible_pos = analyze_word(word)
            result.append(Token(word, match.start(), match.end(), pos, lemma, morph_tag, possible_pos))
    return result

def sentence_to_tags(sentence):
    """Совместимость со старой версией проекта."""
    return " ".join(t.pos if not t.is_punctuation else t.text
                    for t in tokenize_and_tag(sentence))
