"""Токенизация и морфологический анализ текста."""
from dataclasses import dataclass
import re
import pymorphy3

morph = pymorphy3.MorphAnalyzer()

TAG_MAPPING = {
    "NOUN": "NOUN",
    "VERB": "VERB",
    "INFN": "VERB",

    "ADJF": "ADJ",
    "ADJS": "ADJ",
    "COMP": "ADJ",

    "GRND": "DEEPR",
    "PRTF": "PART",
    "PRTS": "PART_SHORT",

    "PREP": "PREP",
    "CONJ": "CONJ",
    "INTJ": "INTRO",

    "PRON": "PRON",
    "NPRO": "PRON",
    "NUMR": "NUMR",
    "ADVB": "ADV",

    "PRED": "PRED",
    "PRCL": "PARTICLE",
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

    parse = parses[0]

    # Субстантивированные причастия и прилагательные: «данные», «больной»,
    # «заведующий». Если разбор NOUN почти не уступает основному, берём его.
    if TAG_MAPPING.get(parse.tag.POS) in {"PART", "ADJ"}:
        for alternative in parses[1:]:
            if alternative.tag.POS == "NOUN" and alternative.score >= parse.score * 0.6:
                parse = alternative
                break

    possible_pos = set()
    for alternative in parses:
        alt_pos = TAG_MAPPING.get(alternative.tag.POS, "UNKN")
        if alternative.score >= 0.20 and alt_pos in {"PART", "PART_SHORT"}:
            possible_pos.add(alt_pos)

    return (
        TAG_MAPPING.get(parse.tag.POS, "UNKN"),
        parse.normal_form,
        str(parse.tag),
        tuple(sorted(possible_pos)),
    )


def get_pos_tag(word):
    pos, lemma, _, _ = analyze_word(word)
    return pos, lemma


def tokenize_and_tag(sentence):
    """Объекты Token с позициями, леммами и морфологией — для эвристик и CFG."""
    result = []

    for match in TOKEN_RE.finditer(sentence):
        token_text = match.group()

        if token_text in ",.!?;:—–()-":
            result.append(
                Token(
                    text=token_text,
                    start=match.start(),
                    end=match.end(),
                    pos="PUNCT",
                    lemma=token_text,
                    morph_tag="",
                )
            )
            continue

        pos, lemma, morph_tag, possible_pos = analyze_word(token_text)

        result.append(
            Token(
                text=token_text,
                start=match.start(),
                end=match.end(),
                pos=pos,
                lemma=lemma,
                morph_tag=morph_tag,
                possible_pos=possible_pos,
            )
        )

    return result


def sentence_to_tags(sentence):
    return " ".join(
        token.pos if not token.is_punctuation else token.text
        for token in tokenize_and_tag(sentence)
    )