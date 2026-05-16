import os
import re
import sqlite3
import tempfile
from collections import defaultdict
from typing import List, Dict, Any, Tuple

import streamlit as st
import pandas as pd
import pdfplumber
import matplotlib.pyplot as plt
from transformers import pipeline

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance AI Dashboard",
    page_icon="💵",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────────────────────
# 1. DATABASE SETUP
# ──────────────────────────────────────────────────────────────────────────────
DB_PATH = "master_transactions.db"


def init_db():
    """Create the SQLite table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            date             TEXT,
            time             TEXT,
            recipient        TEXT,
            type             TEXT,
            amount           REAL,
            transaction_id   TEXT UNIQUE,
            utr_number       TEXT,
            source_file      TEXT,
            uploaded_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


def save_transactions(transactions: List[Dict], source_file: str) -> int:
    """Insert transactions, skipping duplicates based on transaction_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = 0
    for tx in transactions:
        try:
            cursor.execute("""
                INSERT INTO transactions
                    (date, time, recipient, type, amount, transaction_id, utr_number, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx.get("date"), tx.get("time"), tx.get("recipient"),
                tx.get("type"), tx.get("amount"), tx.get("transaction_id"),
                tx.get("utr_number"), source_file,
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            continue  # duplicate – skip
    conn.commit()
    conn.close()
    return inserted


def load_all_transactions() -> pd.DataFrame:
    """Return all transactions as a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
    conn.close()
    return df


# ──────────────────────────────────────────────────────────────────────────────
# 2. PDF EXTRACTION
# ──────────────────────────────────────────────────────────────────────────────
def extract_transactions_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Extract transactions from a PhonePe / Paytm / bank statement PDF.
    Returns a list of dicts: date, time, recipient, type, amount,
    transaction_id, utr_number.
    """
    transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                # Primary pattern: "01 Apr 2025  10:30  Swiggy  Debit  450.00  T123456"
                pattern = (
                    r"(\d{1,2}\s\w{3}\s\d{4})\s+"
                    r"(\d{2}:\d{2})\s+"
                    r"([A-Za-z0-9\s]+?)\s+"
                    r"(Debit|Credit|Paid|Received)\s+"
                    r"([\d,]+\.?\d*)\s+"
                    r"([A-Z0-9]+)"
                )
                match = re.search(pattern, line)
                if match:
                    date, time, recipient, tx_type, amount_str, tx_id = match.groups()
                    amount = float(amount_str.replace(",", ""))
                    transactions.append({
                        "date": date,
                        "time": time,
                        "recipient": recipient.strip(),
                        "type": tx_type,
                        "amount": amount if tx_type in ("Debit", "Paid") else -amount,
                        "transaction_id": tx_id,
                        "utr_number": None,
                    })
                elif "Debit" in line or "Credit" in line:
                    # Fallback: heuristic split
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            amount = float(parts[-2].replace(",", ""))
                            transactions.append({
                                "date": parts[0] if len(parts[0]) > 5 else None,
                                "time": None,
                                "recipient": " ".join(parts[1:-3]),
                                "type": "Debit" if "Debit" in line else "Credit",
                                "amount": amount,
                                "transaction_id": parts[-1],
                                "utr_number": None,
                            })
                        except ValueError:
                            pass
    return transactions


# ──────────────────────────────────────────────────────────────────────────────
# 3. ANALYTICS ENGINE
# ──────────────────────────────────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "Food":          ["swiggy", "zomato", "pizza", "restaurant", "starbucks", "dominos"],
    "Shopping":      ["amazon", "flipkart", "myntra", "ajio", "mall", "nykaa"],
    "Recharge":      ["jio", "airtel", "vi", "recharge", "mobile", "internet"],
    "Bills":         ["electricity", "water", "gas", "broadband", "rent"],
    "Travel":        ["uber", "ola", "metro", "railway", "flight", "bus"],
    "Entertainment": ["netflix", "prime", "hotstar", "bookmyshow", "spotify"],
}


def compute_analytics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute key metrics, category breakdown, and daily spending."""
    if df.empty:
        return {
            "total_spent": 0, "transaction_count": 0, "avg_daily": 0,
            "top_categories": {}, "top_recipients": {}, "daily_spending": {},
        }

    df = df.copy()
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_dt"])

    spending = df[df["type"].str.lower().isin(["debit", "paid"])]

    total_spent = spending["amount"].sum()
    transaction_count = len(spending)

    if transaction_count > 0:
        days_range = (spending["date_dt"].max() - spending["date_dt"].min()).days
        avg_daily = total_spent / max(days_range, 1)
    else:
        avg_daily = 0.0

    category_spend: Dict[str, float] = defaultdict(float)
    for _, row in spending.iterrows():
        recipient = row["recipient"].lower()
        assigned = False
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in recipient for kw in keywords):
                category_spend[cat] += row["amount"]
                assigned = True
                break
        if not assigned:
            category_spend["Other"] += row["amount"]

    top_recipients = (
        spending.groupby("recipient")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .to_dict()
    )

    daily_spending = (
        spending.groupby("date_dt")["amount"].sum().to_dict()
    )

    return {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "avg_daily": avg_daily,
        "top_categories": dict(category_spend),
        "top_recipients": top_recipients,
        "daily_spending": daily_spending,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 4. VISUALIZATIONS
# ──────────────────────────────────────────────────────────────────────────────
def make_trend_chart(analytics: Dict) -> plt.Figure:
    daily = analytics["daily_spending"]
    fig, ax = plt.subplots(figsize=(10, 4))
    if daily:
        dates  = list(daily.keys())
        amounts = list(daily.values())
        ax.plot(dates, amounts, marker="o", linestyle="-", color="#1f77b4")
        ax.set_title("Daily Spending Trend", fontsize=14)
        ax.set_xlabel("Date")
        ax.set_ylabel("Amount (₹)")
        plt.xticks(rotation=45)
    else:
        ax.text(0.5, 0.5, "Not enough data", ha="center", va="center")
    plt.tight_layout()
    return fig


def make_pie_chart(analytics: Dict) -> plt.Figure:
    categories = analytics["top_categories"]
    fig, ax = plt.subplots(figsize=(6, 6))
    if categories:
        ax.pie(
            categories.values(),
            labels=categories.keys(),
            autopct="%1.1f%%",
            startangle=90,
        )
        ax.set_title("Spending by Category")
        ax.axis("equal")
    else:
        ax.text(0.5, 0.5, "No categories", ha="center", va="center")
    return fig


def make_bar_chart(analytics: Dict) -> plt.Figure:
    recipients = analytics["top_recipients"]
    fig, ax = plt.subplots(figsize=(8, 4))
    if recipients:
        names   = list(recipients.keys())
        amounts = list(recipients.values())
        ax.barh(names, amounts, color="#ff7f0e")
        ax.set_title("Top 5 Recipients by Spending")
        ax.set_xlabel("Amount (₹)")
        ax.invert_yaxis()
    else:
        ax.text(0.5, 0.5, "No recipients", ha="center", va="center")
    plt.tight_layout()
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# 5. AI SUMMARY  (cached so the model loads only once)
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading AI model…")
def load_summarizer():
    try:
        return pipeline("summarization", model="Falconsai/text_summarization")
    except Exception as e:
        st.warning(f"Could not load summarizer: {e}")
        return None


def generate_ai_summary(analytics: Dict) -> str:
    if analytics["transaction_count"] == 0:
        return "No transactions found. Upload a PDF to see your financial summary."

    total   = analytics["total_spent"]
    count   = analytics["transaction_count"]
    avg     = analytics["avg_daily"]
    top_cats  = analytics["top_categories"]
    top_recip = analytics["top_recipients"]

    sorted_cats = sorted(top_cats.items(), key=lambda x: x[1], reverse=True)
    cat_text = (
        f"Top spending categories: {', '.join(c[0] for c in sorted_cats[:3])}."
        if sorted_cats else ""
    )
    rec_text = (
        f"Highest payment was to {list(top_recip.keys())[0]}."
        if top_recip else ""
    )

    prompt = (
        f"In the last period, you spent ₹{total:,.2f} across {count} transactions. "
        f"Average daily spend: ₹{avg:,.2f}. {cat_text} {rec_text}"
    )

    summarizer = load_summarizer()
    if summarizer:
        try:
            result = summarizer(prompt, max_length=100, min_length=20, do_sample=False)
            return result[0]["summary_text"]
        except Exception:
            pass
    return prompt


# ──────────────────────────────────────────────────────────────────────────────
# 6. STREAMLIT UI
# ──────────────────────────────────────────────────────────────────────────────
st.title("💵 Financial Transaction Analyzer")
st.markdown(
    "Upload your **PhonePe**, **Paytm**, or **bank statement** PDF. "
    "The app extracts transactions, stores them in a local database, "
    "and shows AI-powered insights."
)

uploaded_file = st.file_uploader("Upload PDF Statement", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("Processing PDF…"):
        # Write to a temp file so pdfplumber can open it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        try:
            transactions = extract_transactions_from_pdf(tmp_path)
        finally:
            os.unlink(tmp_path)

    if not transactions:
        st.error("No transactions found in the PDF. Please check the file format.")
        st.stop()

    inserted = save_transactions(transactions, source_file=uploaded_file.name)
    st.success(f"✅ Extracted **{len(transactions)}** transactions — **{inserted}** new records saved.")

    df        = load_all_transactions()
    analytics = compute_analytics(df)

    # ── Metric Cards ──────────────────────────────────────────────────────────
    st.subheader("📊 Financial Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Spent",      f"₹{analytics['total_spent']:,.2f}")
    col2.metric("🧾 Transactions",      analytics["transaction_count"])
    col3.metric("📅 Avg Daily Spend",   f"₹{analytics['avg_daily']:,.2f}")

    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────────
    st.subheader("📈 Spending Trend")
    st.pyplot(make_trend_chart(analytics), use_container_width=True)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("🍕 Spending by Category")
        st.pyplot(make_pie_chart(analytics))
    with chart_col2:
        st.subheader("🏆 Top Recipients")
        st.pyplot(make_bar_chart(analytics))

    st.divider()

    # ── AI Summary ────────────────────────────────────────────────────────────
    st.subheader("🤖 AI-Generated Summary")
    with st.spinner("Generating summary…"):
        summary = generate_ai_summary(analytics)
    st.info(summary)

    st.divider()

    # ── Raw Data Table ────────────────────────────────────────────────────────
    with st.expander("🗃️ View All Transactions"):
        st.dataframe(df, use_container_width=True)

else:
    st.info("👆 Upload a PDF statement above to get started.")