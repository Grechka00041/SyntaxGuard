"""Расширенная учебная контекстно-свободная грамматика SyntaxGuard CFG v2.

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
except ImportError:  # pragma: no cover - зависит от окружения пользователя
    CFG = ChartParser = Tree = None


GRAMMAR_TEXT = r"""
# Базовые типы предложений
S -> CLAUSE
S -> CLAUSE CONJ CLAUSE
S -> CLAUSE CONJ CLAUSE CONJ CLAUSE
S -> ADDR CLAUSE
S -> ADDR GREETING
S -> GREETING ADDR
S -> GREETING
S -> GREETING_PHRASE
S -> ADDR GREETING_PHRASE
S -> GREETING_PHRASE ADDR
S -> ADDR

# Предикативная часть: подлежащее и сказуемое либо самостоятельная VP
CLAUSE -> NP VP
CLAUSE -> VP
CLAUSE -> DEEPR NP CLAUSE
CLAUSE -> PARTICLE CLAUSE
CLAUSE -> INTJ CLAUSE
CLAUSE -> ADV CLAUSE
CLAUSE -> VP ADDR
CLAUSE -> VP ADDR NP
CLAUSE -> NP VP ADV
CLAUSE -> NP SHORT_ADJ
CLAUSE -> NP SHORT_PART
CLAUSE -> NP PRED

# Именные группы и определения
NP -> NOUN
NP -> PROPN
NP -> PRON
NP -> NUMR
# Предпочитаем цельную однородную группу, если она содержит перечисление.
NP -> HOMOG_NP NOUN
NP -> HOMOG_NP
NP -> ADJ NP
NP -> NUMR NP
NP -> NP PP
NP -> NP CONJ NP
NP -> NP CONJ NP CONJ NP
NP -> NOUN PART
NP -> NOUN PART NP
NP -> NOUN PART PP
NP -> NOUN SHORT_PART
NP -> PARTICLE NP

# Типовые однородные перечисления. Запятые не входят в CFG-вход:
# их наличие/отсутствие проверяют отдельные пунктуационные правила.
HOMOG_NP -> NOUN CONJ NOUN
HOMOG_NP -> NOUN NOUN CONJ NOUN
HOMOG_NP -> NOUN CONJ NOUN CONJ NOUN
HOMOG_NP -> ADJ CONJ ADJ
HOMOG_NP -> ADJ ADJ CONJ ADJ
HOMOG_NP -> ADJ CONJ ADJ CONJ ADJ

# Глагольные группы, включая конструкции «глагол + инфинитив»
VP -> VERB
VP -> VERB NP
VP -> VERB PP
VP -> VERB ADV
VP -> VERB ADJ
VP -> VERB SHORT_ADJ
VP -> VERB SHORT_PART
VP -> VERB NP PP
VP -> VERB INFN
VP -> VERB INFN NP
VP -> VERB INFN PP
VP -> INFN
VP -> ADV VP
VP -> DEEPR VP
VP -> VP DEEPR
VP -> VP CONJ VP
VP -> VP CONJ VP CONJ VP
VP -> VP ADV
VP -> PRED
VP -> PRED NP
VP -> ADJ
VP -> SHORT_ADJ
VP -> SHORT_PART
VP -> ADV
VP -> PARTICLE VP

# Приветственные формулы и обращения
GREETING_PHRASE -> GREETING_ADJ NOUN

# Предложные группы
PP -> PREP NP

# Терминалы, получаемые после морфологической нормализации
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
ADDR -> 'ADDR'
GREETING -> 'GREETING'
"""


# Слова, которые в типичных формулах общения выступают приветствием.
# Это узкий лексический список для учебной CFG, а не пунктуационное правило.
GREETING_WORDS = {"привет", "здравствуйте", "здравствуй", "салют"}
GREETING_PHRASES = {
    ("доброе", "утро"),
    ("добрый", "день"),
    ("добрый", "вечер"),
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
    def _normalized_pos(token) -> str | None:
        """Преобразовать POS pymorphy3 в терминал грамматики."""
        pos = getattr(token, "pos", "UNKN")
        morph_tag = str(getattr(token, "morph_tag", "") or "").upper()
        possible_pos = set(getattr(token, "possible_pos", ()) or ())
        # INFN в основном препроцессоре для совместимости с пунктуационными
        # эвристиками хранится как VERB. Для CFG восстанавливаем более точную
        # категорию из морфологического тега pymorphy3.
        morph_head = morph_tag.split(",", 1)[0].strip()
        if morph_head == "INFN":
            return "INFN"

        # Сохраняем специальный разбор причастия, если pymorphy3 обнаружил его
        # среди достаточно вероятных альтернатив к прилагательному.
        if pos == "ADJ" and "PART" in possible_pos:
            return "PART"
        if pos == "PART_SHORT":
            return "SHORT_PART"
        if pos == "ADJ" and "ADJS" in morph_tag:
            return "SHORT_ADJ"
        if pos == "NOUN" and "NAME" in morph_tag:
            return "PROPN"
        if pos in {
            "NOUN", "PROPN", "PRON", "VERB", "ADJ", "PART", "DEEPR",
            "ADV", "PREP", "CONJ", "NUMR", "PRED", "PARTICLE", "INTJ",
        }:
            return pos
        return None

    @staticmethod
    def _decorate_tree(tree, words: Iterable[_Word]):
        """Заменить листья-категории на исходные слова, сохранив узлы дерева."""
        iterator = iter(words)

        def visit(node):
            if isinstance(node, Tree):
                # Лексический узел: например, NOUN -> 'NOUN'.
                if len(node) == 1 and isinstance(node[0], str):
                    word = next(iterator)
                    return Tree(node.label(), [word.text])
                return Tree(node.label(), [visit(child) for child in node])
            return node

        return visit(tree)

    @staticmethod
    def _tree_to_data(tree):
        """Преобразовать NLTK Tree в простой формат для HTML/SVG-визуализации."""
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
        """Экранировать подпись узла для Graphviz DOT."""
        return (str(value).replace("\\", "\\\\")
                .replace('"', '\\"').replace("\n", "\\n"))

    @classmethod
    def tree_to_graphviz(cls, tree) -> str:
        """Преобразовать дерево NLTK в DOT для графического отображения в Streamlit."""
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

    def analyze_tokens(self, tokens) -> dict:
        """Вернуть статус CFG-разбора, POS-последовательность и деревья.

        Знаки препинания исключаются из входа грамматики: здесь разбирается
        синтаксическая структура, а пунктуационные правила работают независимо
        с исходной строкой и позициями токенов.
        """
        words: List[_Word] = []
        source_tokens = []
        for token in tokens:
            if getattr(token, "is_punctuation", False):
                continue
            category = self._normalized_pos(token)
            if category is None:
                return {
                    "status": "not_parsed",
                    "message": f"Грамматика не поддерживает категорию слова «{getattr(token, 'text', '')}». Это не означает пунктуационную ошибку.",
                    "tags": [word.pos for word in words] + ["UNSUPPORTED"],
                    "trees": [],
                    "tree_data": [],
                    "graphs": [],
                    "tree_count": 0,
                }
            words.append(_Word(str(getattr(token, "text", "")), category))
            source_tokens.append(token)

        # Приветствия распознаём только в характерных позициях, чтобы не
        # переопределять обычное существительное «привет» в «передай привет».
        normalized_text = [word.text.lower().replace("ё", "е") for word in words]
        normalized_lemmas = [
            str(getattr(token, "lemma", "") or "").lower().replace("ё", "е")
            for token in source_tokens
        ]
        greeting_forms = GREETING_WORDS
        if len(words) == 1 and (normalized_text[0] in greeting_forms or normalized_lemmas[0] in greeting_forms):
            words[0] = _Word(words[0].text, "GREETING")
        elif len(words) >= 2:
            # «Дима, привет» / «Привет, Дима» / «Здравствуйте, коллеги».
            if (words[0].pos in {"NOUN", "PROPN", "PRON"}
                    and (normalized_text[1] in greeting_forms or normalized_lemmas[1] in greeting_forms)):
                words[1] = _Word(words[1].text, "GREETING")
            elif ((normalized_text[0] in greeting_forms or normalized_lemmas[0] in greeting_forms)
                    and words[1].pos in {"NOUN", "PROPN", "PRON"}):
                words[0] = _Word(words[0].text, "GREETING")

            # Узкий набор устойчивых формул: «доброе утро», «добрый день/вечер».
            if len(words) >= 2 and (normalized_text[0], normalized_text[1]) in GREETING_PHRASES:
                words[0] = _Word(words[0].text, "GREETING_ADJ")
            elif len(words) >= 3 and (normalized_text[1], normalized_text[2]) in GREETING_PHRASES:
                words[1] = _Word(words[1].text, "GREETING_ADJ")

        # Обращение — отдельная категория CFG. Не смешиваем его с дополнением:
        # «Маша, закрой окно» -> ADDR VERB NOUN, но «закрой окно» -> VERB NOUN.
        adjusted = list(words)

        def is_name_or_nominative(index: int) -> bool:
            word = words[index]
            tag = str(getattr(source_tokens[index], "morph_tag", "")).upper()
            return (word.pos == "PROPN" or "NAME" in tag or "NOMN" in tag)

        def has_imperative(index: int) -> bool:
            return 0 <= index < len(source_tokens) and "IMPR" in str(
                getattr(source_tokens[index], "morph_tag", "")
            ).upper()

        for index, word in enumerate(words):
            if word.pos not in {"NOUN", "PROPN", "PRON"}:
                continue
            previous_is_imperative = has_imperative(index - 1)
            next_is_imperative = has_imperative(index + 1)
            if is_name_or_nominative(index) and (previous_is_imperative or next_is_imperative):
                adjusted[index] = _Word(word.text, "ADDR")

        # Формулы приветствия: «Дима, привет», «Привет, Дима»,
        # «Дима, доброе утро». В CFG обращение маркируется отдельно.
        if len(words) >= 2:
            if words[0].pos in {"NOUN", "PROPN", "PRON"} and words[1].pos == "GREETING":
                if is_name_or_nominative(0):
                    adjusted[0] = _Word(words[0].text, "ADDR")
            if words[0].pos == "GREETING" and words[1].pos in {"NOUN", "PROPN", "PRON"}:
                if is_name_or_nominative(1):
                    adjusted[1] = _Word(words[1].text, "ADDR")

            # «Дима, доброе утро» / «Доброе утро, Дима».
            if len(words) >= 3:
                if (words[0].pos in {"NOUN", "PROPN", "PRON"}
                        and words[1].pos == "GREETING_ADJ" and words[2].pos == "NOUN"
                        and is_name_or_nominative(0)):
                    adjusted[0] = _Word(words[0].text, "ADDR")
                if (words[0].pos == "GREETING_ADJ" and words[1].pos == "NOUN"
                        and words[2].pos in {"NOUN", "PROPN", "PRON"}
                        and is_name_or_nominative(2)):
                    adjusted[2] = _Word(words[2].text, "ADDR")

        words = adjusted

        tags = [word.pos for word in words]
        if not tags:
            return {
                "status": "not_parsed", "message": "Нет слов для синтаксического разбора.",
                "tags": [], "trees": [], "tree_data": [], "graphs": [], "tree_count": 0,
            }

        try:
            raw_trees = list(islice(self.parser.parse(tags), self.max_trees + 1))
        except (ValueError, LookupError) as exc:
            return {
                "status": "error", "message": f"Не удалось выполнить CFG-разбор: {exc}",
                "tags": tags, "trees": [], "tree_data": [], "graphs": [], "tree_count": 0,
            }

        if not raw_trees:
            return {
                "status": "not_parsed",
                "message": (
                    "Последовательность частей речи не соответствует ограниченной "
                    "учебной КС-грамматике. Это не означает, что предложение "
                    "пунктуационно или грамматически неверно."
                ),
                "tags": tags,
                "trees": [],
                "tree_data": [],
                "graphs": [],
                "tree_count": 0,
            }

        more_trees = len(raw_trees) > self.max_trees
        raw_trees = raw_trees[:self.max_trees]
        rendered = []
        tree_data = []
        graphs = []
        for raw_tree in raw_trees:
            decorated = self._decorate_tree(raw_tree, words)
            rendered.append(decorated.pformat(margin=88))
            tree_data.append(self._tree_to_data(decorated))
            # DOT оставляем как дополнительное машиночитаемое представление;
            # интерфейс использует безопасный SVG-рендерер без Graphviz.
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
        """Удобный интерфейс для вызова из общего SyntaxAnalyzer."""
        return self.analyze_tokens(tokens)
