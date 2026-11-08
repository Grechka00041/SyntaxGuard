"""Эвристическая проверка запятых в перечислениях однородных членов.

Первая версия правила намеренно ограничена перечислениями существительных
и прилагательных перед одиночным сочинительным союзом «и», «или» или «либо».
Например: «Купил хлеб молоко и сыр» -> «Купил хлеб, молоко и сыр».
Правило не пытается автоматически распознавать все виды однородных членов.
"""
from .base import Finding

ITEM_POS = {"NOUN", "ADJ"}
COORDINATING_CONJUNCTIONS = {"и", "или", "либо"}


def _is_punctuation(token):
    return getattr(token, "is_punctuation", token.text in ",.!?;:—–()-")


def check_homogeneous_members(sentence, tokens):
    findings = []

    for conjunction_index, conjunction in enumerate(tokens):
        if _is_punctuation(conjunction):
            continue
        if conjunction.text.lower() not in COORDINATING_CONJUNCTIONS:
            continue

        # Союз должен соединять два однородных элемента одного типа.
        if conjunction_index == 0 or conjunction_index + 1 >= len(tokens):
            continue
        previous_index = conjunction_index - 1
        next_index = conjunction_index + 1
        previous = tokens[previous_index]
        following = tokens[next_index]

        if (previous.pos not in ITEM_POS or following.pos != previous.pos
                or _is_punctuation(previous) or _is_punctuation(following)):
            continue

        item_pos = previous.pos

        # Собираем цепочку однородных элементов слева от союза.
        # Запятые разрешены: они означают, что соответствующая граница уже оформлена.
        item_indices = [previous_index]
        cursor = previous_index - 1
        while cursor >= 0:
            current = tokens[cursor]
            if current.pos == item_pos and not _is_punctuation(current):
                item_indices.append(cursor)
                cursor -= 1
                continue
            if current.text == ",":
                cursor -= 1
                continue
            break

        item_indices.reverse()
        if len(item_indices) < 2:
            # Обычное сочетание двух однородных членов с одиночным «и»:
            # «хлеб и молоко» — запятая не нужна.
            continue

        # Проверяем каждую границу между элементами перечисления.
        for left_index, right_index in zip(item_indices, item_indices[1:]):
            left = tokens[left_index]
            right = tokens[right_index]
            has_comma = any(tokens[k].text == ","
                            for k in range(left_index + 1, right_index))
            if not has_comma:
                findings.append(Finding(
                    "Однородные члены предложения",
                    "В перечислении однородных членов перед одиночным союзом «и», «или» или «либо» между предыдущими элементами обычно ставится запятая.",
                    left.end, right.start,
                    f"Поставьте запятую после слова «{left.text}».",
                ))

    # Удаляем возможные дубли, сохраняя порядок обнаружения.
    unique = {}
    for finding in findings:
        key = (finding.start, finding.end, finding.message)
        unique[key] = finding
    return list(unique.values())
