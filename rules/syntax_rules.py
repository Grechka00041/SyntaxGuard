"""Замечания по синтаксической структуре на основе дерева КС-разбора.

Правила работают с tree_data из syntax_parser.SyntaxParser.

Важно:
- CFG-дерево — это один возможный вариант разбора.
- Поэтому замечания формулируются мягко: "в выбранном разборе",
  "может быть особенностью структуры", а не как абсолютная ошибка.
- Не выводим мусорные неоднозначности вроде:
  «критическую ошибку» / «ошибку»,
  «автоматически отправляет» / «отправляет».
"""
from .base import Finding

SEVERITY_NOTE = "note"

SUBJECT_LABELS = {"NOUN", "PROPN", "PRON", "NUMR"}
PREDICATE_LABELS = {"VERB", "INFN", "PRED", "SHORT_ADJ", "SHORT_PART"}


# -----------------------------
# Служебные функции обхода дерева
# -----------------------------

def _walk(node):
    """Обход дерева в глубину."""
    stack = [(node, 0)]
    while stack:
        current, depth = stack.pop()
        yield current, depth
        for child in reversed(current.get("children", [])):
            stack.append((child, depth + 1))


def _is_leaf(node):
    return node.get("word") is not None


def _leaves(node):
    for current, _ in _walk(node):
        if _is_leaf(current):
            yield current


def _words_of(node):
    return tuple(leaf["word"] for leaf in _leaves(node))


def _labels_of(node):
    return {leaf.get("label") for leaf in _leaves(node)}


def _word_tokens(tokens):
    return [t for t in tokens if not getattr(t, "is_punctuation", False)]


def _span_from_indices(indices, words):
    indices = list(indices)
    if not indices or not words:
        return None

    first, last = min(indices), max(indices)
    if first < 0 or last >= len(words):
        return None

    return words[first].start, words[last].end


def _fallback_span(words):
    if not words:
        return 0, 0
    return words[0].start, words[-1].end


def _node_count(node):
    return sum(1 for _ in _leaves(node))


def _iter_nodes_with_spans(tree_data, words):
    """
    Итератор по узлам с корректными диапазонами.

    Диапазон считается по порядку листьев, а не поиском текста.
    Это важно для повторяющихся слов и составных предлогов.
    """
    def visit(node, offset):
        count = _node_count(node)
        span = _span_from_indices(range(offset, offset + count), words)
        yield node, span, offset, count

        cursor = offset
        for child in node.get("children", []):
            yield from visit(child, cursor)
            cursor += _node_count(child)

    yield from visit(tree_data, 0)


def _parent_map(tree_data):
    """Карта id(child) -> parent."""
    parents = {}

    def visit(node):
        for child in node.get("children", []):
            parents[id(child)] = node
            visit(child)

    visit(tree_data)
    return parents


def _nearest_parent_with_label(node, parents, labels):
    current = node
    while id(current) in parents:
        parent = parents[id(current)]
        if parent.get("label") in labels:
            return parent
        current = parent
    return None


def _dedup(findings):
    unique = {}
    for finding in findings:
        key = (
            finding.rule,
            finding.message,
            finding.start,
            finding.end,
            finding.suggestion,
            finding.severity,
        )
        unique[key] = finding
    return list(unique.values())


# -----------------------------
# 1. Назывное предложение / нет сказуемого
# -----------------------------

def check_nominal_sentence(sentence, tokens, tree_data):
    """
    Предложение состоит только из именной группы.

    Пример:
    «Тихая зимняя ночь.»
    «Старый дом у реки.»
    «Мой любимый город.»

    Это не ошибка, но полезное синтаксическое наблюдение:
    сказуемое не выражено, предложение может быть назывным.
    """
    words = _word_tokens(tokens)
    findings = []

    for node, span, _, _ in _iter_nodes_with_spans(tree_data, words):
        if node.get("label") != "CLAUSE":
            continue

        children = node.get("children", [])
        labels = _labels_of(node)

        only_np = len(children) == 1 and children[0].get("label") == "NP"
        has_predicate = bool(labels & PREDICATE_LABELS)

        if only_np and not has_predicate and span:
            findings.append(Finding(
                "Назывное предложение",
                "В предложении выражена именная группа, но нет сказуемого. "
                "Такая конструкция может быть назывным предложением: она называет "
                "предмет, состояние или обстановку.",
                span[0], span[1],
                "Это не ошибка. Если по смыслу требуется действие или признак, "
                "проверьте, не пропущено ли сказуемое.",
                severity=SEVERITY_NOTE,
            ))

    return findings


# -----------------------------
# 2. Нераспознанные слова
# -----------------------------

def check_unknown_words(sentence, tokens, tree_data):
    """
    Листья UNKN: морфология не распознала слово.

    Важно: pymorphy3 может угадывать неизвестные слова по форме,
    поэтому не каждое выдуманное слово обязательно попадёт сюда.
    """
    words = _word_tokens(tokens)
    findings = []

    for index, leaf in enumerate(_leaves(tree_data)):
        if index >= len(words):
            break

        if leaf.get("label") != "UNKN":
            continue

        token = words[index]
        findings.append(Finding(
            "Нераспознанное слово",
            f"Слово «{token.text}» не получило надёжного морфологического разбора. "
            "Грамматика трактует его как неопределённую категорию, поэтому "
            "структура предложения разобрана приближённо.",
            token.start, token.end,
            "Проверьте написание слова или добавьте его в словарь анализатора.",
            severity=SEVERITY_NOTE,
        ))

    return findings


# -----------------------------
# 3. Прилагательное + причастие перед существительным
# -----------------------------

def check_mixed_attributes(sentence, tokens, tree_data):
    """
    Сочетание прилагательного и причастия перед существительным.

    Примеры:
    «новый построенный дом»
    «опытный работающий инженер»
    «тяжёлый загруженный файл»

    Это не ошибка, но полезное наблюдение:
    такие определения часто неоднородны.
    """
    words = _word_tokens(tokens)
    findings = []

    for node, span, _, _ in _iter_nodes_with_spans(tree_data, words):
        if node.get("label") != "ATTRS":
            continue

        labels = [leaf.get("label") for leaf in _leaves(node)]

        if "ADJ" in labels and "PART" in labels and span:
            findings.append(Finding(
                "Сочетание определений",
                "Перед существительным сочетаются прилагательное и причастие. "
                "Такие определения часто являются неоднородными: одно называет "
                "признак предмета, другое — признак по действию или состоянию.",
                span[0], span[1],
                "Проверьте смысл: если определения неоднородны, запятая между ними не нужна.",
                severity=SEVERITY_NOTE,
            ))

    return findings


# -----------------------------
# 4. Сложная цепочка зависимых существительных
# -----------------------------

def check_complex_np_chain(sentence, tokens, tree_data):
    """
    Скопление зависимых существительных.

    Считаем существительные во всей именной группе, а не только в NP_CHAIN:
    «структуру отдела обработки данных компании» грамматика может собрать
    через NP -> NP NP_CHAIN, и тогда одного узла NP_CHAIN не хватит.
    """
    words = _word_tokens(tokens)
    findings = []
    reported = set()

    for node, span, _, _ in _iter_nodes_with_spans(tree_data, words):
        if node.get("label") != "NP":
            continue

        leaves = list(_leaves(node))
        noun_count = sum(1 for leaf in leaves if leaf.get("label") in {"NOUN", "PROPN"})

        if noun_count < 4 or not span:
            continue
        if span in reported:
            continue

        inner_same = False
        for child in node.get("children", []):
            if child.get("label") != "NP":
                continue
            inner_nouns = sum(
                1 for leaf in _leaves(child) if leaf.get("label") in {"NOUN", "PROPN"}
            )
            if inner_nouns == noun_count:
                inner_same = True
                break
        if inner_same:
            continue

        reported.add(span)
        findings.append(Finding(
            "Сложная именная конструкция",
            f"В именной группе подряд идут {noun_count} существительных. "
            "Такие конструкции трудно читать: приходится удерживать несколько "
            "связей между словами одновременно.",
            span[0], span[1],
            "Если текст рассчитан на широкую аудиторию, замените часть цепочки "
            "предложной группой или отдельным предложением.",
            severity=SEVERITY_NOTE,
        ))

    return findings


# -----------------------------
# 5. Неоднозначность прикрепления PP
# -----------------------------

def _collect_pp_attachments(tree_data, words):
    """
    Собирает предложные группы и их ближайшие значимые родители.

    Возвращает:
    {
        ("с", "телескопом"): {
            "parents": {"NP", "VP"},
            "span": (...)
        }
    }
    """
    parents = _parent_map(tree_data)
    result = {}

    for node, span, _, _ in _iter_nodes_with_spans(tree_data, words):
        if node.get("label") != "PP":
            continue

        key = _words_of(node)
        if not key or not span:
            continue

        parent = _nearest_parent_with_label(node, parents, {"NP", "VP", "CLAUSE"})
        parent_label = parent.get("label") if parent else None

        if parent_label not in {"NP", "VP", "CLAUSE"}:
            continue

        item = result.setdefault(key, {"parents": set(), "span": span})
        item["parents"].add(parent_label)

    return result


def check_attachment_ambiguity(sentence, tokens, trees_data):
    """
    Показываем только содержательную неоднозначность прикрепления PP.
    """
    if not trees_data or len(trees_data) < 2:
        return []

    words = _word_tokens(tokens)
    attachments = [_collect_pp_attachments(tree, words) for tree in trees_data]

    all_keys = set()
    for item in attachments:
        all_keys.update(item.keys())

    for key in all_keys:
        parent_sets = []
        span = None

        for item in attachments:
            if key in item:
                parent_sets.append(item[key]["parents"])
                span = item[key]["span"]

        if len(parent_sets) < 2 or span is None:
            continue

        normalized = []
        for labels in parent_sets:
            current = set(labels)
            if "CLAUSE" in current:
                current.add("VP")
            normalized.append(current)

        has_np_attachment = any("NP" in labels for labels in normalized)
        has_vp_attachment = any("VP" in labels for labels in normalized)

        if not (has_np_attachment and has_vp_attachment):
            continue

        pp_text = sentence[span[0]:span[1]].strip()

        return [Finding(
            "Неоднозначность прикрепления",
            f"Предложная группа «{pp_text}» может относиться либо к имени, "
            "либо к действию. Это содержательная структурная неоднозначность: "
            "разные деревья дают разные связи между словами.",
            span[0], span[1],
            "Оба варианта возможны грамматически. Правильный смысл определяется контекстом.",
            severity=SEVERITY_NOTE,
        )]

    return []


# -----------------------------
# Точка входа
# -----------------------------

TREE_RULES = [
    check_nominal_sentence,
    check_unknown_words,
    check_mixed_attributes,
    check_complex_np_chain,
]


def check_syntax(sentence, tokens, syntax_result):
    """Замечания по структуре предложения."""
    syntax_result = syntax_result or {}

    if syntax_result.get("status") != "parsed":
        return []

    trees_data = syntax_result.get("tree_data") or []
    if not trees_data:
        return []

    findings = []

    for rule in TREE_RULES:
        findings.extend(rule(sentence, tokens, trees_data[0]))

    findings.extend(check_attachment_ambiguity(sentence, tokens, trees_data))

    return _dedup(findings)