"""Контекстно-свободная грамматика.

Парсер строит дерево по последовательности морфологических категорий, полученных
от preprocessor.tokenize_and_tag. Он демонстрирует CFG и ChartParser, но не является
полным синтаксическим анализатором русского языка.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from typing import Iterable, List

try:
    from nltk import CFG, ChartParser, Tree
except ImportError:
    CFG = ChartParser = Tree = None


GRAMMAR_TEXT = r"""
# Типы предложений
S -> CLAUSE
S -> INTRO CLAUSE
S -> INTRO S
S -> ADDR CLAUSE
S -> ADDR GREETING
S -> GREETING ADDR
S -> GREETING
S -> GREETING_PHRASE
S -> ADDR GREETING_PHRASE
S -> GREETING_PHRASE ADDR
S -> ADDR
S -> S CONJ S

# Предикативная часть
CLAUSE -> NP VP
CLAUSE -> VP
CLAUSE -> NP PREDICATIVE
CLAUSE -> NP
CLAUSE -> PARTICLE CLAUSE
CLAUSE -> INTJ CLAUSE
CLAUSE -> INTRO CLAUSE
CLAUSE -> ADV CLAUSE
CLAUSE -> PP CLAUSE
CLAUSE -> DEEPR_PHRASE CLAUSE
CLAUSE -> CLAUSE PP
CLAUSE -> CLAUSE ADV
CLAUSE -> CLAUSE DEEPR_PHRASE
CLAUSE -> CLAUSE COMPARATIVE
CLAUSE -> CLAUSE CONJ CLAUSE
CLAUSE -> NP INTRO VP
CLAUSE -> VP ADDR
CLAUSE -> VP ADDR NP

# Именные группы
NP -> NOUN
NP -> PROPN
NP -> PRON
NP -> NUMR
NP -> ADJ
NP -> UNKN
NP -> ATTRS NOUN
NP -> ATTRS PROPN
NP -> ATTRS PRON
NP -> NP NOUN
NP -> NP PROPN
NP -> NP ADJ
NP -> NUMR NP
NP -> NP PP
NP -> NP REL_CLAUSE
NP -> REL_CLAUSE NP
NP -> NP CONJ NP
NP -> NP HOMOG_NP
NP -> HOMOG_NP
NP -> PARTICLE NP
NP -> NP COMPARATIVE

ATTRS -> ADJ
ATTRS -> PART
ATTRS -> NUMR
ATTRS -> ATTRS ADJ
ATTRS -> ATTRS PART
ATTRS -> ATTRS NUMR

# Перечисления, в том числе бессоюзные
HOMOG_NP -> NOUN NOUN
HOMOG_NP -> NOUN NOUN NOUN
HOMOG_NP -> NOUN NOUN NOUN NOUN
HOMOG_NP -> NOUN CONJ NOUN
HOMOG_NP -> NOUN NOUN CONJ NOUN
HOMOG_NP -> ADJ ADJ
HOMOG_NP -> ADJ CONJ ADJ
HOMOG_NP -> ADJ ADJ CONJ ADJ

# Глагольные группы
# Убрана продукция VP -> VP VP: она порождала бесконечную неоднозначность
# (комбинаторный взрыв) на любой цепочке глаголов.
VP -> VERB
VP -> INFN
VP -> ADV VP
VP -> PARTICLE VP
VP -> DEEPR_PHRASE VP
VP -> VP ADV
VP -> VP NP
VP -> VP PP
VP -> VP INFN
VP -> VP INFN NP
VP -> VP INFN PP
VP -> VP DEEPR_PHRASE
VP -> VP COMPARATIVE
VP -> VP REL_CLAUSE
VP -> VP CONJ VP

# Именное сказуемое
PREDICATIVE -> PRED
PREDICATIVE -> SHORT_ADJ
PREDICATIVE -> SHORT_PART
PREDICATIVE -> ADJ
PREDICATIVE -> ADV PREDICATIVE
PREDICATIVE -> PREDICATIVE ADV
PREDICATIVE -> PREDICATIVE NP
PREDICATIVE -> PREDICATIVE PP
PREDICATIVE -> PREDICATIVE INFN
PREDICATIVE -> PREDICATIVE COMPARATIVE

# Обороты
DEEPR_PHRASE -> DEEPR
DEEPR_PHRASE -> DEEPR NP
DEEPR_PHRASE -> DEEPR PP
DEEPR_PHRASE -> DEEPR ADV
DEEPR_PHRASE -> DEEPR INFN
DEEPR_PHRASE -> ADV DEEPR_PHRASE
DEEPR_PHRASE -> PARTICLE DEEPR_PHRASE

REL_CLAUSE -> PART
REL_CLAUSE -> PART NP
REL_CLAUSE -> PART PP
REL_CLAUSE -> PART ADV
REL_CLAUSE -> ADV REL_CLAUSE
REL_CLAUSE -> PRON VP
REL_CLAUSE -> PRON ADV VP

COMPARATIVE -> CONJ NP
COMPARATIVE -> CONJ ADJ
COMPARATIVE -> CONJ ADV
COMPARATIVE -> CONJ PP

PP -> PREP NP
GREETING_PHRASE -> GREETING_ADJ NOUN

# Терминалы
NOUN -> 'NOUN'
PROPN -> 'PROPN'
PRON -> 'PRON'
VERB -> 'VERB'
INFN -> 'INFN'
ADJ -> 'ADJ'
GREETING_ADJ -> 'GREETING_ADJ'
SHORT_ADJ -> 'SHORT_ADJ'
PART -> 'PART'
SHORT_PART -> 'SHORT_PART'
DEEPR -> 'DEEPR'
ADV -> 'ADV'
PREP -> 'PREP'
CONJ -> 'CONJ'
NUMR -> 'NUMR'
PRED -> 'PRED'
PARTICLE -> 'PARTICLE'
INTJ -> 'INTJ'
INTRO -> 'INTRO'
ADDR -> 'ADDR'
GREETING -> 'GREETING'
UNKN -> 'UNKN'
"""


# Предел длины входа: дальше число вариантов разбора растёт экспоненциально
MAX_CFG_TOKENS = 18

GREETING_WORDS = {"привет", "здравствуйте", "здравствуй", "салют"}
GREETING_PHRASES = {
    ("доброе", "утро"),
    ("добрый", "день"),
    ("добрый", "вечер"),
}

COMPOUND_PREPOSITIONS = [
    ("несмотря", "на"),
    ("невзирая", "на"),
    ("в", "течение"),
    ("в", "продолжение"),
    ("в", "отличие"),
    ("в", "силу"),
    ("в", "виде"),
    ("по", "мере"),
    ("за", "исключением"),
]

INTRODUCTORY_WORDS = {
    "конечно", "безусловно", "несомненно", "вероятно", "пожалуй",
    "например", "итак", "следовательно", "кстати", "впрочем",
    "во-первых", "во-вторых", "в-третьих", "по-видимому",
}

POS_ALIASES = {
    "INTRO": "INTJ",
    "ADJS": "ADJ",
    "ADJF": "ADJ",
    "COMP": "ADJ",
    "ADVB": "ADV",
    "NPRO": "PRON",
    "PRCL": "PARTICLE",
    "PRTF": "PART",
    "PRTS": "SHORT_PART",
    "GRND": "DEEPR",
}

SUPPORTED_POS = {
    "NOUN", "PROPN", "PRON", "VERB", "INFN", "ADJ", "SHORT_ADJ",
    "PART", "SHORT_PART", "DEEPR", "ADV", "PREP", "CONJ", "NUMR",
    "PRED", "PARTICLE", "INTJ", "INTRO", "GREETING", "GREETING_ADJ",
    "ADDR", "UNKN",
}


@dataclass(frozen=True)
class _Word:
    text: str
    pos: str


class SyntaxParser:
    """Строит до нескольких деревьев разбора по учебной русской CFG."""
    def __init__(self, max_trees: int = 3):
        if CFG is None or ChartParser is None or Tree is None:
            raise RuntimeError(
                "Для синтаксического разбора нужна библиотека NLTK. "
                "Установите зависимости: python -m pip install -r requirements.txt"
            )
        self.grammar = CFG.fromstring(GRAMMAR_TEXT)
        self.parser = ChartParser(self.grammar)
        self.max_trees = max(1, int(max_trees))

    @staticmethod
    def _normalized_pos(token) -> str:
        pos = getattr(token, "pos", "UNKN") or "UNKN"
        morph_tag = str(getattr(token, "morph_tag", "") or "").upper()
        possible_pos = set(getattr(token, "possible_pos", ()) or ())

        morph_head = morph_tag.split(",", 1)[0].strip()
        if morph_head == "INFN":
            return "INFN"

        if pos == "ADJ" and "PART" in possible_pos:
            return "PART"
        if pos == "PART_SHORT":
            return "SHORT_PART"
        if pos == "ADJ" and "ADJS" in morph_tag:
            return "SHORT_ADJ"
        if pos == "NOUN" and "NAME" in morph_tag:
            return "PROPN"

        pos = POS_ALIASES.get(pos, pos)
        return pos if pos in SUPPORTED_POS else "UNKN"

    @staticmethod
    def _merge_compound_prepositions(words, source_tokens):
        merged_words = []
        merged_sources = []
        i = 0
        while i < len(words):
            matched = None
            for phrase in COMPOUND_PREPOSITIONS:
                window = tuple(
                    words[j].text.lower().replace("ё", "е")
                    for j in range(i, min(i + len(phrase), len(words)))
                )
                if window == phrase:
                    matched = phrase
                    break
            if matched:
                text = " ".join(w.text for w in words[i:i + len(matched)])
                merged_words.append(_Word(text, "PREP"))
                merged_sources.append(source_tokens[i])
                i += len(matched)
                continue
            merged_words.append(words[i])
            merged_sources.append(source_tokens[i])
            i += 1
        return merged_words, merged_sources

    @staticmethod
    def _restore_subjects(words, source_tokens):
        """Вернуть ADDR роль подлежащего, если за ним следует сказуемое."""
        predicate_tags = {"VERB", "INFN", "PRED", "SHORT_ADJ", "SHORT_PART"}
        restored = list(words)
        for index in range(len(words) - 1):
            if words[index].pos != "ADDR":
                continue
            if words[index + 1].pos not in predicate_tags:
                continue
            token = source_tokens[index]
            category = SyntaxParser._normalized_pos(token)
            if category == "ADDR":
                morph_tag = str(getattr(token, "morph_tag", "") or "").upper()
                category = "PRON" if "NPRO" in morph_tag else "NOUN"
            restored[index] = _Word(words[index].text, category)
        return restored

    @staticmethod
    def _decorate_tree(tree, words: Iterable[_Word]):
        """Заменить листья-категории на исходные слова, сохранив узлы дерева."""
        iterator = iter(words)

        def visit(node):
            if isinstance(node, Tree):
                if len(node) == 1 and isinstance(node[0], str):
                    word = next(iterator)
                    return Tree(node.label(), [word.text])
                return Tree(node.label(), [visit(child) for child in node])
            return node

        return visit(tree)

    @staticmethod
    def _tree_to_data(tree):
        if isinstance(tree, Tree):
            if len(tree) == 1 and isinstance(tree[0], str):
                return {"label": str(tree.label()), "word": str(tree[0]), "children": []}
            return {
                "label": str(tree.label()),
                "children": [SyntaxParser._tree_to_data(child) for child in tree],
            }
        return {"label": str(tree), "children": []}

    @staticmethod
    def _dot_quote(value: str) -> str:
        return (str(value).replace("\\", "\\\\")
                .replace('"', '\\"').replace("\n", "\\n"))

    @classmethod
    def tree_to_graphviz(cls, tree) -> str:
        if isinstance(tree, str):
            tree = Tree.fromstring(tree)
        if not isinstance(tree, Tree):
            raise TypeError("Ожидалось дерево nltk.Tree или его строковое представление")

        lines = [
            "digraph SyntaxTree {",
            '  graph [rankdir="TB", bgcolor="transparent", nodesep="0.34", ranksep="0.48", pad="0.18", ordering="out"];',
            '  node [fontname="Arial", fontsize="11", style="rounded,filled", color="#64748b", penwidth="1.1", margin="0.12,0.08"];',
            '  edge [color="#94a3b8", penwidth="1.15", arrowsize="0.65"];',
        ]
        counter = 0

        def add_node(node, parent_id=None):
            nonlocal counter
            node_id = f"node_{counter}"
            counter += 1

            if isinstance(node, Tree):
                label = cls._dot_quote(node.label())
                lines.append(
                    f'  {node_id} [label="{label}", shape="box", fillcolor="#eaf1ff", fontcolor="#172554"];'
                )
                if parent_id is not None:
                    lines.append(f"  {parent_id} -> {node_id};")
                for child in node:
                    add_node(child, node_id)
            else:
                label = cls._dot_quote(node)
                lines.append(
                    f'  {node_id} [label="{label}", shape="ellipse", fillcolor="#e8f5ee", fontcolor="#14532d"];'
                )
                if parent_id is not None:
                    lines.append(f"  {parent_id} -> {node_id};")
            return node_id

        add_node(tree)
        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def _empty_result(status: str, message: str, tags=None) -> dict:
        return {
            "status": status,
            "message": message,
            "tags": tags or [],
            "trees": [],
            "tree_data": [],
            "graphs": [],
            "tree_count": 0,
        }

    @staticmethod
    def _first_child_label(node) -> str:
        """Метка первого дочернего узла, или пустая строка для листа."""
        if not isinstance(node, Tree) or len(node) == 0:
            return ""
        first = node[0]
        if isinstance(first, Tree):
            return str(first.label())
        return ""

    @classmethod
    def _tree_score(cls, tree) -> tuple:
        subtrees = list(tree.subtrees())
        labels = [str(node.label()) for node in subtrees]

        has_subject = any(
            str(node.label()) == "CLAUSE" and cls._first_child_label(node) == "NP"
            for node in subtrees
        )
        nominal_only = any(
            str(node.label()) == "CLAUSE"
            and len(node) == 1
            and cls._first_child_label(node) == "NP"
            for node in subtrees
        )

        return (
            0 if (has_subject or nominal_only) else 1,
            labels.count("PREDICATIVE"),
            len(labels),
        )

    def analyze_tokens(self, tokens) -> dict:
        words: List[_Word] = []
        source_tokens = []

        for token in tokens:
            if getattr(token, "is_punctuation", False):
                continue
            category = self._normalized_pos(token)
            words.append(_Word(str(getattr(token, "text", "")), category))
            source_tokens.append(token)

        if not words:
            return self._empty_result("not_parsed", "Нет слов для синтаксического разбора.")

        words, source_tokens = self._merge_compound_prepositions(words, source_tokens)

        normalized_text = [word.text.lower().replace("ё", "е") for word in words]
        normalized_lemmas = [
            str(getattr(token, "lemma", "") or "").lower().replace("ё", "е")
            for token in source_tokens
        ]

        if (normalized_text[0] in INTRODUCTORY_WORDS
                or normalized_lemmas[0] in INTRODUCTORY_WORDS):
            words[0] = _Word(words[0].text, "INTRO")

        greeting_forms = GREETING_WORDS
        if len(words) == 1 and (normalized_text[0] in greeting_forms
                                or normalized_lemmas[0] in greeting_forms):
            words[0] = _Word(words[0].text, "GREETING")
        elif len(words) >= 2:
            if (words[0].pos in {"NOUN", "PROPN", "PRON"}
                    and (normalized_text[1] in greeting_forms
                         or normalized_lemmas[1] in greeting_forms)):
                words[1] = _Word(words[1].text, "GREETING")
            elif ((normalized_text[0] in greeting_forms
                   or normalized_lemmas[0] in greeting_forms)
                    and words[1].pos in {"NOUN", "PROPN", "PRON"}):
                words[0] = _Word(words[0].text, "GREETING")

            if (normalized_text[0], normalized_text[1]) in GREETING_PHRASES:
                words[0] = _Word(words[0].text, "GREETING_ADJ")
            elif (len(words) >= 3
                    and (normalized_text[1], normalized_text[2]) in GREETING_PHRASES):
                words[1] = _Word(words[1].text, "GREETING_ADJ")

        adjusted = list(words)

        def is_name_or_nominative(index: int) -> bool:
            word = words[index]
            tag = str(getattr(source_tokens[index], "morph_tag", "")).upper()
            return word.pos == "PROPN" or "NAME" in tag or "NOMN" in tag

        def has_imperative(index: int) -> bool:
            return 0 <= index < len(source_tokens) and "IMPR" in str(
                getattr(source_tokens[index], "morph_tag", "")
            ).upper()

        for index, word in enumerate(words):
            if word.pos not in {"NOUN", "PROPN"}:
                continue
            if is_name_or_nominative(index) and (has_imperative(index - 1)
                                                 or has_imperative(index + 1)):
                adjusted[index] = _Word(word.text, "ADDR")

        if len(words) >= 2:
            if (words[0].pos in {"NOUN", "PROPN", "PRON"}
                    and words[1].pos == "GREETING" and is_name_or_nominative(0)):
                adjusted[0] = _Word(words[0].text, "ADDR")
            if (words[0].pos == "GREETING"
                    and words[1].pos in {"NOUN", "PROPN", "PRON"}
                    and is_name_or_nominative(1)):
                adjusted[1] = _Word(words[1].text, "ADDR")

            if len(words) >= 3:
                if (words[0].pos in {"NOUN", "PROPN", "PRON"}
                        and words[1].pos == "GREETING_ADJ"
                        and words[2].pos == "NOUN"
                        and is_name_or_nominative(0)):
                    adjusted[0] = _Word(words[0].text, "ADDR")
                if (words[0].pos == "GREETING_ADJ"
                        and words[1].pos == "NOUN"
                        and words[2].pos in {"NOUN", "PROPN", "PRON"}
                        and is_name_or_nominative(2)):
                    adjusted[2] = _Word(words[2].text, "ADDR")

        words = self._restore_subjects(adjusted, source_tokens)

        tags = [word.pos for word in words]
        if not tags:
            return self._empty_result("not_parsed", "Нет слов для синтаксического разбора.")

        if len(tags) > MAX_CFG_TOKENS:
            return self._empty_result(
                "too_long",
                f"Предложение содержит {len(tags)} слов. Учебная КС-грамматика "
                f"разбирает предложения до {MAX_CFG_TOKENS} слов: на более длинных "
                "число вариантов разбора растёт экспоненциально. Это ограничение "
                "алгоритма, а не ошибка в тексте.",
                tags,
            )

        try:
            candidates = list(islice(self.parser.parse(tags), self.max_trees * 4 + 4))
        except (ValueError, LookupError) as exc:
            text = str(exc)
            if "highly-ambiguous" in text or "MAX_PARSE_TREES" in text:
                return self._empty_result(
                    "too_ambiguous",
                    "Грамматика допускает слишком много вариантов разбора этого "
                    "предложения (комбинаторный взрыв). Это свойство КС-грамматик "
                    "с рекурсивными правилами, а не ошибка в тексте. Попробуйте "
                    "разобрать предложение по частям.",
                    tags,
                )
            return self._empty_result(
                "error", f"Не удалось выполнить CFG-разбор: {exc}", tags
            )

        if not candidates:
            return self._empty_result(
                "not_parsed",
                "Последовательность частей речи не соответствует ограниченной "
                "учебной КС-грамматике. Это не означает, что предложение "
                "пунктуационно или грамматически неверно.",
                tags,
            )

        more_trees = len(candidates) > self.max_trees
        candidates.sort(key=self._tree_score)
        raw_trees = candidates[:self.max_trees]

        rendered, tree_data, graphs = [], [], []
        for raw_tree in raw_trees:
            decorated = self._decorate_tree(raw_tree, words)
            rendered.append(decorated.pformat(margin=88))
            tree_data.append(self._tree_to_data(decorated))
            graphs.append(self.tree_to_graphviz(decorated))

        return {
            "status": "parsed",
            "message": "Синтаксическое дерево построено учебной КС-грамматикой.",
            "tags": tags,
            "trees": rendered,
            "tree_data": tree_data,
            "graphs": graphs,
            "tree_count": len(rendered),
            "more_trees_available": more_trees,
        }

    def analyze_sentence(self, sentence: str, tokens) -> dict:
        """Интерфейс для вызова из общего SyntaxAnalyzer."""
        return self.analyze_tokens(tokens)