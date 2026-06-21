
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# CHATBOT ASET DAN GANGGUAN
# =====================================================

st.title("⚡ Chatbot Aset dan Gangguan")
st.caption("Conversational Analytics - Use Case C")

with st.sidebar:
    st.subheader("Contoh Pertanyaan")

    st.markdown("""
    - Berapa jumlah gangguan per aset?
    - Berapa rata-rata durasi pemulihan per jenis aset?
    - Apa penyebab gangguan yang paling sering terjadi?
    """)

    if st.button("Reset Percakapan"):
        st.session_state.messages = []
        st.rerun()

# =====================================================
# FUNGSI PIPELINE 
# =====================================================

def build_prompt(question: str) -> str:
    """
    Susun prompt yang berisi:
    - skema database (SCHEMA_STR) agar LLM tahu nama tabel & kolom
    - instruksi tegas: HANYA balas SATU query PostgreSQL SELECT, tanpa penjelasan
    - pertanyaan pengguna
    Boleh tambahkan 1-2 contoh (few-shot) bila perlu.
    """
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
