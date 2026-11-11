import streamlit as st
import streamlit.components.v1 as components

from analyzer import SyntaxAnalyzer
from ui_helpers import build_location_marker
from tree_visualizer import render_tree_html

st.set_page_config(page_title="SyntaxGuard", page_icon="🛡️", layout="wide")
st.title("🛡️ SyntaxGuard: проверка пунктуации и синтаксиса")
st.caption(
    "Пунктуационные правила: причастные и деепричастные обороты, вводные конструкции, "
    "однородные члены, обращения, сложносочинённые предложения, сравнительные обороты, "
    "уточнения и противительные союзы. Построение синтаксического дерева "
    "по контекстно-свободной грамматике."
)


@st.cache_resource
def load_analyzer():
    return SyntaxAnalyzer()


try:
    analyzer = load_analyzer()
except Exception as exc:
    st.error(f"Не удалось загрузить анализатор: {exc}")
    st.stop()


def render_punctuation_findings(item: dict) -> None:
    """Замечания по пунктуации: с указанием позиции запятой."""
    findings = item.get("findings") or []
    for number, finding in enumerate(findings, start=1):
        st.markdown(f"**Замечание {number}. {finding['rule']}**")
        st.write(finding["message"])

        marker = build_location_marker(item["text"], finding)
        if marker:
            excerpt, pointer, label = marker
            st.caption(label)
            st.code(excerpt + "\n" + pointer, language=None)

        if finding.get("suggestion"):
            st.caption(f"Рекомендация: {finding['suggestion']}")


def render_syntax_findings(item: dict) -> None:
    """Замечания по структуре: показываем фрагмент."""
    notes = item.get("syntax_findings") or []
    if not notes:
        return

    st.markdown("#### Наблюдения по синтаксической структуре")
    st.caption(
        "Эти замечания получены из дерева КС-разбора. Они не являются "
        "пунктуационными ошибками и не всегда означают ошибку текста: "
        "часто это особенности структуры или ограничения учебной грамматики."
    )

    sentence = item["text"]

    for number, note in enumerate(notes, start=1):
        st.markdown(f"**{number}. {note['rule']}**")
        st.write(note["message"])

        start = max(0, min(len(sentence), int(note.get("start", 0))))
        end = max(start, min(len(sentence), int(note.get("end", start))))
        fragment = sentence[start:end].strip()

        if fragment:
            st.caption("Фрагмент предложения:")
            st.code(fragment, language=None)

        if note.get("suggestion"):
            st.caption(f"Пояснение: {note['suggestion']}")

def render_syntax_block(item: dict) -> None:
    """Результат CFG-разбора: категории, деревья или причина отказа."""
    syntax = (item or {}).get("syntax") or {}
    status = syntax.get("status")

    with st.expander(" Синтаксическое дерево (контекстно-свободная грамматика)"):
        st.caption(
            "КС-грамматика анализирует последовательность частей речи и показывает "
            "структуру предложения. Формальные обозначения сохранены, а их русские "
            "значения приведены в графическом дереве и справке ниже. "
            "Синтаксический разбор не заменяет пунктуационные правила."
        )

        tags = syntax.get("tags") or []
        if tags:
            st.caption("Последовательность категорий: " + " → ".join(tags))

        if status == "parsed":
            tree_data = syntax.get("tree_data") or []
            total = syntax.get("tree_count", len(tree_data))
            for index, node in enumerate(tree_data, start=1):
                if total > 1:
                    st.markdown(f"**Вариант разбора {index} из {total}**")
                try:
                    document, height = render_tree_html(node)
                except ValueError as exc:
                    st.caption(f"Не удалось отобразить дерево: {exc}")
                    continue
                components.html(document, height=height, scrolling=False)

            if syntax.get("more_trees_available"):
                st.caption(
                    "Грамматика допускает больше вариантов разбора, чем показано. "
                    "Это свойство КС-грамматик с рекурсивными правилами."
                )

            with st.expander("Текстовое представление дерева"):
                for text_tree in syntax.get("trees") or []:
                    st.code(text_tree, language=None)

        elif status in {"too_long", "too_ambiguous"}:
            st.info(syntax.get("message", "Разбор ограничен по сложности."))

        elif status == "not_parsed":
            st.caption(
                syntax.get(
                    "message",
                    "Последовательность частей речи не соответствует учебной КС-грамматике.",
                )
            )

        elif status == "error":
            st.warning(syntax.get("message", "Не удалось выполнить CFG-разбор."))

        else:
            st.caption("Синтаксический разбор недоступен.")

        with st.expander("Справка по обозначениям"):
            st.markdown(
                "**Нетерминалы:** S — предложение, CLAUSE — предикативная часть, "
                "NP — именная группа, VP — глагольная группа, PP — предложная группа, "
                "ATTRS — согласованные определения, NP_CHAIN — цепочка существительных, "
                "PREDICATIVE — именное сказуемое, DEEPR_PHRASE — деепричастный оборот, "
                "REL_CLAUSE — причастный или относительный оборот, "
                "COMPARATIVE — сравнительный оборот, HOMOG_NP — однородная группа, "
                "ADDR — обращение."
            )
            st.markdown(
                "**Терминалы** соответствуют частям речи: NOUN, PROPN, PRON, VERB, INFN, "
                "ADJ, SHORT_ADJ, PART, SHORT_PART, DEEPR, ADV, PREP, CONJ, NUMR, PRED, "
                "PARTICLE, INTJ, INTRO. Категория UNKN означает, что морфологический "
                "анализатор не распознал слово."
            )


user_text = st.text_area(
    "Введите текст:", height=260,
    placeholder="Например: Анализируя данные студент нашёл ошибку."
)

if st.button("Проверить текст", type="primary"):
    if not user_text.strip():
        st.warning("Пожалуйста, введите текст.")
    else:
        results = analyzer.analyze_full_text(user_text)
        ok_count = sum(item["status"] == "ok" for item in results)
        warning_count = sum(item["status"] == "error" for item in results)
        finding_count = sum(len(item.get("findings", [])) for item in results)
        syntax_note_count = sum(len(item.get("syntax_findings", [])) for item in results)
        parsed_count = sum(
            (item.get("syntax") or {}).get("status") == "parsed" for item in results
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Без замечаний", ok_count)
        col2.metric("С замечаниями", warning_count)
        col3.metric("Замечаний по пунктуации", finding_count)
        col4.metric("Замечаний по синтаксису", syntax_note_count)

        st.caption(f"Синтаксических деревьев построено: {parsed_count} из {len(results)}")

        st.divider()
        st.subheader("Результаты проверки")

        for item in results:
            if item["status"] == "empty":
                continue

            if item["status"] == "ok":
                st.success(item["text"])
            else:
                st.warning(item["text"])
                if item["status"] != "error" and item.get("msg"):
                    st.caption(item["msg"])

            render_punctuation_findings(item)
            render_syntax_findings(item)
            render_syntax_block(item)

            st.divider()

        st.info(
            "SyntaxGuard — учебный анализатор. Пунктуационные правила основаны на "
            "морфологическом анализе и эвристиках, синтаксический разбор — на "
            "контекстно-свободной грамматике и алгоритме ChartParser. Проверяется "
            "ограниченный набор конструкций; отсутствие замечаний не гарантирует "
            "абсолютную правильность текста. Сомнительные случаи нужно проверять "
            "по контексту."
        )