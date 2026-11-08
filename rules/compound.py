"""Начальная эвристика проверки запятой между частями сложносочинённого предложения.

Проверяются конструкции с союзами «и», «а», «но», «да», когда после союза
обнаруживается новая грамматическая основа (подлежащее + сказуемое) либо
явное безличное сказуемое. Однородные сказуемые при общем подлежащем правило
не считает сложносочинённым предложением.
"""
from .base import Finding

COORDINATING_CONJUNCTIONS = {"и", "а", "но", "да"}
TERMINAL = {".", "!", "?", ";", ":", "—", "–"}
IMPERSONAL_LEMMAS = {
    "смеркаться", "темнеть", "светать", "вечереть", "холодать",
    "моросить", "морозить", "лихорадить", "нездоровиться",
}


def _is_punct(token):
    return getattr(token, "is_punctuation", token.text in ",.!?;:—–()-")


def _is_finite_predicate(token):
    if token.pos == "PRED":
        return True
    if token.pos != "VERB":
        return False
    tag = (getattr(token, "morph_tag", "") or "").upper()
    # pymorphy3 помечает инфинитив как INFN; его не считаем самостоятельной
    # грамматической основой без контекста.
    if "INFN" in tag:
        return False
    return True


def _is_subject_candidate(tokens, index):
    token = tokens[index]
    if token.pos not in {"NOUN", "PRON"}:
        return False
    if index > 0 and tokens[index - 1].pos == "PREP":
        return False
    return True


def _has_impersonal_predicate(tokens, predicate_index):
    token = tokens[predicate_index]
    tag = (getattr(token, "morph_tag", "") or "").lower()
    lemma = (getattr(token, "lemma", "") or token.text).lower()
    if "impers" in tag or lemma in IMPERSONAL_LEMMAS:
        return True
    # Конструкции типа «стало холодно», «было темно».
    for following in tokens[predicate_index + 1:predicate_index + 3]:
        if _is_punct(following):
            break
        if following.pos == "PRED":
            return True
    return token.pos == "PRED"


def _find_left_predicate(tokens, conjunction_index):
    for i in range(conjunction_index - 1, -1, -1):
        token = tokens[i]
        if token.text in TERMINAL or token.text in COORDINATING_CONJUNCTIONS:
            break
        if _is_finite_predicate(token):
            return i
    return None


def _find_right_predicate(tokens, conjunction_index):
    for i in range(conjunction_index + 1, len(tokens)):
        token = tokens[i]
        if token.text in TERMINAL or token.text in COORDINATING_CONJUNCTIONS:
            break
        if _is_finite_predicate(token):
            return i
    return None


def _has_explicit_subject(tokens, start, end):
    return any(_is_subject_candidate(tokens, i) for i in range(start, end))


def check_compound_sentences(sentence, tokens):
    findings = []
    for i, token in enumerate(tokens):
        if _is_punct(token) or token.text.lower() not in COORDINATING_CONJUNCTIONS:
            continue

        left_predicate = _find_left_predicate(tokens, i)
        right_predicate = _find_right_predicate(tokens, i)
        if left_predicate is None or right_predicate is None:
            continue

        # Запятая может стоять непосредственно перед союзом.
        if any(tokens[k].text == "," for k in range(left_predicate + 1, i)):
            continue

        # Новое подлежащее справа от союза — сильный признак второй основы.
        has_right_subject = _has_explicit_subject(tokens, i + 1, right_predicate)
        right_is_impersonal = _has_impersonal_predicate(tokens, right_predicate)
        if not has_right_subject and not right_is_impersonal:
            # «Маша пришла и села» — общее подлежащее, запятая не нужна.
            continue

        findings.append(Finding(
            "Сложносочинённое предложение",
            "Между частями сложносочинённого предложения обычно ставится запятая перед сочинительным союзом.",
            token.start, token.end,
            f"Поставьте запятую перед союзом «{token.text.lower()}»."
        ))

    unique = {}
    for finding in findings:
        unique[(finding.start, finding.end, finding.message)] = finding
    return list(unique.values())
