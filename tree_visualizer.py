"""Графическое отображение синтаксических деревьев в формате SVG.

Модуль не требует Graphviz или дополнительных библиотек: дерево получает
структуру от syntax_parser.py и визуализирует её в виде безопасного SVG.
В графике сохраняются формальные метки КС-грамматики и рядом показываются
их русские пояснения.
"""
from __future__ import annotations

from html import escape
from typing import Any


INTERNAL_HEIGHT = 58
LEAF_HEIGHT = 88
LEAF_SPACING = 210
LEVEL_SPACING = 118
LEFT_MARGIN = 60
TOP_MARGIN = 62
RIGHT_MARGIN = 60
BOTTOM_MARGIN = 46

# Нетерминалы КС-грамматики: формальные обозначения сохраняются,
# русское название показывается рядом/под ними в графическом дереве.
NONTERMINAL_RU = {
    "S": "Предложение",
    "CLAUSE": "Предикативная часть",
    "NP": "Именная группа",
    "VP": "Глагольная группа",
    "PP": "Предложная группа",
    "ADDR": "Обращение",
    "HOMOG_NP": "Однородная именная группа",
    "GREETING_PHRASE": "Формула приветствия",
}

# Терминалы, получаемые из морфологических категорий.
TERMINAL_RU = {
    "NOUN": "Существительное",
    "PROPN": "Имя собственное",
    "PRON": "Местоимение",
    "VERB": "Глагол",
    "ADJ": "Прилагательное",
    "GREETING_ADJ": "Слово в формуле приветствия",
    "SHORT_ADJ": "Краткое прилагательное",
    "PART": "Причастие",
    "SHORT_PART": "Краткое причастие",
    "DEEPR": "Деепричастие",
    "ADV": "Наречие",
    "PREP": "Предлог",
    "CONJ": "Союз",
    "NUMR": "Числительное",
    "PRED": "Слово категории состояния",
    "PARTICLE": "Частица",
    "INTJ": "Междометие",
    "INFN": "Инфинитив",
    "GREETING": "Приветствие",
}


def _validate_node(node: Any) -> dict:
    """Нормализовать узел дерева, не доверяя входным HTML/SVG-строкам."""
    if not isinstance(node, dict):
        raise ValueError("Узел дерева должен быть словарём.")
    label = str(node.get("label", ""))
    word = node.get("word")
    children = node.get("children", [])
    if not isinstance(children, list):
        raise ValueError("Поле children должно быть списком.")
    normalized = {
        "label": label,
        "word": None if word is None else str(word),
        "children": [_validate_node(child) for child in children],
    }
    if normalized["word"] is not None and normalized["children"]:
        raise ValueError("Лексический узел не должен содержать дочерние узлы.")
    return normalized


def _prepare_layout(root: dict):
    """Назначить координаты узлам по порядку листьев и глубине дерева."""
    cursor = 0
    nodes = {}
    edges = []
    max_depth = 0
    next_id = 0

    def place(node: dict, depth: int):
        nonlocal cursor, max_depth, next_id
        max_depth = max(max_depth, depth)
        node_id = next_id
        next_id += 1
        child_ids = [place(child, depth + 1) for child in node["children"]]

        if not child_ids:
            x = LEFT_MARGIN + cursor * LEAF_SPACING + LEAF_SPACING / 2
            cursor += 1
        else:
            first_x = nodes[child_ids[0]]["x"]
            last_x = nodes[child_ids[-1]]["x"]
            x = (first_x + last_x) / 2
            for child_id in child_ids:
                edges.append((node_id, child_id))

        nodes[node_id] = {
            "node": node,
            "x": x,
            "y": TOP_MARGIN + depth * LEVEL_SPACING,
            "depth": depth,
        }
        return node_id

    place(root, 0)
    leaf_count = max(1, cursor)
    width = max(520, int(LEFT_MARGIN + RIGHT_MARGIN + leaf_count * LEAF_SPACING))
    height = int(TOP_MARGIN + (max_depth + 1) * LEVEL_SPACING + BOTTOM_MARGIN)
    return nodes, edges, width, height


def render_tree_html(tree_data: dict, title: str = "Синтаксическое дерево") -> tuple[str, int]:
    """Вернуть HTML-документ с графическим SVG-деревом и высоту iframe.

    Формальная метка CFG (например, NP) сохраняется. Под ней выводится русское
    пояснение (например, «Именная группа»). Листья показывают код части речи,
    её русское название и исходное слово. Пользовательский текст экранируется.
    """
    root = _validate_node(tree_data)
    nodes, edges, width, height = _prepare_layout(root)

    def node_height(node):
        return LEAF_HEIGHT if node["word"] is not None else INTERNAL_HEIGHT

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{escape(title, quote=True)}" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        """<defs>
          <linearGradient id="sg-root" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#dbeafe"/>
            <stop offset="100%" stop-color="#bfdbfe"/>
          </linearGradient>
          <filter id="sg-shadow" x="-20%" y="-20%" width="140%" height="150%">
            <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#0f172a" flood-opacity="0.10"/>
          </filter>
        </defs>""",
        """<style>
          .sg-edge { stroke: #94a3b8; stroke-width: 2.2; fill: none; }
          .sg-node rect { filter: url(#sg-shadow); stroke-width: 1.4; }
          .sg-internal rect { fill: #f1f5f9; stroke: #94a3b8; }
          .sg-root rect { fill: url(#sg-root); stroke: #3b82f6; stroke-width: 2; }
          .sg-code { font: 700 12px system-ui, sans-serif; fill: #1e293b; text-anchor: middle; }
          .sg-meaning { font: 500 10px system-ui, sans-serif; fill: #475569; text-anchor: middle; }
          .sg-leaf rect { fill: #ecfdf5; stroke: #34d399; }
          .sg-tag { font: 700 10px system-ui, sans-serif; fill: #047857; text-anchor: middle; }
          .sg-meaning-leaf { font: 500 10px system-ui, sans-serif; fill: #047857; text-anchor: middle; }
          .sg-word { font: 700 14px system-ui, sans-serif; fill: #064e3b; text-anchor: middle; }
        </style>""",
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="14" fill="#ffffff"/>',
    ]

    # Рисуем связи до узлов, чтобы линии не перекрывали подписи.
    for parent_id, child_id in edges:
        parent = nodes[parent_id]
        child = nodes[child_id]
        parent_x, child_x = parent["x"], child["x"]
        y1 = parent["y"] + node_height(parent["node"]) / 2
        y2 = child["y"] - node_height(child["node"]) / 2
        svg_parts.append(
            f'<path class="sg-edge" d="M {parent_x:.1f} {y1:.1f} '
            f'C {parent_x:.1f} {(y1 + y2) / 2:.1f}, '
            f'{child_x:.1f} {(y1 + y2) / 2:.1f}, {child_x:.1f} {y2:.1f}"/>'
        )

    for item in nodes.values():
        node = item["node"]
        x, y = item["x"], item["y"]
        label = escape(node["label"])
        if node["word"] is not None:
            word = escape(node["word"])
            meaning = escape(TERMINAL_RU.get(node["label"], node["label"]))
            box_width = max(
                128,
                min(230, max(len(meaning) * 6.7, len(node["word"]) * 7.8) + 34),
            )
            svg_parts.append(
                f'<g class="sg-node sg-leaf" transform="translate({x:.1f},{y:.1f})">'
                f'<rect x="{-box_width/2:.1f}" y="{-LEAF_HEIGHT/2}" '
                f'width="{box_width:.1f}" height="{LEAF_HEIGHT}" rx="10"/>'
                f'<text class="sg-tag" x="0" y="-27">{label}</text>'
                f'<text class="sg-meaning-leaf" x="0" y="-9">{meaning}</text>'
                f'<text class="sg-word" x="0" y="19">{word}</text>'
                "</g>"
            )
        else:
            meaning = escape(NONTERMINAL_RU.get(node["label"], node["label"]))
            box_width = max(100, min(190, max(len(node["label"]) * 9, len(NONTERMINAL_RU.get(node["label"], node["label"])) * 6.2) + 30))
            root_class = "sg-root" if item["depth"] == 0 else "sg-internal"
            svg_parts.append(
                f'<g class="sg-node {root_class}" transform="translate({x:.1f},{y:.1f})">'
                f'<rect x="{-box_width/2:.1f}" y="{-INTERNAL_HEIGHT/2}" '
                f'width="{box_width:.1f}" height="{INTERNAL_HEIGHT}" rx="12"/>'
                f'<text class="sg-code" x="0" y="-5">{label}</text>'
                f'<text class="sg-meaning" x="0" y="14">{meaning}</text>'
                "</g>"
            )

    svg_parts.append("</svg>")
    svg = "".join(svg_parts)
    document = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  html, body {{ margin: 0; padding: 0; background: transparent; }}
  .sg-scroll {{ width: 100%; overflow-x: auto; overflow-y: hidden; padding: 4px 0 10px; }}
  svg {{ display: block; max-width: none; height: auto; }}
</style>
</head>
<body><div class="sg-scroll">{svg}</div></body>
</html>"""
    iframe_height = min(max(height + 18, 210), 1200)
    return document, iframe_height
