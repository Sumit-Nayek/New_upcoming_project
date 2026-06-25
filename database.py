import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = "data/spendwise.db"


import streamlit as st

@st.cache_resource
def get_connection():
    return sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )


def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        transactions_added INTEGER
    )
    """)

    conn.commit()
    conn.close()


def insert_transactions(df, source_file):
    if df.empty:
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for _, row in df.iterrows():
        try:
            cursor.execute("""
            INSERT INTO transactions
            (
                date,
                time,
                recipient,
                type,
                amount,
                category,
                transaction_id,
                utr_number,
                source_file
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("date"),
                row.get("time"),
                row.get("recipient"),
                row.get("type"),
                row.get("amount"),
                row.get("category"),
                row.get("transaction_id"),
                row.get("utr_number"),
                source_file
            ))

            inserted += 1

        except sqlite3.IntegrityError:
            pass

    cursor.execute("""
    INSERT INTO uploads(filename, transactions_added)
    VALUES (?, ?)
    """, (source_file, inserted))

    conn.commit()
    conn.close()

    return inserted


def load_transactions():
    conn = get_connection()

    df = pd.read_sql("""
    SELECT *
    FROM transactions
    ORDER BY date DESC
    """, conn)

    conn.close()
    return df
def get_total_transactions():
    conn = get_connection()

    count = pd.read_sql(
        "SELECT COUNT(*) AS cnt FROM transactions",
        conn
    ).iloc[0]["cnt"]

    conn.close()

    return int(count)
def get_total_spending():
    conn = get_connection()

    result = pd.read_sql("""
        SELECT
        COALESCE(
            SUM(amount),
            0
        ) AS total
        FROM transactions
        WHERE type='DEBIT'
    """, conn)

    conn.close()

    return float(result.iloc[0]["total"])
def get_total_income():
    conn = get_connection()

    result = pd.read_sql("""
        SELECT
        COALESCE(
            SUM(amount),
            0
        ) AS total
        FROM transactions
        WHERE type='CREDIT'
    """, conn)

    conn.close()

    return float(result.iloc[0]["total"])
def get_monthly_spending():
    conn = get_connection()

    df = pd.read_sql("""
    SELECT
        substr(date,1,8) AS month,
        SUM(amount) AS total
    FROM transactions
    WHERE type='DEBIT'
    GROUP BY month
    ORDER BY month
    """, conn)

    conn.close()

    return df