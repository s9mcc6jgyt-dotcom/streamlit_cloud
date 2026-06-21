import re
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import text
from google import genai
from google.genai import types

# =====================================================
# CONFIG
# =====================================================

GEMINI_API_KEY = "ISI_API_KEY"
MODEL_NAME = "gemini-2.5-flash"

client = genai.Client(api_key=GEMINI_API_KEY)

# =====================================================
# SCHEMA
# =====================================================

SCHEMA_STR = """
Table assets
- asset_id
- nama
- jenis
- lokasi

Table outages
- outage_id
- asset_id
- mulai
- selesai
- durasi_menit
- penyebab
"""

# =====================================================
# PROMPT BUILDER
# =====================================================

def build_prompt(question: str) -> str:

    prompt = f"""
Anda adalah generator SQL PostgreSQL.

Schema database:

{SCHEMA_STR}

Aturan:
1. Hanya buat query PostgreSQL.
2. Hanya boleh SELECT.
3. Jangan gunakan INSERT, UPDATE, DELETE, DROP, ALTER, CREATE.
4. Jangan berikan penjelasan.
5. Jangan gunakan markdown.
6. Kembalikan satu query SQL saja.

Pertanyaan:
{question}

SQL:
"""

    return prompt

# =====================================================
# GENERATE SQL
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

    sql = resp.text.strip()

    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```", "", sql)
    sql = sql.strip()

    return sql

# =====================================================
# VALIDATE SQL
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

    cleaned = sql.strip().lower()

    if not cleaned.startswith("select"):
        return False

    for word in FORBIDDEN:
        if word in cleaned:
            return False

    statements = [
        s.strip()
        for s in sql.split(";")
        if s.strip()
    ]

    if len(statements) > 1:
        return False

    return True

# =====================================================
# RUN SQL
# =====================================================

def run_sql(sql: str):

    with engine.connect() as conn:
        df = pd.read_sql(
            text(sql),
            conn
        )

    return df

# =====================================================
# VISUALIZE
# =====================================================

def visualize(df: pd.DataFrame):

    if df.empty:
        print("Tidak ada data.")
        return

    if len(df.columns) != 2:
        print(df)
        return

    col1 = df.columns[0]
    col2 = df.columns[1]

    if pd.api.types.is_numeric_dtype(df[col2]):

        plt.figure(figsize=(8,4))

        if (
            "tanggal" in col1.lower()
            or "bulan" in col1.lower()
            or pd.api.types.is_datetime64_any_dtype(df[col1])
        ):
            plt.plot(df[col1], df[col2])
        else:
            plt.bar(df[col1], df[col2])

        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    else:
        print(df)

# =====================================================
# ASK PIPELINE
# =====================================================

def ask(question: str):

    sql = generate_sql(question)

    if not validate_sql(sql):

        print("SQL pertama tidak valid. Regenerate...")

        sql = generate_sql(question)

        if not validate_sql(sql):
            print("Gagal menghasilkan SQL yang aman.")
            return

    print("\nSQL:")
    print(sql)

    try:

        df = run_sql(sql)

        print("\nHASIL:")
        print(df.head())

        visualize(df)

    except Exception as e:

        print("Error eksekusi SQL:")
        print(str(e))

# =====================================================
# EXAMPLE
# =====================================================

ask("Berapa jumlah gangguan berdasarkan penyebab?")
