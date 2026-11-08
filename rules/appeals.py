"""Эвристическая проверка запятых при обращениях.

Проверка намеренно ограничена:
- распознаёт частые обращения по словарю;
- распознаёт имена собственные по морфологической помете pymorphy3 (Name);
- при отсутствии запятых требует дополнительный сигнал (повелительная форма
  рядом или позиция в конце обращения), чтобы не путать обращение с подлежащим.
Это учебная эвристика, а не полный синтаксический анализ.
"""
from .base import Finding

ADDRESS_WORDS = {
    "мама", "папа", "мам", "пап", "друзья", "ребята", "коллеги",
    "господа", "товарищи", "брат", "сестра", "дети", "девушка",
    "молодой человек", "уважаемые", "дорогие", "граждане", "народ",
    "доктор", "профессор", "учитель", "учителя", "девочки", "мальчики",
}

# Небольшой резервный список на случай, если конкретная форма не получила
# грамматическую помету impr в установленной версии словаря.
IMPERATIVE_FORMS = {
    "скажи", "скажите", "закрой", "закройте", "открой", "откройте",
    "посмотри", "посмотрите", "подойди", "подойдите", "подумай",
    "подумайте", "возьми", "возьмите", "иди", "идите", "приходи",
    "приходите", "позвони", "позвоните", "ответь", "ответьте",
    "слушай", "слушайте", "напиши", "напишите", "прочитай", "прочитайте",
    "помоги", "помогите", "подожди", "подождите", "сделай", "сделайте",
    "обрати", "обратите", "обращай", "обращайте", "обратитесь",
}

TERMINAL = {".", "!", "?", ";"}


def _is_punct(token):
    return getattr(token, "is_punctuation", token.text in ",.!?;:—–()-")


def _is_comma(token):
    return token.text == ","


def _is_proper_name(token):
    tag = getattr(token, "morph_tag", "") or ""
    return "name" in str(tag).lower() or "surn" in str(tag).lower() or "patr" in str(tag).lower()


def _is_imperative(token):
    tag = (getattr(token, "morph_tag", "") or "").lower()
    lemma = (getattr(token, "lemma", "") or token.text).lower()
    return "impr" in tag or lemma in IMPERATIVE_FORMS or token.text.lower() in IMPERATIVE_FORMS


def _is_address_candidate(token):
    text = token.text.lower().replace("ё", "е")
    lemma = (getattr(token, "lemma", "") or "").lower().replace("ё", "е")
    return text in ADDRESS_WORDS or lemma in ADDRESS_WORDS or _is_proper_name(token)


def _word_index_before(tokens, index):
    for i in range(index - 1, -1, -1):
        if not _is_punct(tokens[i]):
            return i
    return None


def _word_index_after(tokens, index):
    for i in range(index + 1, len(tokens)):
        if not _is_punct(tokens[i]):
            return i
    return None


def _follows_gerund_clause(tokens, index, previous_word):
    """Не принимает подлежащее после деепричастного оборота за обращение.

    Примеры: «Увидев друга, девушка улыбнулась» и
    «Прочитав письмо, Анна задумалась».
    """
    if index == 0 or not _is_comma(tokens[index - 1]) or previous_word is None:
        return False
    # Ищем деепричастие в ближайшей левой группе; если после него до
    # запятой нет личного глагола, кандидат — вероятнее подлежащее.
    lower_bound = max(0, previous_word - 5)
    for j in range(previous_word, lower_bound - 1, -1):
        if tokens[j].pos == "DEEPR":
            has_finite_verb = any(
                tokens[k].pos in {"VERB", "PRED"}
                for k in range(j + 1, index - 1)
            )
            return not has_finite_verb
        if tokens[j].text in TERMINAL:
            break
    return False


def check_appeals(sentence, tokens):
    findings = []
    for i, token in enumerate(tokens):
        if _is_punct(token) or not _is_address_candidate(token):
            continue

        prev_word = _word_index_before(tokens, i)
        next_word = _word_index_after(tokens, i)
        if _follows_gerund_clause(tokens, i, prev_word):
            continue

        # Не распознаём существительное как обращение, если оно входит
        # в сравнительную/ролевую конструкцию: «Он, как учитель, объяснил»;
        # «Она, в качестве докладчика, выступила». Эта проверка должна
        # выполняться и для середины предложения, а не только для конца.
        if prev_word is not None:
            previous_context = tokens[prev_word]
            previous_text = previous_context.text.lower().replace("ё", "е")
            previous_lemma = (getattr(previous_context, "lemma", "") or previous_context.text).lower().replace("ё", "е")
            if previous_text in {"как", "будто", "словно", "точно", "качестве"}:
                continue
            # «Он, как и брат, любит спорт»: слово «брат» входит в
            # сравнительную конструкцию, а не является обращением.
            if (previous_text == "и" and prev_word > 0
                    and tokens[prev_word - 1].text.lower() == "как"):
                continue
            if previous_lemma == "качество":
                continue

        at_start = prev_word is None
        at_end = next_word is None
        comma_before = i > 0 and _is_comma(tokens[i - 1])
        comma_after = i + 1 < len(tokens) and _is_comma(tokens[i + 1])

        if at_start:
            # В начале предложения обращение без запятой распознаём,
            # только если дальше следует повелительная форма.
            if comma_after:
                continue
            if next_word is not None and _is_imperative(tokens[next_word]):
                findings.append(Finding(
                    "Обращение",
                    "Обращение в начале предложения отделяется запятой от последующей части.",
                    token.start, token.end,
                    "Поставьте запятую после обращения."
                ))
            continue

        if at_end:
            if comma_before:
                continue
            previous = tokens[prev_word]
            previous_word = previous.text.lower().replace("ё", "е")
            previous_lemma = (getattr(previous, "lemma", "") or previous.text).lower().replace("ё", "е")

            # Не принимаем именную часть обстоятельства/сравнения за обращение:
            # «Он работает как учитель», «Она выступает в качестве докладчика».
            # После предлога или сравнительного/подчинительного союза конечное
            # существительное обычно является частью конструкции, а не вокативом.
            if previous_word in {"как", "будто", "словно", "точно"}:
                continue
            if previous.pos in {"PREP", "CONJ"}:
                continue
            if previous_word == "качестве" or previous_lemma == "качество":
                continue

            # Не принимаем прямое дополнение в винительном падеже за обращение:
            # «Позови папу», «Я встретил маму». Для pymorphy3 падеж обозначается
            # пометой accs. Это особенно важно после повелительного глагола.
            token_tag = (getattr(token, "morph_tag", "") or "").lower()
            if previous.pos in {"VERB", "PRED"} and "accs" in token_tag:
                continue

            # Конечное имя не считаем обращением, если непосредственно перед
            # ним стоит сказуемое: «Пришла Маша» — здесь это подлежащее.
            if _is_proper_name(token) and previous.pos in {"VERB", "PRED"}:
                continue
            if token.text.lower() in ADDRESS_WORDS or token.lemma.lower() in ADDRESS_WORDS or _is_proper_name(token):
                findings.append(Finding(
                    "Обращение",
                    "Обращение в конце предложения обычно отделяется запятой слева.",
                    token.start, token.end,
                    "Поставьте запятую перед обращением."
                ))
            continue

        previous = tokens[prev_word]
        # В середине предложения уверенно распознаём обращение после
        # повелительного глагола либо при уже поставленной одной из запятых.
        address_context = (
            _is_imperative(previous)
            or comma_before
            or comma_after
        )
        if not address_context:
            continue

        if not comma_before:
            findings.append(Finding(
                "Обращение",
                "Обращение в середине предложения выделяется запятыми с двух сторон.",
                token.start, token.end,
                "Поставьте запятую перед обращением."
            ))
        if not comma_after:
            findings.append(Finding(
                "Обращение",
                "Обращение в середине предложения выделяется запятыми с двух сторон.",
                token.start, token.end,
                "Поставьте запятую после обращения."
            ))

    unique = {}
    for finding in findings:
        unique[(finding.start, finding.end, finding.suggestion)] = finding
    return list(unique.values())
