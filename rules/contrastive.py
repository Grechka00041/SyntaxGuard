"""Проверка запятой перед противительными союзами.

В этой версии уверенно обрабатываются «а» и «но» между однородными словами
одной части речи, а также некоторые конструкции с «да» в значении «но».
Сочетание «быстро да аккуратно» не трактуется как противительное.
"""
from .base import Finding

CONTRASTIVE_CONJUNCTIONS = {"а", "но"}
DA_CONTRAST_HINTS = {
    "мал", "малый", "маленький", "короткий", "прост", "простой",
    "бедный", "дешевый", "дешёвый", "худой", "слабый",
}
COMPARABLE_POS = {"NOUN", "ADJ", "ADV", "VERB"}


def _is_punct(token):
    return getattr(token, "is_punctuation", token.text in ",.!?;:—–()-")


def check_contrastive_conjunctions(sentence, tokens):
    findings = []
    for i, conjunction in enumerate(tokens):
        if _is_punct(conjunction):
            continue
        word = conjunction.text.lower()
        if word not in CONTRASTIVE_CONJUNCTIONS | {"да"}:
            continue
        if i == 0 or i + 1 >= len(tokens):
            continue

        left = tokens[i - 1]
        right = tokens[i + 1]
        if _is_punct(left) or _is_punct(right):
            continue

        # Не рассматриваем «да» как противительный союз без контекстного сигнала:
        # чаще оно означает соединительное «и».
        if word == "да":
            left_lemma = (getattr(left, "lemma", "") or left.text).lower()
            preceding_lemma = ""
            if i >= 2:
                preceding = tokens[i - 2]
                preceding_lemma = (getattr(preceding, "lemma", "") or preceding.text).lower()
            da_is_contrastive = left_lemma in DA_CONTRAST_HINTS or preceding_lemma in DA_CONTRAST_HINTS
            if not da_is_contrastive:
                continue
            # В устойчивом примере «мал золотник да дорог» элементы
            # противопоставления могут иметь разную часть речи.
            if left.pos not in COMPARABLE_POS or right.pos not in COMPARABLE_POS:
                continue
        elif word == "а":
            # Противительное «а» соединяет не только однородные члены,
            # но и части предложений с разными типами сказуемых:
            # «День был пасмурным, а вечер солнечным».
            pass
        elif left.pos not in COMPARABLE_POS or right.pos != left.pos:
            continue

        if i > 0 and tokens[i - 1].text == ",":
            continue

        findings.append(Finding(
            "Противительный союз",
            f"Перед противительным союзом «{word}» между однородными членами ставится запятая.",
            conjunction.start, conjunction.end,
            f"Поставьте запятую перед союзом «{word}»."
        ))

    return findings
