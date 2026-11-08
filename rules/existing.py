"""Эвристические проверки причастных и деепричастных оборотов.

Правила рассчитаны на распространённые учебные примеры. Они используют
морфологические теги и позиции токенов, но не заменяют полноценный
синтаксический разбор русского предложения.
"""
from .base import Finding

TERMINAL_PUNCTUATION = {".", "!", "?", ";"}
PHRASE_PARTS = {"NOUN", "ADJ", "ADV", "PREP", "NUMR"}
PARTICIPLE_SUFFIXES = (
    "вший", "вшая", "вшее", "вшие", "ший", "шая", "шее", "шие",
    "ющий", "ющая", "ющее", "ющие", "ущий", "ущая", "ущее", "ущие",
    "ащий", "ащая", "яший", "ящая", "ящий", "емая", "емый", "имое",
    "имый", "имая", "нный", "нная", "нное", "нные", "тый", "тая", "тое", "тые",
)


def _is_full_participle(token):
    if token.pos == "PART" or "PART" in set(getattr(token, "possible_pos", ()) or ()):
        return True
    # Некоторые действительные причастия pymorphy3 может разбирать как ADJF.
    # В постпозиции после существительного учитываем характерные суффиксы.
    # Ограничение позиции снижает риск принять обычное прилагательное за причастие.
    word = token.text.lower().replace("ё", "е")
    return token.pos == "ADJ" and word.endswith(PARTICIPLE_SUFFIXES)


def _is_comma(token):
    return token.text == ","


def _is_terminal(token):
    return token.text in TERMINAL_PUNCTUATION


def _previous_word_index(tokens, index):
    """Индекс ближайшего слова слева, пропуская пунктуацию."""
    for pos in range(index - 1, -1, -1):
        if not tokens[pos].is_punctuation:
            return pos
    return None


def _scan_phrase_end(tokens, start_index, allow_one_noun=True):
    """Возвращает индекс первого токена после простой модели оборота.

    В зависимые слова включаем наречия, прилагательные, предлоги и
    ограниченное число существительных. Личное местоимение или глагол
    обычно сигнализируют о начале основной части предложения.
    """
    index = start_index + 1
    noun_count = 0
    while index < len(tokens):
        current = tokens[index]
        if current.is_punctuation or current.pos in {"VERB", "PRON"}:
            break
        if current.pos == "NOUN":
            noun_count += 1
            if allow_one_noun and noun_count > 1:
                break
            if not allow_one_noun:
                break
            index += 1
            continue
        if current.pos in PHRASE_PARTS or current.pos == "DEEPR":
            index += 1
            continue
        break
    return index


def _comma_before(tokens, index, previous_word_index):
    if previous_word_index is None:
        return False
    return any(_is_comma(tokens[k]) for k in range(previous_word_index + 1, index))


def _comma_after(tokens, boundary_index):
    return boundary_index < len(tokens) and _is_comma(tokens[boundary_index])


def _has_continuation(tokens, boundary_index):
    """Есть ли после оборота продолжение того же предложения."""
    if boundary_index >= len(tokens):
        return False
    return not _is_terminal(tokens[boundary_index])


def check_adverbial_participles(sentence, tokens):
    findings = []
    for i, token in enumerate(tokens):
        if token.pos != "DEEPR":
            continue

        boundary = _scan_phrase_end(tokens, i, allow_one_noun=True)
        phrase_end = tokens[boundary - 1].end if boundary > i + 1 else token.end
        previous_word = _previous_word_index(tokens, i)
        # Частицы «не» и «ни» перед деепричастием входят в начало оборота:
        # «Не заметив ошибки, редактор отправил текст».
        prefix_words = [t.text.lower() for t in tokens[:i] if not t.is_punctuation]
        effective_sentence_start = not prefix_words or all(w in {"не", "ни"} for w in prefix_words)
        if effective_sentence_start:
            previous_word = None
        has_left_comma = _comma_before(tokens, i, previous_word)
        has_right_comma = _comma_after(tokens, boundary)

        # В начале предложения оборот открывается без запятой,
        # но обязательно закрывается перед продолжением предложения.
        if previous_word is None:
            if not has_right_comma:
                findings.append(Finding(
                    "Деепричастный оборот",
                    "Деепричастный оборот в начале предложения обычно отделяется запятой после себя.",
                    token.start, phrase_end,
                    "Поставьте запятую после деепричастного оборота."
                ))
        else:
            if not has_left_comma:
                findings.append(Finding(
                    "Деепричастный оборот",
                    "Деепричастный оборот обычно обособляется запятой.",
                    token.start, phrase_end,
                    "Поставьте запятую перед деепричастным оборотом."
                ))
            if _has_continuation(tokens, boundary) and not has_right_comma:
                findings.append(Finding(
                    "Деепричастный оборот",
                    "После деепричастного оборота перед продолжением предложения нужна закрывающая запятая.",
                    token.start, phrase_end,
                    "Поставьте запятую после деепричастного оборота."
                ))
    return findings


def check_participial_phrases(sentence, tokens):
    findings = []
    for i, token in enumerate(tokens):
        possible_pos = set(getattr(token, "possible_pos", ()) or ())
        if not _is_full_participle(token):
            # PART_SHORT (краткие причастия) не обособляются как определения.
            continue

        previous_word = _previous_word_index(tokens, i)
        # В этой версии проверяем только постпозитивный оборот:
        # перед причастием должно находиться определяемое существительное.
        if previous_word is None or tokens[previous_word].pos != "NOUN":
            continue

        if not _comma_before(tokens, i, previous_word):
            findings.append(Finding(
                "Причастный оборот",
                "Причастный оборот после определяемого слова обычно обособляется запятой.",
                token.start, token.end,
                "Поставьте запятую перед причастным оборотом."
            ))

        boundary = _scan_phrase_end(tokens, i, allow_one_noun=True)
        phrase_end = tokens[boundary - 1].end if boundary > i + 1 else token.end
        if _has_continuation(tokens, boundary) and not _comma_after(tokens, boundary):
            findings.append(Finding(
                "Причастный оборот",
                "После причастного оборота перед продолжением предложения нужна закрывающая запятая.",
                token.start, phrase_end,
                "Поставьте запятую после причастного оборота."
            ))

    return findings
