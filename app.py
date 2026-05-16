# import os
# import re
# import sqlite3
# import tempfile
# import warnings
# from collections import defaultdict
# from datetime import datetime
# from typing import List, Dict, Any, Optional

# import streamlit as st
# import pandas as pd
# import pdfplumber
# import matplotlib.pyplot as plt
# from transformers import pipeline

# warnings.filterwarnings("ignore")

# # ──────────────────────────────────────────────────────────────────────────────
# # PAGE CONFIG
# # ──────────────────────────────────────────────────────────────────────────────
# st.set_page_config(
#     page_title="Finance AI Dashboard",
#     page_icon="💵",
#     layout="wide",
# )

# # ──────────────────────────────────────────────────────────────────────────────
# # 1. DATABASE SETUP
# # ──────────────────────────────────────────────────────────────────────────────
# DB_PATH = "master_transactions.db"


# def init_db():
#     conn = sqlite3.connect(DB_PATH)
#     # NOTE: transaction_id is NOT UNIQUE — PhonePe PDFs frequently yield
#     # NULL ids (multi-line layout). Deduplication is done via explicit SELECT.
#     conn.execute("""
#         CREATE TABLE IF NOT EXISTS transactions (
#             id             INTEGER PRIMARY KEY AUTOINCREMENT,
#             date           TEXT,
#             time           TEXT,
#             recipient      TEXT,
#             type           TEXT,
#             amount         REAL,
#             transaction_id TEXT,
#             utr_number     TEXT,
#             source_file    TEXT,
#             uploaded_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     """)
#     conn.commit()
#     conn.close()


# init_db()


# def save_transactions(transactions: List[Dict], source_file: str) -> int:
#     """Insert transactions; skip only when a non-null transaction_id already exists."""
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     inserted = 0
#     for tx in transactions:
#         tx_id = tx.get("transaction_id")
#         if tx_id:                                           # dedup by real ID only
#             cursor.execute(
#                 "SELECT 1 FROM transactions WHERE transaction_id = ?", (tx_id,)
#             )
#             if cursor.fetchone():
#                 continue
#         cursor.execute("""
#             INSERT INTO transactions
#                 (date, time, recipient, type, amount, transaction_id, utr_number, source_file)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """, (
#             tx.get("date"), tx.get("time"), tx.get("recipient"),
#             tx.get("type"), tx.get("amount"), tx_id,
#             tx.get("utr_number"), source_file,
#         ))
#         inserted += 1
#     conn.commit()
#     conn.close()
#     return inserted


# def load_all_transactions() -> pd.DataFrame:
#     conn = sqlite3.connect(DB_PATH)
#     df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
#     conn.close()
#     return df


# def clear_all_transactions():
#     conn = sqlite3.connect(DB_PATH)
#     conn.execute("DELETE FROM transactions")
#     conn.commit()
#     conn.close()


# # ──────────────────────────────────────────────────────────────────────────────
# # 2. PDF EXTRACTION  — multi-line aware TransactionExtractor
# # ──────────────────────────────────────────────────────────────────────────────
# class TransactionExtractor:
#     """
#     Parses PhonePe / Paytm / bank-statement PDFs where each transaction
#     is spread across 3-5 consecutive lines:

#         Line 1 : "Feb 13, 2026"            ← date anchor
#         Line 2 : "3:45 pm"
#         Line 3 : "Paid to Swiggy  DEBIT  ₹450.00"
#         Line 4 : "Transaction ID 4567ABCD  UTR No. 98765"

#     The old single-line regex in app.py matched nothing on real statements.
#     This class finds the date line as an anchor and merges the next N lines
#     into a single block for field extraction.
#     """

#     DATE_PATTERNS = [
#         r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}",   # Feb 13, 2026
#         r"\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}",    # 13 Feb 2026
#         r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",      # 13/02/2026  or  13-02-26
#     ]

#     def __init__(self, pdf_path: str):
#         self.pdf_path = pdf_path
#         self.transactions: List[Dict] = []

#     # ── public entry point ────────────────────────────────────────────────────
#     def extract_transactions(self) -> pd.DataFrame:
#         try:
#             with pdfplumber.open(self.pdf_path) as pdf:
#                 for page_num, page in enumerate(pdf.pages, 1):
#                     text = page.extract_text()
#                     if not text:
#                         continue
#                     lines = [l.strip() for l in text.split("\n") if l.strip()]
#                     self.transactions.extend(self._process_page(lines, page_num))
#         except Exception as e:
#             st.error(f"PDF read error: {e}")

#         return self._to_dataframe()

#     # ── page processing ───────────────────────────────────────────────────────
#     def _process_page(self, lines: List[str], page_num: int) -> List[Dict]:
#         results, i = [], 0
#         while i < len(lines):
#             if self._is_date_line(lines[i]):
#                 txn = self._parse_block(lines, i, page_num)
#                 if txn:
#                     results.append(txn)
#                 i += 4          # skip the consumed block (approx)
#             else:
#                 i += 1
#         return results

#     def _parse_block(self, lines: List[str], start: int, page_num: int) -> Optional[Dict]:
#         """Merge up to 5 lines starting at `start` and extract all fields."""
#         try:
#             block_lines = lines[start: start + 5]
#             full = " ".join(block_lines)

#             txn: Dict = {"page_number": page_num}

#             # date
#             txn.update(self._parse_date(block_lines[0]))

#             # time — search all lines
#             for ln in block_lines:
#                 m = re.search(r"(\d{1,2}:\d{2}\s*[ap]m)", ln, re.IGNORECASE)
#                 if m:
#                     txn["time"] = m.group(1)
#                     break

#             # transaction type
#             if re.search(r"\bDEBIT\b|\bPaid to\b", full, re.IGNORECASE):
#                 txn["type"] = "DEBIT"
#             elif re.search(r"\bCREDIT\b|\bReceived from\b", full, re.IGNORECASE):
#                 txn["type"] = "CREDIT"

#             # recipient
#             for pat in [
#                 r"Paid to\s+(.+?)(?:\s+DEBIT|\s+CREDIT|\s+₹|\s+Rs\.?|$)",
#                 r"Received from\s+(.+?)(?:\s+DEBIT|\s+CREDIT|\s+₹|\s+Rs\.?|$)",
#             ]:
#                 m = re.search(pat, full, re.IGNORECASE)
#                 if m:
#                     txn["recipient"] = m.group(1).strip()
#                     break

#             # amount — ₹ symbol or Rs. prefix, or number after DEBIT/CREDIT keyword
#             amt_m = re.search(r"(?:₹|Rs\.?)\s*([\d,]+\.?\d*)", full) \
#                     or re.search(r"(?:DEBIT|CREDIT)\s+([\d,]+\.?\d*)", full, re.IGNORECASE)
#             if amt_m:
#                 amt = float(amt_m.group(1).replace(",", ""))
#                 txn["amount"] = amt if txn.get("type") == "DEBIT" else -amt

#             # transaction ID
#             m = re.search(r"Transaction\s+ID\s+(\S+)", full, re.IGNORECASE)
#             if m:
#                 txn["transaction_id"] = m.group(1)

#             # UTR
#             m = re.search(r"UTR\s*No\.?\s*(\S+)", full, re.IGNORECASE)
#             if m:
#                 txn["utr_number"] = m.group(1)

#             # require at minimum a date and amount
#             if "date" not in txn or "amount" not in txn:
#                 return None

#             return txn

#         except Exception:
#             return None

#     # ── helpers ───────────────────────────────────────────────────────────────
#     def _is_date_line(self, line: str) -> bool:
#         return any(re.search(p, line) for p in self.DATE_PATTERNS)

#     def _parse_date(self, line: str) -> Dict:
#         result: Dict = {}
#         candidates = [
#             ("%b %d, %Y", r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})"),
#             ("%d %b %Y",  r"(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})"),
#             ("%d/%m/%Y",  r"(\d{1,2}/\d{1,2}/\d{4})"),
#             ("%d-%m-%Y",  r"(\d{1,2}-\d{1,2}-\d{4})"),
#         ]
#         for fmt, pat in candidates:
#             m = re.search(pat, line)
#             if m:
#                 result["date"] = m.group(1)
#                 try:
#                     result["parsed_date"] = datetime.strptime(m.group(1), fmt)
#                 except ValueError:
#                     pass
#                 break
#         return result

#     def _to_dataframe(self) -> pd.DataFrame:
#         if not self.transactions:
#             return pd.DataFrame()
#         tmp = pd.DataFrame(self.transactions)
#         display_cols = ["date", "time", "recipient", "type", "amount",
#                         "transaction_id", "utr_number"]
#         available = [c for c in display_cols if c in tmp.columns]
#         df = tmp[available].copy()
#         if "parsed_date" in tmp.columns:
#             df = df.copy()
#             df["_sort"] = tmp["parsed_date"]
#             df = df.sort_values("_sort").drop(columns=["_sort"])
#         return df.reset_index(drop=True)


# def extract_transactions_from_pdf(pdf_path: str) -> List[Dict]:
#     """Thin wrapper — returns list of dicts for the Streamlit layer."""
#     extractor = TransactionExtractor(pdf_path)
#     df = extractor.extract_transactions()
#     return [] if df.empty else df.to_dict(orient="records")


# # ──────────────────────────────────────────────────────────────────────────────
# # 3. ANALYTICS ENGINE
# # ──────────────────────────────────────────────────────────────────────────────
# CATEGORY_KEYWORDS: Dict[str, List[str]] = {
#     "Food":          ["swiggy", "zomato", "pizza", "restaurant", "starbucks", "dominos"],
#     "Shopping":      ["amazon", "flipkart", "myntra", "ajio", "mall", "nykaa"],
#     "Recharge":      ["jio", "airtel", "vi", "recharge", "mobile", "internet"],
#     "Bills":         ["electricity", "water", "gas", "broadband", "rent"],
#     "Travel":        ["uber", "ola", "metro", "railway", "flight", "bus"],
#     "Entertainment": ["netflix", "prime", "hotstar", "bookmyshow", "spotify"],
# }

# _EMPTY_ANALYTICS: Dict[str, Any] = {
#     "total_spent": 0, "total_credited": 0,
#     "transaction_count": 0, "avg_daily": 0,
#     "top_categories": {}, "top_recipients": {}, "daily_spending": {},
# }


# def compute_analytics(df: pd.DataFrame) -> Dict[str, Any]:
#     if df.empty:
#         return _EMPTY_ANALYTICS.copy()

#     df = df.copy()
#     df["date_dt"]  = pd.to_datetime(df["date"], errors="coerce")
#     df             = df.dropna(subset=["date_dt"])
#     # FIX: NaN recipient causes AttributeError in .lower()
#     df["recipient"] = df["recipient"].fillna("Unknown")

#     if df.empty:
#         return _EMPTY_ANALYTICS.copy()

#     spending  = df[df["type"].str.upper().isin(["DEBIT",  "PAID"])]
#     receiving = df[df["type"].str.upper().isin(["CREDIT", "RECEIVED"])]

#     total_spent    = spending["amount"].sum()
#     total_credited = receiving["amount"].abs().sum()
#     count          = len(spending)

#     # FIX: same-day edge case (days_range=0) — max(...,1) prevents /0
#     if count > 0:
#         days_range = (spending["date_dt"].max() - spending["date_dt"].min()).days
#         avg_daily  = total_spent / max(days_range, 1)
#     else:
#         avg_daily = 0.0

#     category_spend: Dict[str, float] = defaultdict(float)
#     for _, row in spending.iterrows():
#         recip    = str(row["recipient"]).lower()
#         assigned = False
#         for cat, kws in CATEGORY_KEYWORDS.items():
#             if any(kw in recip for kw in kws):
#                 category_spend[cat] += row["amount"]
#                 assigned = True
#                 break
#         if not assigned:
#             category_spend["Other"] += row["amount"]

#     top_recipients = (
#         spending.groupby("recipient")["amount"]
#         .sum().sort_values(ascending=False).head(5).to_dict()
#     )
#     daily_spending = spending.groupby("date_dt")["amount"].sum().to_dict()

#     return {
#         "total_spent":       total_spent,
#         "total_credited":    total_credited,
#         "transaction_count": count,
#         "avg_daily":         avg_daily,
#         "top_categories":    dict(category_spend),
#         "top_recipients":    top_recipients,
#         "daily_spending":    daily_spending,
#     }


# # ──────────────────────────────────────────────────────────────────────────────
# # 3b. WEEKLY RECIPIENT SUMMARY
# # ──────────────────────────────────────────────────────────────────────────────
# def weekly_recipient_summary(df: pd.DataFrame) -> pd.DataFrame:
#     """Groups by ISO week + recipient; counts occurrences and sums amount."""
#     if df.empty:
#         return pd.DataFrame()

#     work = df.copy()
#     work["date_dt"]  = pd.to_datetime(work.get("date", pd.Series(dtype=str)), errors="coerce")
#     work["recipient"] = work.get("recipient", pd.Series(dtype=str)).fillna("Unknown")
#     work = work.dropna(subset=["date_dt"])
#     if work.empty:
#         return pd.DataFrame()

#     work["week_start"] = work["date_dt"].dt.to_period("W").dt.start_time
#     grouped = (
#         work.groupby(["week_start", "recipient"])
#         .agg(occurrence_count=("recipient", "count"), total_amount=("amount", "sum"))
#         .reset_index()
#         .sort_values(["week_start", "occurrence_count"], ascending=[True, False])
#     )
#     grouped["week_start"] = grouped["week_start"].dt.date
#     return grouped.reset_index(drop=True)


# # ──────────────────────────────────────────────────────────────────────────────
# # 4. VISUALIZATIONS
# # ──────────────────────────────────────────────────────────────────────────────
# def make_trend_chart(analytics: Dict) -> plt.Figure:
#     daily = analytics["daily_spending"]
#     fig, ax = plt.subplots(figsize=(10, 4))
#     if daily:
#         ax.plot(list(daily.keys()), list(daily.values()),
#                 marker="o", linestyle="-", color="#1f77b4")
#         ax.set_title("Daily Spending Trend", fontsize=14)
#         ax.set_xlabel("Date")
#         ax.set_ylabel("Amount (₹)")
#         plt.xticks(rotation=45)
#     else:
#         ax.text(0.5, 0.5, "Not enough data", ha="center", va="center")
#     plt.tight_layout()
#     return fig


# def make_pie_chart(analytics: Dict) -> plt.Figure:
#     cats = analytics["top_categories"]
#     fig, ax = plt.subplots(figsize=(6, 6))
#     if cats:
#         ax.pie(cats.values(), labels=cats.keys(), autopct="%1.1f%%", startangle=90)
#         ax.set_title("Spending by Category")
#         ax.axis("equal")
#     else:
#         ax.text(0.5, 0.5, "No categories", ha="center", va="center")
#     return fig


# def make_bar_chart(analytics: Dict) -> plt.Figure:
#     recips = analytics["top_recipients"]
#     fig, ax = plt.subplots(figsize=(8, 4))
#     if recips:
#         ax.barh(list(recips.keys()), list(recips.values()), color="#ff7f0e")
#         ax.set_title("Top 5 Recipients by Spending")
#         ax.set_xlabel("Amount (₹)")
#         ax.invert_yaxis()
#     else:
#         ax.text(0.5, 0.5, "No recipients", ha="center", va="center")
#     plt.tight_layout()
#     return fig


# # ──────────────────────────────────────────────────────────────────────────────
# # 5. AI SUMMARY
# # ──────────────────────────────────────────────────────────────────────────────
# @st.cache_resource(show_spinner="Loading AI model…")
# def load_summarizer():
#     try:
#         return pipeline("summarization", model="Falconsai/text_summarization")
#     except Exception as e:
#         st.warning(f"Could not load summarizer: {e}")
#         return None


# def generate_ai_summary(analytics: Dict) -> str:
#     if analytics["transaction_count"] == 0:
#         return "No transactions found. Upload a PDF to see your financial summary."

#     sorted_cats = sorted(analytics["top_categories"].items(),
#                          key=lambda x: x[1], reverse=True)
#     cat_text = (f"Top spending categories: {', '.join(c[0] for c in sorted_cats[:3])}."
#                 if sorted_cats else "")
#     rec_text = (f"Highest payment was to {list(analytics['top_recipients'].keys())[0]}."
#                 if analytics["top_recipients"] else "")

#     prompt = (
#         f"In the last period, you spent ₹{analytics['total_spent']:,.2f} across "
#         f"{analytics['transaction_count']} transactions. "
#         f"Average daily spend: ₹{analytics['avg_daily']:,.2f}. {cat_text} {rec_text}"
#     )
#     summarizer = load_summarizer()
#     if summarizer:
#         try:
#             result = summarizer(prompt, max_length=100, min_length=20, do_sample=False)
#             return result[0]["summary_text"]
#         except Exception:
#             pass
#     return prompt


# # ──────────────────────────────────────────────────────────────────────────────
# # 6. STREAMLIT UI
# # ──────────────────────────────────────────────────────────────────────────────
# st.title("💵 Financial Transaction Analyzer")
# st.markdown(
#     "Upload your **PhonePe**, **Paytm**, or **bank statement** PDF. "
#     "The app extracts transactions, stores them in a local database, "
#     "and shows AI-powered insights."
# )

# # ── Sidebar ───────────────────────────────────────────────────────────────────
# with st.sidebar:
#     st.header("⚙️ Controls")
#     uploaded_file = st.file_uploader("📄 Upload PDF Statement", type=["pdf"])
#     st.divider()
#     if st.button("🗑️ Clear all stored data", type="secondary"):
#         clear_all_transactions()
#         st.success("Database cleared.")
#         st.rerun()

# # ── Main area ─────────────────────────────────────────────────────────────────
# if uploaded_file is not None:
#     with st.spinner("Extracting transactions from PDF…"):
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
#             tmp.write(uploaded_file.read())
#             tmp_path = tmp.name
#         try:
#             transactions = extract_transactions_from_pdf(tmp_path)
#         finally:
#             os.unlink(tmp_path)

#     if not transactions:
#         st.error(
#             "⚠️ **No transactions found in this PDF.**\n\n"
#             "Possible reasons:\n"
#             "- The PDF is a scanned image (no selectable text). Use an OCR tool first.\n"
#             "- The date format doesn't match `Feb 13, 2026` / `13 Feb 2026` / `DD/MM/YYYY`.\n"
#             "- Each transaction block spans more than 5 lines.\n\n"
#             "Try opening the PDF in a browser and selecting text to check."
#         )
#         st.stop()

#     inserted = save_transactions(transactions, source_file=uploaded_file.name)
#     st.success(
#         f"✅ Parsed **{len(transactions)}** transactions — "
#         f"**{inserted}** new records saved."
#     )

#     df        = load_all_transactions()
#     analytics = compute_analytics(df)

#     tab1, tab2, tab3, tab4 = st.tabs(
#         ["📊 Overview", "📈 Charts", "📅 Weekly Summary", "🗃️ Raw Data"]
#     )

#     # ── Tab 1 ─────────────────────────────────────────────────────────────────
#     with tab1:
#         st.subheader("Financial Overview")
#         c1, c2, c3, c4 = st.columns(4)
#         c1.metric("💰 Total Spent",        f"₹{analytics['total_spent']:,.2f}")
#         c2.metric("📥 Total Received",     f"₹{analytics['total_credited']:,.2f}")
#         c3.metric("🧾 Debit Transactions", analytics["transaction_count"])
#         c4.metric("📅 Avg Daily Spend",    f"₹{analytics['avg_daily']:,.2f}")
#         st.divider()
#         st.subheader("🤖 AI Summary")
#         with st.spinner("Generating summary…"):
#             st.info(generate_ai_summary(analytics))

#     # ── Tab 2 ─────────────────────────────────────────────────────────────────
#     with tab2:
#         st.subheader("📈 Daily Spending Trend")
#         st.pyplot(make_trend_chart(analytics), use_container_width=True)
#         cc1, cc2 = st.columns(2)
#         with cc1:
#             st.subheader("🍕 By Category")
#             st.pyplot(make_pie_chart(analytics))
#         with cc2:
#             st.subheader("🏆 Top Recipients")
#             st.pyplot(make_bar_chart(analytics))

#     # ── Tab 3 ─────────────────────────────────────────────────────────────────
#     with tab3:
#         st.subheader("📅 Weekly Recipient Summary")
#         weekly = weekly_recipient_summary(df)
#         if weekly.empty:
#             st.info("Not enough dated data to build a weekly summary.")
#         else:
#             st.dataframe(weekly, use_container_width=True)
#             st.download_button(
#                 "⬇️ Download Weekly Summary (CSV)",
#                 data=weekly.to_csv(index=False).encode("utf-8"),
#                 file_name="weekly_recipient_summary.csv",
#                 mime="text/csv",
#             )

#     # ── Tab 4 ─────────────────────────────────────────────────────────────────
#     with tab4:
#         st.subheader("All Stored Transactions")
#         st.dataframe(df, use_container_width=True)
#         st.download_button(
#             "⬇️ Download All Transactions (CSV)",
#             data=df.to_csv(index=False).encode("utf-8"),
#             file_name="all_transactions.csv",
#             mime="text/csv",
#         )

# else:
#     st.info("👈 Upload a PDF statement from the sidebar to get started.")

#     # Show any previously loaded data
#     df_existing = load_all_transactions()
#     if not df_existing.empty:
#         st.subheader("📂 Previously Loaded Transactions")
#         a = compute_analytics(df_existing)
#         e1, e2, e3 = st.columns(3)
#         e1.metric("💰 Total Spent",     f"₹{a['total_spent']:,.2f}")
#         e2.metric("🧾 Transactions",    a["transaction_count"])
#         e3.metric("📅 Avg Daily Spend", f"₹{a['avg_daily']:,.2f}")
#         st.dataframe(df_existing, use_container_width=True)

# ========================= IMPORTS =========================
import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from typing import List, Dict, Optional
import plotly.express as px
import plotly.graph_objects as go
import warnings

warnings.filterwarnings("ignore")

# ========================= PAGE CONFIG =========================
st.set_page_config(
    page_title="Financial Transaction Analyzer",
    page_icon="💰",
    layout="wide"
)

# ========================= CUSTOM CSS =========================
st.markdown("""
<style>
.metric-card {
    background-color: #111827;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #374151;
}
.success-box {
    background-color: #14532d;
    padding: 15px;
    border-radius: 10px;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ========================= TRANSACTION EXTRACTOR =========================
class TransactionExtractor:
    """
    Robust PDF transaction extractor
    """

    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.transactions = []

    # =========================================================
    # MAIN EXTRACTION
    # =========================================================
    def extract_transactions(self) -> pd.DataFrame:

        try:
            with pdfplumber.open(self.pdf_file) as pdf:

                for page_num, page in enumerate(pdf.pages, start=1):

                    text = page.extract_text()

                    if not text:
                        continue

                    lines = text.split("\n")

                    page_transactions = self._process_page(
                        lines=lines,
                        page_num=page_num
                    )

                    self.transactions.extend(page_transactions)

            df = self._create_dataframe()

            return df

        except Exception as e:
            st.error(f"Extraction Error: {str(e)}")
            return pd.DataFrame()

    # =========================================================
    # PROCESS PAGE
    # =========================================================
    def _process_page(
        self,
        lines: List[str],
        page_num: int
    ) -> List[Dict]:

        transactions = []

        i = 0

        while i < len(lines):

            line = lines[i].strip()

            if self._looks_like_date_line(line):

                transaction = self._extract_transaction_block(
                    lines=lines,
                    start_idx=i,
                    page_num=page_num
                )

                if transaction:
                    transactions.append(transaction)

                    # Skip next few lines
                    i += 4
                else:
                    i += 1

            else:
                i += 1

        return transactions

    # =========================================================
    # EXTRACT BLOCK
    # =========================================================
    def _extract_transaction_block(
        self,
        lines: List[str],
        start_idx: int,
        page_num: int
    ) -> Optional[Dict]:

        try:

            transaction = {
                "page_number": page_num,
                "raw_lines": []
            }

            line1 = lines[start_idx].strip()

            transaction["raw_lines"].append(line1)

            # DATE + TIME
            date_time = self._extract_date_time(line1)
            transaction.update(date_time)

            # TYPE + RECIPIENT
            recipient_info = self._extract_recipient_and_type(line1)
            transaction.update(recipient_info)

            # AMOUNT
            amount = self._extract_amount(line1)

            if amount is not None:
                transaction["amount"] = amount

            # LOOK AHEAD LINES
            for offset in [1, 2, 3]:

                if start_idx + offset >= len(lines):
                    continue

                check_line = lines[start_idx + offset].strip()

                if not check_line:
                    continue

                transaction["raw_lines"].append(check_line)

                # TIME
                if "time" not in transaction:

                    time_match = re.search(
                        r'(\d{1,2}:\d{2}\s*[ap]m)',
                        check_line.lower()
                    )

                    if time_match:
                        transaction["time"] = time_match.group(1)

                # TX ID
                if (
                    "Transaction ID" in check_line
                    or "UTR" in check_line
                ):
                    tx_info = self._extract_transaction_ids(check_line)
                    transaction.update(tx_info)

                # PAID BY
                if "Paid by" in check_line:
                    transaction["paid_by"] = (
                        check_line
                        .replace("Paid by", "")
                        .strip()
                    )

            return transaction

        except Exception:
            return None

    # =========================================================
    # DATE LINE CHECK
    # =========================================================
    def _looks_like_date_line(self, line: str) -> bool:

        patterns = [
            r'[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}',
            r'\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}',
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
        ]

        return any(re.search(p, line) for p in patterns)

    # =========================================================
    # DATE + TIME
    # =========================================================
    def _extract_date_time(self, line: str) -> Dict:

        result = {}

        date_match = re.search(
            r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})',
            line
        )

        if date_match:

            result["date"] = date_match.group(1)

            try:
                result["parsed_date"] = datetime.strptime(
                    date_match.group(1),
                    "%b %d, %Y"
                )
            except:
                pass

        time_match = re.search(
            r'(\d{1,2}:\d{2}\s*[ap]m)',
            line.lower()
        )

        if time_match:
            result["time"] = time_match.group(1)

        return result

    # =========================================================
    # TYPE + RECIPIENT
    # =========================================================
    def _extract_recipient_and_type(self, line: str) -> Dict:

        result = {}

        line_upper = line.upper()

        # ---------- TYPE ----------
        if "DEBIT" in line_upper:
            result["type"] = "DEBIT"

        elif "CREDIT" in line_upper:
            result["type"] = "CREDIT"

        elif "PAID TO" in line_upper:
            result["type"] = "DEBIT"

        elif "RECEIVED FROM" in line_upper:
            result["type"] = "CREDIT"

        # ---------- RECIPIENT ----------
        recipient_patterns = [
            r'Paid to\s+(.+?)(?:\s+DEBIT|\s+CREDIT|₹|$)',
            r'Received from\s+(.+?)(?:\s+DEBIT|\s+CREDIT|₹|$)'
        ]

        for pattern in recipient_patterns:

            match = re.search(pattern, line, re.IGNORECASE)

            if match:
                result["recipient"] = match.group(1).strip()
                break

        return result

    # =========================================================
    # AMOUNT EXTRACTION
    # =========================================================
    def _extract_amount(self, line: str) -> Optional[float]:

        # STRICT ₹ AMOUNT EXTRACTION
        amount_patterns = [

            # ₹12,345.67
            r'₹\s*([\d,]+\.\d{2})',

            # INR 1234.00
            r'INR\s*([\d,]+\.\d{2})',

            # fallback decimal
            r'([\d,]+\.\d{2})'
        ]

        for pattern in amount_patterns:

            matches = re.findall(pattern, line)

            if matches:

                try:
                    amount = matches[0].replace(",", "")
                    return float(amount)
                except:
                    continue

        return None

    # =========================================================
    # TX IDS
    # =========================================================
    def _extract_transaction_ids(self, line: str) -> Dict:

        result = {}

        tx_match = re.search(
            r'Transaction ID\s+(\S+)',
            line
        )

        if tx_match:
            result["transaction_id"] = tx_match.group(1)

        utr_match = re.search(
            r'UTR No\.?\s+(\S+)',
            line
        )

        if utr_match:
            result["utr_number"] = utr_match.group(1)

        return result

    # =========================================================
    # DATAFRAME
    # =========================================================
    def _create_dataframe(self) -> pd.DataFrame:

        if not self.transactions:
            return pd.DataFrame()

        df = pd.DataFrame(self.transactions)

        # ---------------- CLEAN TYPE ----------------
        if "type" in df.columns:

            df["type"] = (
                df["type"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

        # ---------------- CLEAN AMOUNT ----------------
        if "amount" in df.columns:

            df["amount"] = pd.to_numeric(
                df["amount"],
                errors="coerce"
            )

        # ---------------- DATE PARSE ----------------
        if "date" in df.columns:

            df["parsed_date"] = pd.to_datetime(
                df["date"],
                errors="coerce"
            )

        # ---------------- COLUMN ORDER ----------------
        columns = [
            "date",
            "parsed_date",
            "time",
            "recipient",
            "type",
            "amount",
            "transaction_id",
            "utr_number"
        ]

        available_cols = [
            col for col in columns
            if col in df.columns
        ]

        df = df[available_cols]

        # ---------------- REMOVE INVALIDS ----------------
        df = df.dropna(subset=["amount"])

        # ---------------- SORT ----------------
        if "parsed_date" in df.columns:
            df = df.sort_values("parsed_date")

        df = df.reset_index(drop=True)

        return df


# ========================= ANALYTICS =========================
def calculate_metrics(df):

    debit_df = df[df["type"] == "DEBIT"]

    credit_df = df[df["type"] == "CREDIT"]

    total_spent = debit_df["amount"].sum()

    total_received = credit_df["amount"].sum()

    debit_count = len(debit_df)

    avg_daily = 0

    if "parsed_date" in df.columns:

        unique_days = df["parsed_date"].dt.date.nunique()

        if unique_days > 0:
            avg_daily = total_spent / unique_days

    return {
        "spent": total_spent,
        "received": total_received,
        "debit_count": debit_count,
        "avg_daily": avg_daily
    }


# ========================= CHARTS =========================
def transaction_type_chart(df):

    chart_df = (
        df.groupby("type")["amount"]
        .sum()
        .reset_index()
    )

    fig = px.pie(
        chart_df,
        names="type",
        values="amount",
        title="Debit vs Credit Distribution"
    )

    return fig


def monthly_spending_chart(df):

    debit_df = df[df["type"] == "DEBIT"].copy()

    if debit_df.empty:
        return None

    debit_df["month"] = (
        debit_df["parsed_date"]
        .dt.to_period("M")
        .astype(str)
    )

    monthly = (
        debit_df.groupby("month")["amount"]
        .sum()
        .reset_index()
    )

    fig = px.bar(
        monthly,
        x="month",
        y="amount",
        title="Monthly Spending"
    )

    return fig


# ========================= AI SUMMARY =========================
def generate_summary(df):

    debit_df = df[df["type"] == "DEBIT"]

    total_spent = debit_df["amount"].sum()

    txn_count = len(debit_df)

    avg_spend = 0

    if not debit_df.empty:

        unique_days = (
            debit_df["parsed_date"]
            .dt.date
            .nunique()
        )

        if unique_days > 0:
            avg_spend = total_spent / unique_days

    top_recipient = "N/A"

    if "recipient" in debit_df.columns:

        recipient_summary = (
            debit_df.groupby("recipient")["amount"]
            .sum()
            .sort_values(ascending=False)
        )

        if not recipient_summary.empty:
            top_recipient = recipient_summary.index[0]

    summary = f"""
In the analyzed statement:

• Total Debit Amount: ₹{total_spent:,.2f}

• Total Credit Amount: ₹{df[df['type']=='CREDIT']['amount'].sum():,.2f}

• Total Debit Transactions: {txn_count}

• Average Daily Spend: ₹{avg_spend:,.2f}

• Highest Spending Recipient: {top_recipient}
"""

    return summary


# ========================= MAIN APP =========================
st.title("💰 Financial Transaction Analyzer")

st.markdown("""
Upload PhonePe, Paytm, or Bank Statement PDFs and get:
- Transaction extraction
- Debit/Credit analysis
- Charts
- Weekly summaries
- Financial insights
""")

uploaded_file = st.file_uploader(
    "Upload PDF Statement",
    type=["pdf"]
)

if uploaded_file:

    with st.spinner("Extracting transactions..."):

        extractor = TransactionExtractor(uploaded_file)

        df = extractor.extract_transactions()

    if not df.empty:

        st.success(
            f"Parsed {len(df)} transactions successfully"
        )

        # ================= METRICS =================
        metrics = calculate_metrics(df)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "💸 Total Spent",
                f"₹{metrics['spent']:,.2f}"
            )

        with col2:
            st.metric(
                "💰 Total Received",
                f"₹{metrics['received']:,.2f}"
            )

        with col3:
            st.metric(
                "📄 Debit Transactions",
                metrics["debit_count"]
            )

        with col4:
            st.metric(
                "📆 Avg Daily Spend",
                f"₹{metrics['avg_daily']:,.2f}"
            )

        # ================= TABS =================
        tab1, tab2, tab3 = st.tabs([
            "Overview",
            "Charts",
            "Raw Data"
        ])

        # ================= OVERVIEW =================
        with tab1:

            st.subheader("AI Financial Summary")

            st.info(generate_summary(df))

            st.subheader("Top Recipients")

            if "recipient" in df.columns:

                top_recipients = (
                    df[df["type"] == "DEBIT"]
                    .groupby("recipient")["amount"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(10)
                )

                st.dataframe(top_recipients)

        # ================= CHARTS =================
        with tab2:

            pie_chart = transaction_type_chart(df)

            st.plotly_chart(
                pie_chart,
                use_container_width=True
            )

            monthly_chart = monthly_spending_chart(df)

            if monthly_chart:
                st.plotly_chart(
                    monthly_chart,
                    use_container_width=True
                )

        # ================= RAW DATA =================
        with tab3:

            st.dataframe(
                df,
                use_container_width=True
            )

            csv = df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="transactions.csv",
                mime="text/csv"
            )

    else:
        st.error("No transactions extracted.")
