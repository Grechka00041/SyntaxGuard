import streamlit as st
import streamlit.components.v1 as components
from analyzer import SyntaxAnalyzer
from ui_helpers import build_location_marker
from tree_visualizer import render_tree_html

st.set_page_config(page_title="SyntaxGuard", page_icon="🛡️", layout="wide")
st.title("🛡️ SyntaxGuard: проверка пунктуации")
st.caption(
    "Проверка причастных и деепричастных оборотов, вводных конструкций, "
    "однородных членов, обращений, сложносочинённых предложений, "
    "сравнительных оборотов, уточнений и противительных союзов. "
    "Для поддерживаемых конструкций также строится синтаксическое дерево по КС-грамматике."
)

@st.cache_resource
def load_analyzer():
    return SyntaxAnalyzer()

try:
    analyzer = load_analyzer()
except Exception as exc:
    st.error(f"Не удалось загрузить анализатор: {exc}")
    st.stop()

user_text = st.text_area(
    "Введите текст:", height=260,
    placeholder="Например: Анализируя данные, студент нашёл ошибку."
)

if st.button("Проверить текст", type="primary"):
    if not user_text.strip():
        st.warning("Пожалуйста, введите текст.")
    else:
        results = analyzer.analyze_full_text(user_text)
        ok_count = sum(item["status"] == "ok" for item in results)
        warning_count = sum(item["status"] == "error" for item in results)
        finding_count = sum(len(item.get("findings", [])) for item in results)

        col1, col2, col3 = st.columns(3)
        col1.metric("Без замечаний", ok_count)
        col2.metric("С замечаниями", warning_count)
        col3.metric("Всего замечаний", finding_count)

        st.divider()
        st.subheader("Результаты проверки")
        for item in results:
            if item["status"] == "ok":
                st.success(item["text"])
            elif item["status"] == "error":
                st.warning(item["text"])
                for number, finding in enumerate(item.get("findings", []), start=1):
                    st.markdown(f"**Замечание {number}. {finding['rule']}**")
                    st.write(finding["message"])
                    excerpt, pointer, label = build_location_marker(item["text"], finding)
                    st.caption(label)
                    st.code(excerpt + "\n" + pointer, language=None)
                    if finding.get("suggestion"):
                        st.caption(f"Рекомендация: {finding['suggestion']}")
            else:
                continue

            # Синтаксическое дерево показывается и для корректных, и для
            # содержащих пунктуационные замечания предложений.
            syntax = item.get("syntax", {})
            with st.expander("Синтаксическое дерево (контекстно-свободная грамматика)"):
                st.caption(
                    "КС-грамматика анализирует последовательность частей речи и показывает структуру предложения. "
                    "Формальные обозначения сохранены, а их русские значения приведены в графическом дереве и справке ниже. "
                    "Синтаксический разбор не заменяет пунктуационные правила."
                )
                if syntax.get("tags"):
                    st.caption("Последовательность категорий: " + " → ".join(syntax["tags"]))
                if syntax.get("status") == "parsed":
                    if syntax.get("tree_count", 0) > 1:
                        suffix = "; возможны дополнительные варианты" if syntax.get("more_trees_available") else ""
                        st.caption(f"Показано вариантов дерева: {syntax['tree_count']}{suffix}.")
                    trees = syntax.get("trees", [])
                    tree_data_items = syntax.get("tree_data", [])
                    for tree_number, tree_text in enumerate(trees, start=1):
                        if len(trees) > 1:
                            st.markdown(f"**Вариант {tree_number}**")
                        if tree_number - 1 < len(tree_data_items):
                            tree_html, tree_height = render_tree_html(
                                tree_data_items[tree_number - 1],
                                title=f"Синтаксическое дерево, вариант {tree_number}",
                            )
                            components.html(tree_html, height=tree_height, scrolling=False)
                        else:
                            st.warning("Графическое представление дерева не сформировано.")
                        with st.expander("Текстовая форма дерева"):
                            st.code(tree_text, language="text")
                    with st.expander("Расшифровка обозначений в дереве"):
                        left, right = st.columns(2)
                        with left:
                            st.markdown(
                                "**Синтаксические группы**\n\n"
                                "| Код | Значение |\n|---|---|\n"
                                "| `S` | Предложение целиком |\n"
                                "| `CLAUSE` | Предикативная часть |\n"
                                "| `NP` | Именная группа |\n"
                                "| `VP` | Глагольная группа |\n"
                                "| `PP` | Предложная группа |\n"
                                "| `ADDR` | Обращение |\n"
                                "| `HOMOG_NP` | Однородная именная группа |\n"
                                "| `GREETING_PHRASE` | Формула приветствия |"
                            )
                        with right:
                            st.markdown(
                                "**Части речи**\n\n"
                                "| Код | Значение |\n|---|---|\n"
                                "| `NOUN` | Существительное |\n"
                                "| `PROPN` | Имя собственное |\n"
                                "| `PRON` | Местоимение |\n"
                                "| `VERB` | Глагол |\n"
                                "| `INFN` | Инфинитив |\n"
                                "| `ADJ` | Прилагательное |\n"
                                "| `GREETING_ADJ` | Слово в формуле приветствия |\n"
                                "| `SHORT_ADJ` | Краткое прилагательное |\n"
                                "| `PART` | Причастие |\n"
                                "| `SHORT_PART` | Краткое причастие |\n"
                                "| `DEEPR` | Деепричастие |\n"
                                "| `ADV` | Наречие |\n"
                                "| `PREP` | Предлог |\n"
                                "| `CONJ` | Союз |\n"
                                "| `NUMR` | Числительное |\n"
                                "| `PRED` | Слово категории состояния |\n"
                                "| `PARTICLE` | Частица |\n"
                                "| `INTJ` | Междометие |\n"
                                "| `GREETING` | Приветствие |"
                            )
                else:
                    st.caption(syntax.get("message", "Синтаксическое дерево для этой конструкции не построено."))

        st.info(
            "SyntaxGuard — учебный пунктуационный анализатор на основе "
            "морфологического анализа и эвристических правил. Он проверяет "
            "ограниченный набор конструкций; отсутствие замечаний не гарантирует "
            "абсолютную пунктуационную правильность. Сомнительные случаи нужно "
            "проверять по контексту."
        )
