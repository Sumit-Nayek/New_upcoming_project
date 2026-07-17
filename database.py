import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


@st.cache_resource
def get_connection():
    cfg = st.secrets["postgres"]
    url = (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    )
    return create_engine(url, pool_pre_ping=True)


def initialize_db():
    engine = get_connection()
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            date TEXT,
            time TEXT,
            recipient TEXT,
            type TEXT,
            amount REAL,
            category TEXT,
            transaction_id TEXT UNIQUE,
            utr_number TEXT,
            source_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS uploads (
            id SERIAL PRIMARY KEY,
            filename TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transactions_added INTEGER
        )
        """))


def insert_transactions(df, source_file):
    if df.empty:
        return 0

    engine = get_connection()
    inserted = 0

    with engine.begin() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(text("""
                INSERT INTO transactions
                (date, time, recipient, type, amount, category, transaction_id, utr_number, source_file)
                VALUES (:date, :time, :recipient, :type, :amount, :category, :transaction_id, :utr_number, :source_file)
                """), {
                    "date": row.get("date"),
                    "time": row.get("time"),
                    "recipient": row.get("recipient"),
                    "type": row.get("type"),
                    "amount": row.get("amount"),
                    "category": row.get("category"),
                    "transaction_id": row.get("transaction_id"),
                    "utr_number": row.get("utr_number"),
                    "source_file": source_file
                })
                inserted += 1
            except Exception:
                pass  # duplicate transaction_id -> UNIQUE constraint violation, skip

        conn.execute(text("""
        INSERT INTO uploads(filename, transactions_added)
        VALUES (:filename, :inserted)
        """), {"filename": source_file, "inserted": inserted})

    return inserted


def load_transactions():
    engine = get_connection()
    return pd.read_sql("SELECT * FROM transactions ORDER BY date DESC", engine)


def get_total_transactions():
    engine = get_connection()
    count = pd.read_sql("SELECT COUNT(*) AS cnt FROM transactions", engine).iloc[0]["cnt"]
    return int(count)


def get_total_spending():
    engine = get_connection()
    result = pd.read_sql("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM transactions WHERE type='DEBIT'
    """, engine)
    return float(result.iloc[0]["total"])


def get_total_income():
    engine = get_connection()
    result = pd.read_sql("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM transactions WHERE type='CREDIT'
    """, engine)
    return float(result.iloc[0]["total"])


def get_monthly_spending():
    engine = get_connection()
    return pd.read_sql("""
        SELECT substr(date,1,8) AS month, SUM(amount) AS total
        FROM transactions WHERE type='DEBIT'
        GROUP BY month ORDER BY month
    """, engine)
