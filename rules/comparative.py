"""Осторожная эвристическая проверка сравнительных оборотов с «как».

Проверяются типовые учебные конструкции: «Он упрям как осёл» и
«Он, как и брат, любит чтение». Обороты со значением роли/качества
(«работает как учитель») и составные союзы «как будто» не проверяются.
Это не полный синтаксический анализ.
"""
from .base import Finding

ROLE_PREDICATES = {
    "работать", "служить", "использовать", "применять", "выступать",
    "действовать", "называть", "считать", "рассматривать", "назначить",
}
NON_COMPARATIVE_FOLLOWERS = {"будто", "словно"}
NOMINAL_POS = {"NOUN", "PRON", "NUMR"}
PHRASE_POS = {"ADJ", "ADV", "NOUN", "PRON", "NUMR"}


def _is_punct(token):
    return getattr(token, "is_punctuation", token.text in ",.!?;:—–()-")


def _previous_word(tokens, index):
    for i in range(index - 1, -1, -1):
        if not _is_punct(tokens[i]):
            return i
    return None


def _scan_comparison(tokens, start):
    """Находит конец короткой именной части сравнения после «как».

    Возвращает индекс первого токена после оборота. Не пытается разбирать
    распространённые конструкции с придаточными предложениями.
    """
    i = start + 1
    if i < len(tokens) and tokens[i].text.lower() == "и":
        i += 1
    while i < len(tokens) and tokens[i].pos in {"ADJ", "ADV"}:
        i += 1
    if i < len(tokens) and tokens[i].pos in NOMINAL_POS:
        i += 1
        return i
    return None


def check_comparative_phrases(sentence, tokens):
    findings = []
    for i, token in enumerate(tokens):
        if _is_punct(token) or token.text.lower() != "как":
            continue
        if i + 1 >= len(tokens) or tokens[i + 1].text.lower() in NON_COMPARATIVE_FOLLOWERS:
            continue

        end = _scan_comparison(tokens, i)
        if end is None:
            continue
        previous = _previous_word(tokens, i)
        at_sentence_start = previous is None
        next_word_exists = any(not _is_punct(t) for t in tokens[end:])
        has_comma_before = i > 0 and tokens[i - 1].text == ","
        has_comma_after = end < len(tokens) and tokens[end].text == ","

        # «Как и брат, ...» — вводящая сравнительная конструкция в начале.
        starts_with_as = at_sentence_start and tokens[i + 1].text.lower() == "и"
        if at_sentence_start and not starts_with_as:
            continue

        # Сочетание в значении «в качестве» не является сравнительным оборотом.
        if previous is not None:
            prev_token = tokens[previous]
            prev_lemma = (getattr(prev_token, "lemma", "") or prev_token.text).lower()
            if prev_lemma in ROLE_PREDICATES:
                continue

        if at_sentence_start:
            if next_word_exists and not has_comma_after:
                phrase_start = token.start
                phrase_end = tokens[end - 1].end
                findings.append(Finding(
                    "Сравнительный оборот",
                    "Конструкция «как и ...» в начале предложения обычно отделяется запятой от последующей части.",
                    phrase_start, phrase_end,
                    "Поставьте запятую после сравнительного оборота."
                ))
            continue

        # Для одиночного сравнения в конце предложения требуется запятая
        # перед «как»: «Он упрям, как осёл».
        if not has_comma_before:
            findings.append(Finding(
                "Сравнительный оборот",
                "Сравнительный оборот с «как» в данном типовом контексте отделяется запятой.",
                token.start, tokens[end - 1].end,
                "Поставьте запятую перед сравнительным оборотом."
            ))

        # Вставные сравнения в середине предложения могут требовать
        # закрывающую запятую: «Он, как и брат, любит чтение»;
        # «Она, как мать, заботилась о сыне».
        next_word_index = next((k for k in range(end, len(tokens)) if not _is_punct(tokens[k])), None)
        is_inserted = tokens[i + 1].text.lower() == "и"
        is_parenthetical = (
            previous is not None
            and tokens[previous].pos in {"NOUN", "PRON"}
            and next_word_index is not None
            and tokens[next_word_index].pos in {"VERB", "PRED"}
        )
        if (is_inserted or is_parenthetical) and next_word_exists and not has_comma_after:
            findings.append(Finding(
                "Сравнительный оборот",
                "Вставная конструкция «как и ...» выделяется запятыми с двух сторон.",
                token.start, tokens[end - 1].end,
                "Поставьте запятую после сравнительного оборота."
            ))

    return findings
