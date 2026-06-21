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
assets = pd.read_csv("assets.csv")
outages = pd.read_csv("outages.csv")

DATA = outages.merge(
    assets,
    on="asset_id",
    how="left"
)

# System prompt: persona + ATURAN + data (ramah saat disapa, akurat saat ditanya data)
SYSTEM_PROMPT = f"""
Anda adalah Asisten Analitik Aset dan Gangguan.

Skema data:

assets
- asset_id
- nama
- jenis
- lokasi

outages
- outage_id
- asset_id
- mulai
- selesai
- durasi_menit
- penyebab

Data gabungan:

{DATA.head(100).to_string(index=False)}

Aturan:
1. Jawab berdasarkan data yang tersedia.
2. Jika ditanya jumlah gangguan, gunakan data outage.
3. Jika ditanya rata-rata durasi pemulihan, gunakan durasi_menit.
4. Jika ditanya penyebab gangguan, gunakan kolom penyebab.
5. Jawab dalam Bahasa Indonesia.
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
        st.dataframe(DATA)

    elif jenis == "penyebab":
        st.bar_chart(
            DATA["penyebab"].value_counts()
        )

    elif jenis == "aset":
        st.bar_chart(
            DATA.groupby("nama")
                .size()
        )
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
        try:
            resp = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=temperature,
                ),
            )
            jawaban = resp.text

        except Exception as e:
            st.error(f"Gemini Error: {str(e)}")
            st.stop()

    p = prompt.lower()                                  # cek kata kunci untuk visual
    if "penyebab" in p:
        show = "penyebab"

    elif "aset" in p or "gardu" in p:
        show = "aset"

    elif any(k in p for k in ["tabel", "data"]):
        show = "table"
        
    else:
        show = None
    with st.chat_message("assistant"):
        st.write(jawaban)
        tampilkan_visual(show)

    st.session_state.messages.append({"role": "assistant", "content": jawaban, "show": show})
