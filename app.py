import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from google import genai
from google.genai import types

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Chatbot Analitik PLN",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Chatbot Analitik PLN")
st.caption("Conversational Analytics dengan Gemini + PostgreSQL")

# =====================================================
# CONFIG
# =====================================================

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    POSTGRES_URI = st.secrets["POSTGRES_URI"]
except Exception:
    st.error("Secrets belum lengkap.")
    st.stop()

# =====================================================
# GEMINI CLIENT
# TODO 1
# =====================================================

@st.cache_resource
def get_client():
    return genai.Client(api_key=GOOGLE_API_KEY)

client = get_client()

# =====================================================
# DATABASE CONNECTION
# =====================================================

@st.cache_resource
def get_engine():
    return create_engine(POSTGRES_URI)

engine = get_engine()

# =====================================================
# SCHEMA
# TODO 2
# =====================================================

SCHEMA_STR = """
Table assets
-------------
asset_id
asset_name
asset_type
region

Table outages
-------------
outage_id
asset_id
outage_start
outage_end
duration_minutes
cause
"""

# =====================================================
# BUILD PROMPT
# TODO 2
# =====================================================

def build_prompt(question):

    return f"""
Anda adalah PostgreSQL SQL Generator.

Database Schema:

{SCHEMA_STR}

ATURAN:
1. Hanya keluarkan SQL.
2. Jangan gunakan markdown.
3. Jangan gunakan ```sql.
4. Hanya query SELECT.
5. Jangan gunakan INSERT, UPDATE, DELETE, DROP.
6. Gunakan PostgreSQL syntax.

Pertanyaan:
{question}
"""

# =====================================================
# GENERATE SQL
# TODO 3
# =====================================================

def generate_sql(question):

    prompt = build_prompt(question)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    sql = response.text.strip()

    sql = sql.replace("```sql", "")
    sql = sql.replace("```", "")
    sql = sql.strip()

    return sql

# =====================================================
# VALIDATE SQL
# TODO 4
# =====================================================

FORBIDDEN_KEYWORDS = [
    "insert",
    "update",
    "delete",
    "drop",
    "truncate",
    "alter",
    "create"
]

def validate_sql(sql):

    lower_sql = sql.lower()

    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in lower_sql:
            return False

    if not lower_sql.startswith("select"):
        return False

    return True

# =====================================================
# EXECUTE SQL
# TODO 5
# =====================================================

def run_sql(sql):

    try:
        with engine.connect() as conn:
            df = pd.read_sql(sql, conn)

        return df

    except Exception as e:
        raise Exception(f"SQL Error: {str(e)}")

# =====================================================
# GENERATE INSIGHT
# TODO 6
# =====================================================

def generate_insight(question, df):

    if df.empty:
        return "Tidak ditemukan data."

    sample = df.head(20).to_string(index=False)

    prompt = f"""
Anda adalah analis data PLN.

Pertanyaan:
{question}

Hasil Query:
{sample}

Berikan:
1. Ringkasan hasil.
2. Insight utama.
3. Maksimum 5 kalimat.
4. Bahasa Indonesia.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text

# =====================================================
# VISUALIZATION
# TODO 7
# =====================================================

def visualize(df):

    if len(df) == 0:
        return

    numeric_cols = list(
        df.select_dtypes(include="number").columns
    )

    if len(df.columns) == 2 and len(numeric_cols) == 1:

        idx_col = df.columns[0]

        st.bar_chart(
            df.set_index(idx_col)
        )

# =====================================================
# MAIN PIPELINE
# =====================================================

def ask(question):

    sql = generate_sql(question)

    if not validate_sql(sql):
        raise Exception(
            "SQL tidak valid atau mengandung perintah terlarang."
        )

    df = run_sql(sql)

    insight = generate_insight(
        question,
        df
    )

    return sql, df, insight

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.subheader("Pengaturan")

    show_sql = st.checkbox(
        "Tampilkan SQL",
        value=True
    )

    if st.button("Reset Percakapan"):
        st.session_state.messages = []
        st.rerun()

# =====================================================
# CHAT MEMORY
# TODO 8
# =====================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# =====================================================
# RENDER HISTORY
# =====================================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.write(msg["content"])

        if "sql" in msg:

            with st.expander("SQL"):
                st.code(
                    msg["sql"],
                    language="sql"
                )

        if "df" in msg:

            st.dataframe(
                msg["df"],
                use_container_width=True
            )

            visualize(msg["df"])

# =====================================================
# CHAT INPUT
# =====================================================

question = st.chat_input(
    "Tanyakan sesuatu tentang data..."
)

if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):

        try:

            with st.spinner("Menganalisis data..."):

                sql, df, insight = ask(question)

            st.write(insight)

            if show_sql:
                with st.expander("SQL"):
                    st.code(
                        sql,
                        language="sql"
                    )

            st.dataframe(
                df,
                use_container_width=True
            )

            visualize(df)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": insight,
                    "sql": sql,
                    "df": df
                }
            )

        except Exception as e:

            error_msg = str(e)

            st.error(error_msg)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_msg
                }
            )
