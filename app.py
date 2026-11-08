import streamlit as st
from analyzer import SyntaxAnalyzer
from ui_helpers import build_location_marker

st.set_page_config(page_title="SyntaxGuard", page_icon="🛡️", layout="wide")
st.title("🛡️ SyntaxGuard: проверка пунктуации")
st.caption(
    "Проверка причастных и деепричастных оборотов, вводных конструкций, "
    "однородных членов, обращений, сложносочинённых предложений, "
    "сравнительных оборотов, уточнений и противительных союзов."
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
                continue
            if item["status"] != "error":
                continue

            st.warning(item["text"])
            for number, finding in enumerate(item.get("findings", []), start=1):
                st.markdown(f"**Замечание {number}. {finding['rule']}**")
                st.write(finding["message"])
                excerpt, pointer, label = build_location_marker(item["text"], finding)
                st.caption(label)
                st.code(excerpt + "\n" + pointer, language=None)
                if finding.get("suggestion"):
                    st.caption(f"Рекомендация: {finding['suggestion']}")

        st.info(
            "SyntaxGuard — учебный пунктуационный анализатор на основе "
            "морфологического анализа и эвристических правил. Он проверяет "
            "ограниченный набор конструкций; отсутствие замечаний не гарантирует "
            "абсолютную пунктуационную правильность. Сомнительные случаи нужно "
            "проверять по контексту."
        )
