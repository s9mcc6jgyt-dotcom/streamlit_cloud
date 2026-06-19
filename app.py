```python
# Import library utama Streamlit
import streamlit as st

# Import pandas untuk data tabel
import pandas as pd

# Import matplotlib untuk visualisasi
import matplotlib.pyplot as plt

# =====================================================
# JUDUL
# =====================================================

st.title("Chatbot Analitik Aset dan Gangguan")
st.caption("Conversational Analytics - Use Case C")

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.subheader("Contoh Pertanyaan")

    st.markdown("""
    - Berapa jumlah gangguan per aset?
    - Berapa rata-rata durasi pemulihan per jenis aset?
    - Apa penyebab gangguan yang paling sering terjadi?
    """)

    st.caption("Tekan Reset untuk menghapus riwayat percakapan.")

    if st.button("Reset"):
        st.session_state.messages = []
        st.rerun()

# =====================================================
# FUNGSI VISUAL STREAMLIT
# =====================================================

def tampilkan_visual(df):

    if df is None or df.empty:
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if len(df.columns) == 2 and len(numeric_cols) == 1:

        fig, ax = plt.subplots(figsize=(8,4))

        x_col = df.columns[0]
        y_col = numeric_cols[0]

        ax.bar(df[x_col].astype(str), df[y_col])

        ax.set_title(f"{y_col} berdasarkan {x_col}")

        plt.xticks(rotation=45)

        st.pyplot(fig)

# =====================================================
# PIPELINE
# =====================================================

def ask(question):

    sql = generate_sql(question)

    if not validate_sql(sql):

        sql = generate_sql(question)

        if not validate_sql(sql):
            raise Exception(
                "Gagal menghasilkan SQL yang valid"
            )

    df = run_sql(sql)

    return sql, df

# =====================================================
# CHAT HISTORY
# =====================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:

    with st.chat_message(m["role"]):

        st.write(m["content"])

        if "sql" in m:
            st.code(
                m["sql"],
                language="sql"
            )

        if "df" in m:
            st.dataframe(
                m["df"],
                use_container_width=True
            )

# =====================================================
# INPUT CHAT
# =====================================================

prompt = st.chat_input(
    "Tanyakan sesuatu tentang aset dan gangguan..."
)

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.write(prompt)

    try:

        with st.spinner("Menganalisis..."):

            sql, df = ask(prompt)

        with st.chat_message("assistant"):

            st.write("Berikut hasil analisis.")

            st.code(
                sql,
                language="sql"
            )

            st.dataframe(
                df,
                use_container_width=True
            )

            tampilkan_visual(df)

        st.session_state.messages.append({
            "role": "assistant",
            "content": "Berikut hasil analisis.",
            "sql": sql,
            "df": df
        })

    except Exception as e:

        with st.chat_message("assistant"):
            st.error(str(e))

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Error: {e}"
        })
```
