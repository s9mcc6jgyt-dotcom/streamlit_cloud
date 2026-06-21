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

    st.session_state.messages.append({"role": "assistant", "content": jawaban, "show": show})    """
    # TODO 2: lengkapi prompt di bawah
    prompt = f"""
Anda adalah ahli PostgreSQL yang bertugas mengubah pertanyaan pengguna menjadi query SQL.

Skema database:

{SCHEMA_STR}

Aturan:
- HANYA keluarkan SATU query SQL PostgreSQL.
- Jangan berikan penjelasan, komentar, atau markdown.
- Query harus diawali dengan SELECT.
- Jangan gunakan INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, atau TRUNCATE.
- Gunakan hanya tabel dan kolom yang tersedia pada skema.
- Jika perlu menggabungkan tabel assets dan outages, gunakan:
  assets.asset_id = outages.asset_id

Contoh 1
Pertanyaan: Apa penyebab gangguan yang paling sering terjadi?
SQL:
SELECT penyebab, COUNT(*) AS jumlah
FROM outages
GROUP BY penyebab
ORDER BY jumlah DESC;

Contoh 2
Pertanyaan: Berapa rata-rata durasi pemulihan per jenis aset?
SQL:
SELECT a.jenis, AVG(o.durasi_menit) AS rata_rata_durasi
FROM outages o
JOIN assets a ON o.asset_id = a.asset_id
GROUP BY a.jenis
ORDER BY rata_rata_durasi DESC;

Pertanyaan: {question}
SQL:"""
    return prompt

def generate_sql(question: str) -> str:
    prompt = build_prompt(question)

    # TODO 3:
    #  1) panggil model -> resp = model.generate_content(prompt)
    #  2) ambil teksnya -> resp.text
    #  3) bersihkan: buang ```sql ... ``` bila ada, .strip()
    #  4) return string SQL

    resp = model.generate_content(prompt)

    sql = resp.text
    sql = sql.replace("```sql", "")
    sql = sql.replace("```", "")
    sql = sql.strip()

    return sql

FORBIDDEN = ["drop", "delete", "update", "insert", "alter", "truncate", "create", "grant"]

def validate_sql(sql: str) -> bool:
    """
    Kembalikan True hanya jika query AMAN untuk dijalankan:
    - tidak kosong
    - diawali SELECT (boleh setelah di-strip & lowercase)
    - tidak mengandung kata di FORBIDDEN
    - bukan multi-statement (tidak ada ';' di tengah)
    """
    # TODO 4: implementasikan pemeriksaan di atas

    if not sql:
        return False

    sql_clean = sql.strip().lower()

    if not sql_clean.startswith("select"):
        return False

    for word in FORBIDDEN:
        if word in sql_clean:
            return False

    if ";" in sql[:-1]:
        return False

    return True

def run_sql(sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)

def visualize(df: pd.DataFrame):
    """
    Buat grafik sederhana dari hasil query bila relevan.
    Contoh: bar chart jumlah gangguan per penyebab, atau rata-rata durasi per jenis aset.
    Aturan praktis:
    - 2 kolom (kategori, angka) -> bar chart
    - kolom waktu/bulan + angka  -> line chart
    - jika tidak cocok -> cukup tampilkan tabelnya saja
    """

    # TODO 5: deteksi bentuk df lalu plot dengan matplotlib (plt)

    if df.empty:
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    # Case 1: kategori + angka -> bar chart
    if len(df.columns) == 2 and len(numeric_cols) == 1:

        x_col = df.columns[0]
        y_col = numeric_cols[0]

        plt.figure(figsize=(8, 4))
        plt.bar(df[x_col].astype(str), df[y_col])
        plt.title(f"{y_col} berdasarkan {x_col}")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    # Case 2: waktu + angka -> line chart
    elif len(numeric_cols) == 1:

        x_col = df.columns[0]
        y_col = numeric_cols[0]

        if any(
            keyword in x_col.lower()
            for keyword in ["tanggal", "bulan", "mulai", "tgl", "date"]
        ):
            plt.figure(figsize=(8, 4))
            plt.plot(df[x_col], df[y_col], marker="o")
            plt.title(f"{y_col} terhadap {x_col}")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()

def ask(question: str):
    """
    Pipeline:
      1) sql = generate_sql(question)
      2) jika not validate_sql(sql): coba generate ulang 1x; jika masih gagal -> pesan fallback
      3) jalankan run_sql(sql) (bungkus try/except -> fallback bila error)
      4) tampilkan SQL, tabel hasil, dan visualize(df)
    """
    # TODO 6: implementasikan alur di atas dengan fallback/retry sederhana

    sql = generate_sql(question)

    if not validate_sql(sql):
        print("⚠️ SQL pertama tidak valid. Mencoba generate ulang...")

        sql = generate_sql(question)

        if not validate_sql(sql):
            print("❌ Gagal menghasilkan SQL yang valid.")
            return None

    print("\n=== SQL Generated ===")
    print(sql)

    try:
        df = run_sql(sql)

        print("\n=== Result ===")
        display(df)

        visualize(df)

        return df

    except Exception as e:
        print(f"❌ Error saat menjalankan SQL: {e}")
        return None

# =====================================================
# CHAT HISTORY
# =====================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.write(msg["content"])

        if "sql" in msg:
            st.code(msg["sql"], language="sql")

        if "df" in msg:
            st.dataframe(
                msg["df"],
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

            visualize(df)

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
