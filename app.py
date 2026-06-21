# Import library utama Streamlit
import streamlit as st
# Import pandas untuk data tabel
import pandas as pd
# Import client Gemini
from google import genai
# Import 'types' untuk konfigurasi (system prompt, temperature)
from google.genai import types

# Judul & caption halaman
st.title("Chatbot Analitik PLN")
st.caption("Conversational Analytics - Streamlit Community Cloud")

# Data contoh (anggap hasil query database)
DATA = pd.DataFrame({
    "wilayah":      ["Jakarta", "Bandung", "Surabaya", "Medan", "Makassar"],  # wilayah
    "pelanggan":    [1200, 870, 1010, 640, 520],                              # jumlah pelanggan
    "konsumsi_mwh": [340, 250, 300, 180, 150],                               # konsumsi (MWh)
    "gangguan":     [12, 9, 14, 7, 5],                                       # jumlah gangguan
})

# System prompt: persona + ATURAN + data (ramah saat disapa, akurat saat ditanya data)
SYSTEM_PROMPT = f"""Anda adalah "Asisten Analitik PLN" yang ramah dan membantu.

ATURAN MENJAWAB:
1. Jika pengguna menyapa atau basa-basi (mis. "halo", "hai", "terima kasih", "siapa kamu"),
   balas ramah dan singkat. Boleh tawarkan 1-2 contoh pertanyaan tentang data.
2. Jika pengguna bertanya tentang data, jawab ringkas berdasarkan TABEL DATA di bawah,
   sebutkan satuan (MWh untuk konsumsi), lalu tutup dengan satu insight singkat.
3. Jika pertanyaan di luar cakupan data, katakan dengan sopan bahwa datanya tidak tersedia.
4. Jangan memaksakan analisis data pada sapaan/percakapan biasa.
5. Selalu jawab dalam Bahasa Indonesia.

TABEL DATA (konsumsi dalam MWh):

{DATA.to_string(index=False)}

"""

# Ambil API key dari Secrets Streamlit Community Cloud (Manage app -> Settings -> Secrets)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]              # baca dari panel Secrets
except Exception:
    api_key = ""                                        # kosong bila belum diset

# --- Sidebar: panel pengaturan (tanpa input API key) ---
with st.sidebar:
    st.subheader("Pengaturan")                          # judul kecil
    model = st.selectbox("Model", ["gemini-2.5-flash", "gemini-2.5-flash-lite"])  # pilih model
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.1)  # kreativitas jawaban
    st.caption("Tekan Reset untuk menghapus riwayat percakapan.")  # catatan kecil
    if st.button("Reset"):                              # tombol reset percakapan
        st.session_state.messages = []                  # kosongkan riwayat
        st.rerun()

# Hentikan bila API key belum diset di Secrets
if not api_key:
    st.error("GOOGLE_API_KEY belum diset di panel Secrets (Manage app -> Settings -> Secrets).")
    st.stop()

# Buat client Gemini SEKALI dan simpan di cache (mencegah error "client has been closed"
# yang muncul bila client dibuat ulang setiap kali Streamlit menjalankan ulang skrip).
@st.cache_resource
def get_client(key):
    return genai.Client(api_key=key)                    # objek koneksi ke Gemini
client = get_client(api_key)                            # ambil client dari cache

# Riwayat percakapan (disimpan agar bertahan antar-rerun)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Fungsi bantu: tampilkan tabel/grafik sesuai jenis
def tampilkan_visual(jenis):
    if jenis == "table":
        st.dataframe(DATA, use_container_width=True)
    elif jenis == "chart":
        st.bar_chart(DATA.set_index("wilayah")["konsumsi_mwh"])
    elif jenis == "gangguan":
        st.bar_chart(DATA.set_index("wilayah")["gangguan"])

# Gambar ulang riwayat percakapan
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        tampilkan_visual(m.get("show"))

# Kotak input chat
prompt = st.chat_input("Tanya tentang data...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})  # simpan pesan user
    with st.chat_message("user"):
        st.write(prompt)

    # Susun SELURUH riwayat menjadi 'contents' agar model punya MEMORI percakapan
    contents = []
    for h in st.session_state.messages:                 # untuk tiap pesan tersimpan
        peran = "user" if h["role"] == "user" else "model"   # peta peran ke format Gemini
        contents.append(types.Content(role=peran, parts=[types.Part(text=h["content"])]))

    # Panggil Gemini (client tetap hidup karena disimpan di cache)

    with st.spinner("Menganalisis..."):
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=temperature,
            ),
        )
        jawaban = resp.text

    p = prompt.lower()                                  # cek kata kunci untuk visual
    if "gangguan" in p:
        show = "gangguan"
    elif any(k in p for k in ["grafik", "chart"]):
        show = "chart"
    elif any(k in p for k in ["tabel", "data"]):
        show = "table"
    else:
        show = None
    with st.chat_message("assistant"):
        st.write(jawaban)
        tampilkan_visual(show)

    st.session_state.messages.append({"role": "assistant", "content": jawaban, "show": show})def get_client():
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
