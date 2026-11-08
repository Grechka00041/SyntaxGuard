"""Консервативная эвристическая проверка вводных слов и сочетаний.

Правило проверяет только ограниченный словарь типичных вводных единиц.
Омонимичные случаи (например, «однако», «значит», «кажется», «наконец»)
пока намеренно не включены: без синтаксического разбора они часто дают
ложные срабатывания.
"""
from .base import Finding

# Ключи — точные последовательности токенов в нижнем регистре.
# Сначала обрабатываются более длинные сочетания.
INTRODUCTORY_PHRASES = sorted(
    [
        ("к", "сожалению"),
        ("к", "счастью"),
        ("к", "удивлению"),
        ("к", "несчастью"),
        ("по", "всей", "вероятности"),
        ("по-видимому",),
        ("во-первых",),
        ("во-вторых",),
        ("в-третьих",),
        ("конечно",),
        ("безусловно",),
        ("несомненно",),
        ("вероятно",),
        ("пожалуй",),
        ("например",),
        ("итак",),
        ("следовательно",),
        ("кстати",),
        ("впрочем",),
    ],
    key=len,
    reverse=True,
)

TERMINAL = {".", "!", "?", ";"}


def _is_punctuation(token):
    return getattr(token, "is_punctuation", token.text in ",.!?;:—–()-")


def _word_before(tokens, index):
    for i in range(index - 1, -1, -1):
        if not _is_punctuation(tokens[i]):
            return i
    return None


def _match_at(tokens, start, phrase):
    end = start + len(phrase)
    if end > len(tokens):
        return False
    for offset, expected in enumerate(phrase):
        token = tokens[start + offset]
        if _is_punctuation(token) or token.text.lower() != expected:
            return False
    return True


def _has_separator(tokens, start, end):
    """Есть ли уже знак препинания между соседними частями предложения."""
    return any(_is_punctuation(tokens[i]) for i in range(start, min(end, len(tokens))))


def check_introductory_words(sentence, tokens):
    findings = []
    i = 0
    while i < len(tokens):
        if _is_punctuation(tokens[i]):
            i += 1
            continue

        matched = None
        for phrase in INTRODUCTORY_PHRASES:
            if _match_at(tokens, i, phrase):
                matched = phrase
                break
        if matched is None:
            i += 1
            continue

        end = i + len(matched)  # индекс первого токена после вводной единицы
        phrase_start = tokens[i].start
        phrase_end = tokens[end - 1].end
        previous_word = _word_before(tokens, i)
        starts_sentence = previous_word is None

        # Запятая перед вводным словом/сочетанием нужна, если перед ним
        # есть продолжение предложения и нет уже стоящего разделителя.
        if not starts_sentence and not _has_separator(tokens, previous_word + 1, i):
            findings.append(Finding(
                "Вводное слово",
                "Вводное слово или сочетание в середине предложения обычно выделяется запятой слева.",
                phrase_start, phrase_end,
                "Поставьте запятую перед вводным словом или сочетанием."
            ))

        # После вводного слова нужна запятая, если далее продолжается
        # предложение и непосредственно после сочетания нет знака.
        has_following_word = any(
            not _is_punctuation(tokens[k])
            for k in range(end, len(tokens))
        )
        if has_following_word and not _has_separator(tokens, end, end + 1):
            findings.append(Finding(
                "Вводное слово",
                "Вводное слово или сочетание обычно отделяется запятой от последующей части предложения.",
                phrase_start, phrase_end,
                "Поставьте запятую после вводного слова или сочетания."
            ))

        i = end
    return findings
