"""Безопасное текстовое отображение предполагаемого места запятой."""
import re


def _position_from_finding(sentence, finding):
    start = max(0, min(len(sentence), int(finding.get("start", 0))))
    end = max(start, min(len(sentence), int(finding.get("end", start))))
    suggestion = (finding.get("suggestion") or "").lower()

    # У уточняющих конструкций рекомендация может указывать на конкретное
    # слово-маркер («после слова "там"»), которое не совпадает с диапазоном
    # самой уточняющей группы. Ищем его в исходном предложении.
    quoted_word = re.search(r"после слова\s+[«\"]([^»\"]+)[»\"]", suggestion)
    if quoted_word:
        target = quoted_word.group(1)
        matches = list(re.finditer(re.escape(target), sentence, flags=re.IGNORECASE))
        if matches:
            match = min(matches, key=lambda item: abs(item.start() - start))
            return match.end(), "после слова «{}»".format(target)

    if "перед" in suggestion:
        return start, "перед выделенным фрагментом"
    if "после" in suggestion:
        return end, "после выделенного фрагмента"
    return start, "в начале выделенного фрагмента"


def build_location_marker(sentence, finding, context=38):
    """Вернуть (фрагмент, указатель, подпись) для конкретной позиции.

    Использует только обычный текст. Это позволяет показывать пользовательский
    ввод без вставки необработанного HTML в интерфейс.
    """
    position, label = _position_from_finding(sentence, finding)
    left = max(0, position - context)
    right = min(len(sentence), position + context)
    excerpt = sentence[left:right].replace("\t", " ")
    relative = max(0, min(len(excerpt), position - left))
    pointer = " " * relative + "^"
    if left > 0:
        excerpt = "…" + excerpt
        pointer = " " + pointer
    if right < len(sentence):
        excerpt += "…"
    return excerpt, pointer, "Предполагаемая позиция запятой: {}".format(label)
