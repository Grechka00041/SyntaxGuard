import unittest

from tree_visualizer import render_tree_html


class TreeVisualizerTests(unittest.TestCase):
    def setUp(self):
        self.tree = {
            "label": "S",
            "children": [
                {
                    "label": "CLAUSE",
                    "children": [
                        {"label": "NP", "children": [
                            {"label": "NOUN", "word": "Студент", "children": []}
                        ]},
                        {"label": "VP", "children": [
                            {"label": "VERB", "word": "читает", "children": []},
                            {"label": "NP", "children": [
                                {"label": "NOUN", "word": "книгу", "children": []}
                            ]},
                        ]},
                    ],
                }
            ],
        }

    def test_svg_contains_all_syntax_labels_and_words(self):
        html, height = render_tree_html(self.tree)
        self.assertIn("<svg", html)
        for value in (
            "S", "Предложение", "CLAUSE", "Предикативная часть",
            "NP", "Именная группа", "VP", "Глагольная группа",
            "NOUN", "Существительное", "Студент", "читает", "книгу",
        ):
            self.assertIn(value, html)
        self.assertGreater(height, 190)
        # Между каждым родительским и дочерним узлом рисуется отдельное ребро.
        self.assertEqual(html.count('<path class="sg-edge"'), 7)

    def test_svg_supports_cfg_v2_labels_in_russian(self):
        tree = {
            "label": "S",
            "children": [
                {"label": "GREETING_PHRASE", "children": [
                    {"label": "GREETING_ADJ", "word": "доброе", "children": []},
                    {"label": "NOUN", "word": "утро", "children": []},
                ]}
            ],
        }
        html, _ = render_tree_html(tree)
        self.assertIn("Формула приветствия", html)
        self.assertIn("Слово в формуле приветствия", html)
        self.assertIn("доброе", html)
        self.assertIn("утро", html)

    def test_user_text_is_escaped(self):
        tree = {
            "label": "S",
            "children": [{"label": "NOUN", "word": "<script>alert(1)</script>", "children": []}],
        }
        html, _ = render_tree_html(tree)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_long_sentence_gets_scrollable_svg_width(self):
        tree = {"label": "S", "children": [
            {"label": "NOUN", "word": f"слово{i}", "children": []}
            for i in range(10)
        ]}
        html, _ = render_tree_html(tree)
        self.assertIn("overflow-x: auto", html)
        self.assertIn('width="2220"', html)

    def test_invalid_node_is_rejected(self):
        with self.assertRaises(ValueError):
            render_tree_html(["not", "a", "dict"])


if __name__ == "__main__":
    unittest.main()
