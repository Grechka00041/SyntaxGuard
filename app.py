import streamlit as st
from analyzer import SyntaxAnalyzer

st.set_page_config(page_title="SyntaxGuard", layout="wide")
st.title("🛡️ SyntaxGuard: Проверка пунктуации")

st.markdown("""
**Легенда:**
- 🔴 **Красный**: Пропущена запятая при обороте или синтаксическая ошибка.
- ✅ **Без подчеркивания**: Корректное предложение.
""")


@st.cache_resource
def load_analyzer():
    return SyntaxAnalyzer()


try:
    analyzer = load_analyzer()
except Exception as e:
    st.error(f"❌ Не удалось загрузить систему: {e}")
    st.stop()

user_text = st.text_area(
    "Вставьте текст:",
    height=300,
    placeholder="Например: Анализируя данные студент нашел ошибку."
)

if st.button("Проверить текст", type="primary"):
    if user_text.strip():
        with st.spinner('Анализируем...'):
            results = analyzer.analyze_full_text(user_text)

            html_parts = []
            stats = {"ok": 0, "error": 0}

            for item in results:
                status = item['status']
                stats[status] = stats.get(status, 0) + 1
                text = item['text']

                if status == 'ok':
                    html_parts.append(f"<span>{text}</span>")
                else:
                    color = item['color']
                    msg = item['msg'].replace('"', '&quot;')

                    html_parts.append(
                        f'<span class="sg-tooltip" style="border-bottom: 2px dotted {color}; cursor: help;">'
                        f'{text}'
                        f'<span class="sg-tooltiptext">{msg}</span>'
                        f'</span>'
                    )
                html_parts.append(" ")

            # ТОЛЬКО 2 КОЛОНКИ
            col1, col2 = st.columns(2)
            col1.metric("✅ Корректных", stats["ok"])
            col2.metric("❌ Ошибок", stats["error"])

            st.divider()
            st.subheader("Размеченный текст:")

            css_styles = """
            <style>
            .sg-tooltip { position: relative; display: inline-block; border-bottom: 2px dotted; }
            .sg-tooltiptext {
                visibility: hidden; width: 320px; background-color: #2b2b2b; color: #fff;
                text-align: left; border-radius: 6px; padding: 10px; position: absolute;
                z-index: 1000; bottom: 130%; left: 50%; margin-left: -160px; opacity: 0;
                transition: opacity 0.3s; font-size: 14px; line-height: 1.4;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3); pointer-events: none;
            }
            .sg-tooltip:hover .sg-tooltiptext { visibility: visible; opacity: 1; }
            .sg-tooltiptext::after {
                content: ""; position: absolute; top: 100%; left: 50%; margin-left: -8px;
                border-width: 8px; border-style: solid; border-color: #2b2b2b transparent transparent transparent;
            }
            </style>
            """

            final_html = "".join(html_parts)
            st.markdown(
                f'{css_styles}<div style="white-space: pre-wrap; line-height: 1.8; font-size: 17px; font-family: sans-serif;">{final_html}</div>',
                unsafe_allow_html=True
            )
    else:
        st.warning("Пожалуйста, введите текст.")