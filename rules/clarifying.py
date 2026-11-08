"""Эвристическая проверка уточняющих обстоятельств места и времени.

Ограниченная модель: маркер места/времени + конкретизирующая предложная
группа («там, у реки, ...», «вечером, около семи»). Не претендует на
распознавание всех видов уточнений.
"""
from .base import Finding

PLACE_MARKERS = {
    "там", "здесь", "слева", "справа", "внизу", "вверху", "вдали",
    "впереди", "позади", "недалеко", "поблизости", "рядом",
}
TIME_MARKERS = {
    "утром", "вечером", "ночью", "днем", "днём", "днем", "тогда",
}
CLARIFYING_PREPOSITIONS = {
    "у", "около", "возле", "за", "под", "над", "перед", "в", "на",
    "между", "после", "до", "к", "от",
}
NOUN_LIKE = {"NOUN", "NUMR", "PRON"}


def _is_punct(token):
    return getattr(token, "is_punctuation", token.text in ",.!?;:—–()-")


def _is_comma(tokens, start, end):
    return any(t.text == "," for t in tokens[start:end])


def _find_phrase_end(tokens, prep_index):
    """Находит конец короткой предложной группы уточнения.

    Допускает морфологически неоднозначные слова (UNKN) внутри группы,
    но останавливается на пунктуации или личном сказуемом.
    """
    i = prep_index + 1
    seen_nominal = False
    while i < len(tokens):
        token = tokens[i]
        if _is_punct(token) or token.pos in {"VERB", "PRED", "DEEPR"}:
            break
        if token.pos in NOUN_LIKE or token.pos in {"ADJ", "ADV", "UNKN"}:
            if token.pos in NOUN_LIKE:
                seen_nominal = True
            i += 1
            continue
        break
    return i if seen_nominal else None


def check_clarifying_members(sentence, tokens):
    findings = []
    for i, marker in enumerate(tokens):
        if _is_punct(marker):
            continue
        word = marker.text.lower().replace("ё", "е")
        if word not in PLACE_MARKERS | TIME_MARKERS:
            continue

        prep_index = i + 1
        # Уже поставленная запятая не должна скрывать уточнение.
        if prep_index < len(tokens) and tokens[prep_index].text == ",":
            prep_index += 1
        if prep_index >= len(tokens) or tokens[prep_index].text.lower() not in CLARIFYING_PREPOSITIONS:
            continue

        end = _find_phrase_end(tokens, prep_index)
        if end is None:
            continue

        phrase_start = tokens[prep_index].start
        phrase_end = tokens[end - 1].end

        has_opening_comma = "," in sentence[marker.end:phrase_start]
        has_closing_comma = end < len(tokens) and tokens[end].text == ","

        # Не выдаём предупреждения, если обе границы уточнения уже оформлены.
        if has_opening_comma and has_closing_comma:
            continue

        if not has_opening_comma:
            findings.append(Finding(
                "Уточняющий член предложения",
                "Уточняющее обстоятельство места или времени обычно отделяется запятой от уточняемого слова.",
                phrase_start, phrase_end,
                f"Поставьте запятую после слова «{marker.text}»."
            ))

        has_continuation = any(not _is_punct(t) for t in tokens[end:])
        if has_continuation and not has_closing_comma:
            findings.append(Finding(
                "Уточняющий член предложения",
                "Уточняющее обстоятельство обычно обособляется с двух сторон, если после него продолжается предложение.",
                phrase_start, phrase_end,
                "Поставьте запятую после уточняющего оборота."
            ))

    return findings
