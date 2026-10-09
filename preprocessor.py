import pymorphy3
import re

morph = pymorphy3.MorphAnalyzer()

TAG_MAPPING = {
    'NOUN': 'NOUN', 'VERB': 'VERB', 'INFN': 'VERB',
    'ADJF': 'ADJ', 'ADJS': 'ADJ', 'COMP': 'ADJ',
    'GRND': 'DEEPR', 'PRTF': 'PART', 'PRTS': 'PART',
    'PREP': 'PREP', 'CONJ': 'CONJ', 'INTJ': 'INTRO',
    'PRON': 'PRON', 'NUMR': 'NUMR', 'ADVB': 'ADV'
}


def get_pos_tag(word):
    clean_word = re.sub(r'[^\w\s-]', '', word)
    if not clean_word:
        return None

    parses = morph.parse(clean_word)
    if not parses:
        return 'UNKN'

    pos = parses[0].tag.POS
    return TAG_MAPPING.get(pos, 'UNKN')


def sentence_to_tags(sentence):
    # Добавляем пробелы вокруг знаков препинания
    temp_sent = re.sub(r'([,.!?;:])', r' \1 ', sentence)
    tokens = temp_sent.split()

    tags = []
    for token in tokens:
        if token == ',':
            tags.append('PUNCT')
            continue
        # ИГНОРИРУЕМ ТОЧКУ И ДРУГИЕ КОНЕЧНЫЕ ЗНАКИ
        elif token in ['.', '!', '?', ';']:
            continue

        clean_word = re.sub(r'[^\w\s-]', '', token)
        if not clean_word:
            continue

        tag = get_pos_tag(clean_word)
        if tag:
            tags.append(tag)

    return " ".join(tags)