
import streamlit as st
import pandas as pd
import sqlite3
from google import genai
from google.genai import types

# =====================================================
# LOAD DATA
# =====================================================

assets = pd.read_csv("assets.csv")
outages = pd.read_csv("outages.csv")

# =====================================================
# SQLITE IN-MEMORY
# =====================================================

@st.cache_resource
def get_connection():

    conn = sqlite3.connect(
        ":memory:",
        check_same_thread=False
    )

    assets.to_sql(
        "assets",
        conn,
        if_exists="replace",
        index=False
    )

    outages.to_sql(
        "outages",
        conn,
        if_exists="replace",
        index=False
    )

    return conn

conn = get_connection()

# =====================================================
# STREAMLIT UI
# =====================================================

st.title("Chatbot Analitik PLN")
st.caption("Conversational Analytics - Streamlit Community Cloud")

# =====================================================
# TODO 1 - KONFIGURASI LLM
# =====================================================

try:
    GEMINI_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    GEMINI_API_KEY = ""

if not GEMINI_API_KEY:
    st.error(
        "GOOGLE_API_KEY belum diset pada Streamlit Secrets."
    )
    st.stop()

MODEL_NAME = "gemini-2.5-flash"

@st.cache_resource
def get_client(api_key):
    return genai.Client(api_key=api_key)

client = get_client(GEMINI_API_KEY)

# =====================================================
# SCHEMA
# =====================================================

SCHEMA_STR = """
assets(
    asset_id,
    nama,
    jenis,
    lokasi
)

outages(
    outage_id,
    asset_id,
    mulai,
    selesai,
    durasi_menit,
    penyebab
)
"""

# =====================================================
# TODO 2 - BUILD PROMPT
# =====================================================

def build_prompt(question: str) -> str:

    prompt = f"""
Anda adalah generator SQL SQLite.

Schema:

{SCHEMA_STR}

Aturan:
- Hanya keluarkan SATU query SQL.
- Jangan gunakan markdown.
- Jangan beri penjelasan.
- Gunakan SELECT saja.
- Jika perlu gunakan JOIN.
- Gunakan nama tabel dan kolom sesuai schema.

Contoh:

Pertanyaan:
Jumlah gangguan per penyebab

SQL:
SELECT
    penyebab,
    COUNT(*) AS jumlah_gangguan
FROM outages
GROUP BY penyebab
ORDER BY jumlah_gangguan DESC;

Pertanyaan:
Rata-rata durasi gangguan per aset

SQL:
SELECT
    a.nama,
    AVG(o.durasi_menit) AS rata_rata_durasi
FROM outages o
JOIN assets a
ON o.asset_id = a.asset_id
GROUP BY a.nama
ORDER BY rata_rata_durasi DESC;

Pertanyaan:
{question}

SQL:
"""

    return prompt

# =====================================================
# TODO 3 - GENERATE SQL
# =====================================================

def generate_sql(question: str) -> str:

    prompt = build_prompt(question)

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0
        )
    )

    try:
        sql = resp.text
    except:
        sql = None

    if not sql:

        try:
            sql = resp.candidates[0].content.parts[0].text
        except:
            raise Exception(
                f"Gagal mengambil output Gemini.\nResponse: {resp}"
            )

    sql = sql.replace("```sql", "")
    sql = sql.replace("```", "")
    sql = sql.strip()

    return sql

# =====================================================
# TODO 4 - VALIDATE SQL
# =====================================================

FORBIDDEN = [
    "drop",
    "delete",
    "update",
    "insert",
    "alter",
    "truncate",
    "create",
    "grant"
]

def validate_sql(sql: str) -> bool:

    if not sql:
        return False

    sql_lower = sql.lower().strip()

    if not sql_lower.startswith("select"):
        return False

    for keyword in FORBIDDEN:
        if keyword in sql_lower:
            return False

    sql_no_last = sql.rstrip(";")

    if ";" in sql_no_last:
        return False

    return True

# =====================================================
# RUN SQL
# =====================================================

def run_sql(sql: str) -> pd.DataFrame:

    return pd.read_sql_query(
        sql,
        conn
    )

# =====================================================
# TODO 5 - VISUALIZE
# =====================================================

def visualize(df: pd.DataFrame):

    if df.empty:
        return

    if len(df.columns) != 2:
        return

    x_col = df.columns[0]
    y_col = df.columns[1]

    if not pd.api.types.is_numeric_dtype(df[y_col]):
        return

    try:

        if (
            "tanggal" in x_col.lower()
            or "bulan" in x_col.lower()
            or "date" in x_col.lower()
        ):
            st.line_chart(
                df.set_index(x_col)
            )

        else:
            st.bar_chart(
                df.set_index(x_col)
            )

    except:
        pass

# =====================================================
# TODO 6 - ASK PIPELINE
# =====================================================

def ask(question: str):

    sql = generate_sql(question)

    if not validate_sql(sql):

        sql = generate_sql(question)

        if not validate_sql(sql):

            return {
                "sql": None,
                "df": None,
                "error": "SQL yang dihasilkan tidak valid."
            }

    try:

        df = run_sql(sql)

        return {
            "sql": sql,
            "df": df,
            "error": None
        }

    except Exception as e:

        return {
            "sql": sql,
            "df": None,
            "error": str(e)
        }

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.subheader("Pengaturan")

    st.caption(
        "Tekan Reset untuk menghapus riwayat percakapan."
    )

    if st.button("Reset"):
        st.session_state.messages = []
        st.rerun()

# =====================================================
# SESSION STATE
# =====================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# =====================================================
# TAMPILKAN RIWAYAT
# =====================================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        if msg["role"] == "user":

            st.write(msg["content"])

        else:

            if msg.get("sql"):
                st.code(
                    msg["sql"],
                    language="sql"
                )

            if msg.get("df") is not None:
                st.dataframe(msg["df"])

            if msg.get("error"):
                st.error(msg["error"])

# =====================================================
# CHAT INPUT
# =====================================================

prompt = st.chat_input(
    "Tanyakan sesuatu tentang data..."
)

if prompt:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.write(prompt)

    with st.spinner("Menganalisis..."):

        result = ask(prompt)

    with st.chat_message("assistant"):

        if result["error"]:

            st.error(result["error"])

        else:

            st.code(
                result["sql"],
                language="sql"
            )

            st.dataframe(
                result["df"]
            )

            visualize(
                result["df"]
            )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "sql": result["sql"],
            "df": result["df"],
            "error": result["error"]
        }
    )
