
import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
# =========================================================
# SESSION STATE INITIALIZATION
# =========================================================
if "uploaded_file_key" not in st.session_state:
    st.session_state.uploaded_file_key = None
if "debit_tagged_df" not in st.session_state:
    st.session_state.debit_tagged_df = None
if "credit_tagged_df" not in st.session_state:
    st.session_state.credit_tagged_df = None
if "master_df" not in st.session_state:
    st.session_state.master_df = None
if "current_df" not in st.session_state:
    st.session_state.current_df = None
# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Spendwise · Transaction Analyzer",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# GLOBAL STYLES
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Tokens ── */
:root {
    --bg:        #0d1117;
    --surface:   #161b22;
    --border:    #21262d;
    --accent:    #7c3aed;
    --accent-lt: #a78bfa;
    --green:     #10b981;
    --red:       #f43f5e;
    --text:      #e6edf3;
    --muted:     #8b949e;
    --mono:      'JetBrains Mono', monospace;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1400px; }

/* ── Wordmark ── */
.wordmark {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text);
    margin-bottom: 0.25rem;
}
.wordmark span { color: var(--accent-lt); }
.tagline {
    font-size: 0.78rem;
    color: var(--muted);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

/* ── Upload zone ── */
.upload-zone {
    border: 2px dashed var(--border);
    border-radius: 14px;
    padding: 3rem 2rem;
    text-align: center;
    background: var(--surface);
    transition: border-color 0.2s;
    margin: 2rem 0;
}
.upload-zone:hover { border-color: var(--accent-lt); }
.upload-title { font-size: 1.1rem; font-weight: 600; color: var(--text); margin-bottom: 0.5rem; }
.upload-sub   { font-size: 0.85rem; color: var(--muted); }

/* ── KPI cards ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1.5rem 0; }
.kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    position: relative;
    overflow: hidden;
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent);
}
.kpi-card.green::after { background: var(--green); }
.kpi-card.red::after   { background: var(--red); }
.kpi-card.purple::after{ background: var(--accent-lt); }
.kpi-label { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.6rem; }
.kpi-value { font-size: 1.8rem; font-weight: 700; color: var(--text); font-family: var(--mono); line-height: 1; }
.kpi-sub   { font-size: 0.75rem; color: var(--muted); margin-top: 0.4rem; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 1.5rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 0.5rem 1.2rem;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--muted);
    background: transparent;
    border: none;
    transition: all 0.15s;
}
.stTabs [aria-selected="true"] {
    background: var(--accent);
    color: #fff !important;
}

/* ── Data table ── */
.stDataFrame { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.stDataFrame thead tr th { background: var(--surface) !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted) !important; }

/* ── Section header ── */
.section-header {
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
    margin: 1.5rem 0 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-header::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── Badge ── */
.badge {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 100px;
    font-size: 0.72rem;
    font-weight: 600;
    font-family: var(--mono);
}
.badge-green { background: rgba(16,185,129,0.12); color: var(--green); }
.badge-red   { background: rgba(244,63,94,0.12);  color: var(--red);   }
.badge-purple{ background: rgba(124,58,237,0.12); color: var(--accent-lt); }

/* ── Buttons ── */
.stButton > button {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.5rem 1.2rem;
    transition: opacity 0.15s;
}
.stButton > button:hover { opacity: 0.85; }
.stDownloadButton > button {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    border-radius: 8px;
    font-size: 0.82rem;
    transition: border-color 0.15s, color 0.15s;
}
.stDownloadButton > button:hover { border-color: var(--accent-lt); color: var(--accent-lt); }

/* ── Selectbox & Checkbox ── */
.stSelectbox > div > div { border-radius: 8px !important; border-color: var(--border) !important; background: var(--surface) !important; }
.stCheckbox label { font-size: 0.85rem; color: var(--muted); }

/* ── Alert-style insight cards ── */
.insight-card {
    border-left: 3px solid var(--accent);
    background: rgba(124,58,237,0.07);
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    font-size: 0.85rem;
    color: var(--text);
    margin-bottom: 0.6rem;
}
.insight-card.warn { border-color: #f59e0b; background: rgba(245,158,11,0.07); }
.insight-card.good { border-color: var(--green); background: rgba(16,185,129,0.07); }

/* ── Progress bar override ── */
.stProgress > div > div > div { background: var(--accent) !important; border-radius: 4px; }

/* ── Expander ── */
.streamlit-expanderHeader {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: var(--muted) !important;
}

/* ── File uploader inner ── */
.stFileUploader > div { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# PRE-COMPILED REGEX
# =========================================================
DATE_PATTERNS = [
    re.compile(r'[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}'),
    re.compile(r'[A-Z][a-z]{3,4}\s+\d{1,2},\s+\d{4}'),
    re.compile(r'\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}'),
    re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}')
]
EXTRACT_DATE_REGEX  = re.compile(r'([A-Z][a-z]{2,4}\s+\d{1,2},\s+\d{4})')
EXTRACT_TIME_REGEX  = re.compile(r'(\d{1,2}:\d{2}\s*[ap]m)')
DEBIT_REGEX         = re.compile(r"Paid to\s+(.+?)(?:\s+DEBIT|\s+₹|$)", re.IGNORECASE)
CREDIT_REGEX        = re.compile(r"Received from\s+(.+?)(?:\s+CREDIT|\s+₹|$)", re.IGNORECASE)
RUPEE_REGEX         = re.compile(r"₹\s*([\d,]+(?:\.\d{1,2})?)")

PLOTLY_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#8b949e", size=12),
    xaxis=dict(gridcolor="#21262d", linecolor="#21262d", tickcolor="#21262d"),
    yaxis=dict(gridcolor="#21262d", linecolor="#21262d", tickcolor="#21262d"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#21262d"),
    margin=dict(l=8, r=8, t=32, b=8),
)

# =========================================================
# HELPER
# =========================================================
def clean_amount(value):
    try:
        return float(str(value).replace("₹", "").replace(",", "").strip())
    except Exception:
        return 0.0

def fmt_inr(value):
    """Format number as Indian Rupee string with commas."""
    try:
        value = float(value)
        if value >= 1_00_000:
            return f"₹{value/1_00_000:.1f}L"
        elif value >= 1_000:
            return f"₹{value/1_000:.1f}K"
        return f"₹{value:,.0f}"
    except Exception:
        return "₹0"

# =========================================================
# TRANSACTION EXTRACTOR
# =========================================================
class TransactionExtractor:
    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file
        self.transactions  = []

    def extract_transactions(self):
        with pdfplumber.open(self.uploaded_file) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if not text:
                    continue
                lines = text.split("\n")
                self.transactions.extend(self.process_page(lines, page_num))
        return self.create_dataframe()

    def process_page(self, lines, page_num):
        transactions = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if self.looks_like_transaction(line):
                t = self.extract_transaction(lines, i, page_num)
                if t:
                    transactions.append(t)
            i += 1
        return transactions

    def looks_like_transaction(self, line):
        has_date   = any(p.search(line) for p in DATE_PATTERNS)
        has_amount = "₹" in line
        return has_date and has_amount

    def extract_transaction(self, lines, start_idx, page_num):
        try:
            line1 = lines[start_idx].strip()
            t = {
                "page_number":   page_num,
                "date": None,   "time": None,
                "receiver_name": None, "type": "UNKNOWN",
                "amount": 0.0
            }

            date_match = EXTRACT_DATE_REGEX.search(line1)
            if date_match:
                raw_date = date_match.group(1).replace("Sept", "Sep")
                t["date"] = raw_date
                try:    t["parsed_date"] = datetime.strptime(raw_date, '%b %d, %Y')
                except: t["parsed_date"] = None

            line_lower = line1.lower()
            time_match = EXTRACT_TIME_REGEX.search(line_lower)
            if time_match:
                t["time"] = time_match.group(1)
            else:
                for offset in [1, 2, 3]:
                    if start_idx + offset < len(lines):
                        next_ll = lines[start_idx + offset].strip().lower()
                        tm = EXTRACT_TIME_REGEX.search(next_ll)
                        if tm:
                            t["time"] = tm.group(1)
                            break

            line_upper = line1.upper()
            if "CREDIT" in line_upper or "RECEIVED FROM" in line_upper:
                t["type"] = "CREDIT"
            elif "DEBIT" in line_upper or "PAID TO" in line_upper:
                t["type"] = "DEBIT"

            dm = DEBIT_REGEX.findall(line1)
            cm = CREDIT_REGEX.findall(line1)
            if dm:   t["receiver_name"] = dm[-1].strip()
            elif cm: t["receiver_name"] = cm[-1].strip()

            rm = RUPEE_REGEX.findall(line1)
            if rm: t["amount"] = clean_amount(rm[-1])

            return t
        except Exception:
            return None

    def create_dataframe(self):
        if not self.transactions:
            return pd.DataFrame()
        df = pd.DataFrame(self.transactions)
        for col in ["date", "time", "receiver_name", "type", "amount"]:
            if col not in df.columns:
                df[col] = None

        df["type"]   = df["type"].astype(str).str.upper().str.strip()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

        if "receiver_name" in df.columns:
            df["receiver_name"] = (
                df["receiver_name"]
                .str.replace(r'\s+', ' ', regex=True)
                .str.strip()
                .str.title()
            )

        if "parsed_date" in df.columns:
            df = df.sort_values(by="parsed_date")
            df = df.drop(columns=["parsed_date"])

        return df.reset_index(drop=True)

@st.cache_data(show_spinner=False)
def get_pdf_data(uploaded_file):
    extractor = TransactionExtractor(uploaded_file)
    return extractor.extract_transactions()

# =========================================================
# AUTO-INSIGHTS ENGINE
# =========================================================
def generate_insights(df):
    insights = []
    if df.empty:
        return insights

    total_debit  = df[df["type"] == "DEBIT"]["amount"].sum()
    total_credit = df[df["type"] == "CREDIT"]["amount"].sum()
    net          = total_credit - total_debit

    if net < 0:
        insights.append(("warn", f"Net cash flow is negative — you spent {fmt_inr(abs(net))} more than you received this period."))
    else:
        insights.append(("good", f"Net cash flow is positive: {fmt_inr(net)} surplus this period."))

    if not df[df["type"] == "DEBIT"].empty:
        top_debit = (
            df[df["type"] == "DEBIT"]
            .groupby("receiver_name")["amount"]
            .sum()
            .nlargest(1)
        )
        if not top_debit.empty:
            name, amt = top_debit.index[0], top_debit.iloc[0]
            pct = (amt / total_debit * 100) if total_debit else 0
            insights.append(("info", f"Largest expense destination: {name} ({fmt_inr(amt)} · {pct:.0f}% of total outflow)."))

    # High-frequency recipients
    freq = df.groupby("receiver_name").size().nlargest(1)
    if not freq.empty:
        insights.append(("info", f"Most frequent transaction partner: {freq.index[0]} ({freq.iloc[0]} transactions)."))

    # Large single transactions
    p95 = df["amount"].quantile(0.95)
    large = df[df["amount"] >= p95]
    if len(large) > 0:
        insights.append(("warn", f"{len(large)} transaction(s) in the top 5% by value (≥ {fmt_inr(p95)}) — worth reviewing."))

    return insights

# =========================================================
# UI — HEADER
# =========================================================
col_logo, col_right = st.columns([3, 1])
with col_logo:
    st.markdown('<div class="wordmark">spend<span>wise</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline">Bank Statement · Transaction Analyzer</div>', unsafe_allow_html=True)

# =========================================================
# FILE UPLOAD
# =========================================================
uploaded_file = st.file_uploader(
    "Upload your bank statement PDF",
    type=["pdf"],
    help="Supports Google Pay, PhonePe, and most Indian bank PDF statement formats",
    label_visibility="collapsed"
)

if not uploaded_file:
    st.markdown("""
    <div class="upload-zone">
        <div class="upload-title">📂 Drop your bank statement PDF here</div>
        <div class="upload-sub">Supports most Indian bank & UPI statement formats · Private & processed locally</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# =========================================================
# EXTRACTION
# =========================================================
with st.spinner("Reading transactions…"):
    df = get_pdf_data(uploaded_file)

if df.empty:
    st.error("No transactions could be extracted from this PDF. Check that the file contains text-based UPI/bank transactions.")
    st.stop()

# =========================================================
# KPI BANNER
# =========================================================
total_debit  = df[df["type"] == "DEBIT"]["amount"].sum()
total_credit = df[df["type"] == "CREDIT"]["amount"].sum()
net_flow     = total_credit - total_debit
n_unique     = df["receiver_name"].dropna().nunique()

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Total Transactions</div>
    <div class="kpi-value">{len(df)}</div>
    <div class="kpi-sub">{n_unique} unique parties</div>
  </div>
  <div class="kpi-card red">
    <div class="kpi-label">Total Outflow</div>
    <div class="kpi-value">{fmt_inr(total_debit)}</div>
    <div class="kpi-sub">Debits / payments</div>
  </div>
  <div class="kpi-card green">
    <div class="kpi-label">Total Inflow</div>
    <div class="kpi-value">{fmt_inr(total_credit)}</div>
    <div class="kpi-sub">Credits / receipts</div>
  </div>
  <div class="kpi-card {'green' if net_flow >= 0 else 'red'}">
    <div class="kpi-label">Net Cash Flow</div>
    <div class="kpi-value">{'+ ' if net_flow >= 0 else '− '}{fmt_inr(abs(net_flow))}</div>
    <div class="kpi-sub">{'Surplus' if net_flow >= 0 else 'Deficit'} this period</div>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Transactions",
    "Visualizations",
    "Receivers",
    "Tag Purposes",
    "Insights",
    "Budget Tracker"
])

# ─────────────────────────────────────────
# TAB 1 — TRANSACTIONS
# ─────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">All Transactions</div>', unsafe_allow_html=True)

    # Filters
    fcol1, fcol2, fcol3 = st.columns([1, 1, 2])
    with fcol1:
        type_filter = st.selectbox("Type", ["All", "DEBIT", "CREDIT"])
    with fcol2:
        min_amt = st.number_input("Min Amount (₹)", value=0, step=100)
    with fcol3:
        name_search = st.text_input("Search by name", placeholder="e.g. Swiggy, Amazon…")

    filtered = df.copy()
    if type_filter != "All":
        filtered = filtered[filtered["type"] == type_filter]
    if min_amt > 0:
        filtered = filtered[filtered["amount"] >= min_amt]
    if name_search:
        filtered = filtered[filtered["receiver_name"].str.contains(name_search, case=False, na=False)]

    st.caption(f"Showing {len(filtered)} of {len(df)} transactions")
    st.dataframe(filtered, use_container_width=True, height=440)

    dcol1, dcol2 = st.columns([1, 5])
    with dcol1:
        st.download_button("⬇ CSV", filtered.to_csv(index=False).encode("utf-8"),
                           "transactions.csv", "text/csv")

# ─────────────────────────────────────────
# TAB 2 — VISUALIZATIONS
# ─────────────────────────────────────────
# ─────────────────────────────────────────
# TAB 2 — VISUALIZATIONS  (FIXED)
# ─────────────────────────────────────────
with tab2:
    # CRITICAL FIX: Always use master_df if available, otherwise fallback to df
    if "master_df" in st.session_state and not st.session_state.master_df.empty:
        viz_df = st.session_state.master_df.copy()
    else:
        viz_df = df.copy()
    
    viz_df["temp_date"] = pd.to_datetime(viz_df["date"], format="%b %d, %Y", errors="coerce")
    grouping_col = "purpose" if "purpose" in viz_df.columns else "receiver_name"

    # ── Donut charts ──
    st.markdown('<div class="section-header">Distribution</div>', unsafe_allow_html=True)
    pc1, pc2 = st.columns(2)

    with pc1:
        st.caption("Outflow breakdown")
        debit_agg = viz_df[viz_df["type"] == "DEBIT"].groupby(grouping_col, as_index=False)["amount"].sum()
        if not debit_agg.empty:
            fig = px.pie(debit_agg, values="amount", names=grouping_col, hole=0.55,
                         color_discrete_sequence=["#f43f5e","#fb7185","#fda4af","#fecdd3","#7c3aed","#a78bfa","#c4b5fd"])
            fig.update_traces(textposition="inside", textinfo="percent+label",
                              marker_line_width=0, hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<extra></extra>")
            fig.update_layout(**PLOTLY_DARK)
            st.plotly_chart(fig, use_container_width=True, key="outflow_donut")  # Added key
        else:
            st.info("No debit data.")

    with pc2:
        st.caption("Inflow breakdown")
        credit_agg = viz_df[viz_df["type"] == "CREDIT"].groupby(grouping_col, as_index=False)["amount"].sum()
        if not credit_agg.empty:
            fig = px.pie(credit_agg, values="amount", names=grouping_col, hole=0.55,
                         color_discrete_sequence=["#10b981","#34d399","#6ee7b7","#a7f3d0","#7c3aed","#a78bfa","#c4b5fd"])
            fig.update_traces(textposition="inside", textinfo="percent+label",
                              marker_line_width=0, hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<extra></extra>")
            fig.update_layout(**PLOTLY_DARK)
            st.plotly_chart(fig, use_container_width=True, key="inflow_donut")  # Added key
        else:
            st.info("No credit data.")

    # ── Cash flow trend ──
    st.markdown('<div class="section-header">Cash Flow Trend</div>', unsafe_allow_html=True)
    trend_df = viz_df.dropna(subset=["temp_date"]).copy()

    if not trend_df.empty:
        interval = st.selectbox("Interval", ["Daily", "Weekly", "Monthly"], key="interval")
        freq_map = {"Daily": "D", "Weekly": "W-MON", "Monthly": "ME"}
        time_agg = (
            trend_df.groupby([pd.Grouper(key="temp_date", freq=freq_map[interval]), "type"])["amount"]
            .sum()
            .reset_index()
        )
        fig_trend = px.line(
            time_agg, x="temp_date", y="amount", color="type",
            markers=True,
            labels={"temp_date": "Date", "amount": "Amount (₹)", "type": ""},
            color_discrete_map={"CREDIT": "#10b981", "DEBIT": "#f43f5e"}
        )
        fig_trend.update_traces(line_width=2, marker_size=5)
        fig_trend.update_layout(hovermode="x unified", **PLOTLY_DARK)
        st.plotly_chart(fig_trend, use_container_width=True, key="trend_chart")  # Added key

    # ── Top 10 recipients bar ──
    st.markdown('<div class="section-header">Top Expense Destinations</div>', unsafe_allow_html=True)
    top_receivers = (
        viz_df[viz_df["type"] == "DEBIT"]
        .groupby("receiver_name")["amount"]
        .sum()
        .nlargest(10)
        .reset_index()
        .sort_values("amount")
    )
    if not top_receivers.empty:
        fig_bar = px.bar(
            top_receivers, x="amount", y="receiver_name",
            orientation="h",
            labels={"amount": "Total Debited (₹)", "receiver_name": ""},
            color="amount",
            color_continuous_scale=["#7c3aed", "#f43f5e"]
        )
        fig_bar.update_coloraxes(showscale=False)
        fig_bar.update_traces(hovertemplate="<b>%{y}</b><br>₹%{x:,.0f}<extra></extra>")
        fig_bar.update_layout(**PLOTLY_DARK)
        st.plotly_chart(fig_bar, use_container_width=True, key="top_receivers")  # Added key
# ─────────────────────────────────────────
# TAB 3 — UNIQUE RECEIVERS
# ─────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">Last Transaction per Party</div>', unsafe_allow_html=True)
    unique_df = (
        df[["date", "time", "receiver_name", "type", "amount"]]
        .dropna(subset=["receiver_name"])
        .drop_duplicates(subset=["receiver_name", "type"], keep="last")
        .reset_index(drop=True)
        .rename(columns={
            "date":          "Last Date",
            "time":          "Last Time",
            "receiver_name": "Name",
            "type":          "Type",
            "amount":        "Amount (₹)"
        })
    )
    st.dataframe(unique_df, use_container_width=True, height=420)
# ─────────────────────────────────────────
# TAB 4 — TAG PURPOSES
# ─────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">Categorise Transactions</div>', unsafe_allow_html=True)

    debit_purposes  = ["Food", "Travel", "Recharge", "Shopping", "Medical",
                       "Education", "Entertainment", "Bills", "Rent", "Fuel",
                       "Investment", "Transfer", "Family", "Other"]
    credit_purposes = ["Salary", "Business", "Transfer", "Cashback", "Refund",
                       "Family", "Investment Return", "Other"]

    if "debit_tagged_df" not in st.session_state:
        dbase = (df[df["type"] == "DEBIT"][["date", "time", "receiver_name", "amount"]]
                 .dropna(subset=["receiver_name"])
                 .drop_duplicates(subset=["receiver_name"], keep="last")
                 .reset_index(drop=True))
        dbase["purpose"] = "Unassigned"
        st.session_state.debit_tagged_df = dbase

    if "credit_tagged_df" not in st.session_state:
        cbase = (df[df["type"] == "CREDIT"][["date", "time", "receiver_name", "amount"]]
                 .dropna(subset=["receiver_name"])
                 .drop_duplicates(subset=["receiver_name"], keep="last")
                 .reset_index(drop=True))
        cbase["purpose"] = "Unassigned"
        st.session_state.credit_tagged_df = cbase

    hide_tagged = st.checkbox("Hide already tagged", value=True)

    # Progress bars
    d_total   = len(st.session_state.debit_tagged_df)
    d_tagged  = (st.session_state.debit_tagged_df["purpose"] != "Unassigned").sum()
    c_total   = len(st.session_state.credit_tagged_df)
    c_tagged  = (st.session_state.credit_tagged_df["purpose"] != "Unassigned").sum()

    p1, p2 = st.columns(2)
    with p1:
        st.caption(f"Debit tagged: {d_tagged}/{d_total}")
        st.progress(d_tagged / d_total if d_total else 0)
    with p2:
        st.caption(f"Credit tagged: {c_tagged}/{c_total}")
        st.progress(c_tagged / c_total if c_total else 0)

    st.divider()

    # DEBIT
    st.markdown("**🔴 Debit Tagging (Money Out)**")
    d_filter = st.session_state.debit_tagged_df
    if hide_tagged:
        d_filter = d_filter[d_filter["purpose"] == "Unassigned"]

    if d_filter.empty and d_total > 0:
        st.success("All debit transactions tagged!")
    elif d_total == 0:
        st.info("No debit transactions found.")
    else:
        dc1, dc2, dc3 = st.columns([2, 2, 1])
        with dc1: sel_dr = st.selectbox("Receiver", d_filter["receiver_name"].tolist(), key="dr")
        with dc2: sel_dp = st.selectbox("Category", debit_purposes, key="dp")
        with dc3:
            st.write("")
            st.write("")
            if st.button("Save", key="save_d"):
                st.session_state.debit_tagged_df.loc[
                    st.session_state.debit_tagged_df["receiver_name"] == sel_dr, "purpose"
                ] = sel_dp
                st.toast(f"Tagged {sel_dr} → {sel_dp}")
                st.rerun()

    with st.expander("View debit tags"):
        st.dataframe(st.session_state.debit_tagged_df, use_container_width=True)

    st.divider()

    # CREDIT
    st.markdown("**🟢 Credit Tagging (Money In)**")
    c_filter = st.session_state.credit_tagged_df
    if hide_tagged:
        c_filter = c_filter[c_filter["purpose"] == "Unassigned"]

    if c_filter.empty and c_total > 0:
        st.success("All credit transactions tagged!")
    elif c_total == 0:
        st.info("No credit transactions found.")
    else:
        cc1, cc2, cc3 = st.columns([2, 2, 1])
        with cc1: sel_cr = st.selectbox("Sender", c_filter["receiver_name"].tolist(), key="cr")
        with cc2: sel_cp = st.selectbox("Category", credit_purposes, key="cp")
        with cc3:
            st.write("")
            st.write("")
            if st.button("Save", key="save_c"):
                st.session_state.credit_tagged_df.loc[
                    st.session_state.credit_tagged_df["receiver_name"] == sel_cr, "purpose"
                ] = sel_cp
                st.toast(f"Tagged {sel_cr} → {sel_cp}")
                st.rerun()

    with st.expander("View credit tags"):
        st.dataframe(st.session_state.credit_tagged_df, use_container_width=True)

    # SYNC
    st.divider()
    st.markdown("**🔄 Sync Tags to Master**")
    if st.button("Apply all tags to transaction list"):
        d_map = dict(zip(st.session_state.debit_tagged_df["receiver_name"],
                         st.session_state.debit_tagged_df["purpose"]))
        c_map = dict(zip(st.session_state.credit_tagged_df["receiver_name"],
                         st.session_state.credit_tagged_df["purpose"]))
        master = df.copy()
        master["purpose"] = "Unassigned"
        dm = master["type"] == "DEBIT"
        master.loc[dm, "purpose"] = master.loc[dm, "receiver_name"].map(d_map).fillna("Unassigned")
        cm = master["type"] == "CREDIT"
        master.loc[cm, "purpose"] = master.loc[cm, "receiver_name"].map(c_map).fillna("Unassigned")
        st.session_state.master_df = master
        st.success("Master file updated — Visualizations will now use your categories.")
        # Force immediate rerun to refresh all tabs
        st.success(f"✅ Master updated! {len(master)} transactions tagged.")
        st.rerun()  # This ensures all tabs refresh with new data

    if "master_df" in st.session_state:
        st.dataframe(st.session_state.master_df, use_container_width=True, height=360)
        st.download_button(
            "⬇ Download Tagged CSV",
            st.session_state.master_df.to_csv(index=False).encode("utf-8"),
            "transactions_tagged.csv", "text/csv"
        )
    

# ─────────────────────────────────────────
# TAB 5 — AUTO-INSIGHTS
# ─────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-header">Automatic Insights</div>', unsafe_allow_html=True)
    insights = generate_insights(df)

    for kind, msg in insights:
        css = {"info": "insight-card", "warn": "insight-card warn", "good": "insight-card good"}.get(kind, "insight-card")
        icon = {"info": "💡", "warn": "⚠️", "good": "✅"}.get(kind, "•")
        st.markdown(f'<div class="{css}">{icon} {msg}</div>', unsafe_allow_html=True)

    st.divider()

    # Daily average spend
    st.markdown('<div class="section-header">Spending Patterns</div>', unsafe_allow_html=True)
    temp = df.copy()
    temp["temp_date"] = pd.to_datetime(temp["date"], format="%b %d, %Y", errors="coerce")

    debit_by_day = temp[temp["type"] == "DEBIT"].groupby("temp_date")["amount"].sum().reset_index()
    if not debit_by_day.empty:
        avg_daily = debit_by_day["amount"].mean()
        max_day   = debit_by_day.loc[debit_by_day["amount"].idxmax()]
        ic1, ic2 = st.columns(2)
        ic1.metric("Avg Daily Spend", fmt_inr(avg_daily))
        ic2.metric("Highest Spend Day", max_day["temp_date"].strftime("%d %b"), fmt_inr(max_day["amount"]))

    # Day-of-week heatmap
    if not temp.empty and "temp_date" in temp.columns:
        temp["day_name"] = temp["temp_date"].dt.day_name()
        dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        dow = (temp[temp["type"] == "DEBIT"]
               .groupby("day_name")["amount"].sum()
               .reindex(dow_order).fillna(0).reset_index())
        fig_dow = px.bar(
            dow, x="day_name", y="amount",
            labels={"day_name": "Day", "amount": "Total Debited (₹)"},
            color="amount", color_continuous_scale=["#7c3aed","#f43f5e"]
        )
        fig_dow.update_coloraxes(showscale=False)
        fig_dow.update_layout(**PLOTLY_DARK)
        st.caption("Spend by day of week")
        st.plotly_chart(fig_dow, use_container_width=True)

# ─────────────────────────────────────────
# TAB 6 — BUDGET TRACKER  (Enhancement)
# ─────────────────────────────────────────
with tab6:
    st.markdown('<div class="section-header">Monthly Budget Limits</div>', unsafe_allow_html=True)
    st.caption("Set a spending limit for each category. Tag your transactions first (Tab 4 → Sync), then come back here.")

    categories = ["Food", "Travel", "Shopping", "Recharge", "Medical",
                  "Education", "Entertainment", "Bills", "Rent", "Fuel", "Other"]

    if "budgets" not in st.session_state:
        st.session_state.budgets = {cat: 0 for cat in categories}

    # Budget input grid (2 columns)
    cols_a = st.columns(2)
    for i, cat in enumerate(categories):
        with cols_a[i % 2]:
            val = st.number_input(f"{cat} (₹)", value=st.session_state.budgets[cat], step=500, key=f"budget_{cat}")
            st.session_state.budgets[cat] = val

    st.divider()
    st.markdown('<div class="section-header">Actual vs Budget</div>', unsafe_allow_html=True)

    master = st.session_state.get("master_df", None)
    if master is None or "purpose" not in master.columns:
        st.info("Sync your tagged transactions (Tab 4) to see budget vs actual comparison.")
    else:
        actuals = master[master["type"] == "DEBIT"].groupby("purpose")["amount"].sum().to_dict()

        rows = []
        for cat in categories:
            budget = st.session_state.budgets.get(cat, 0)
            actual = actuals.get(cat, 0)
            if budget == 0 and actual == 0:
                continue
            pct    = (actual / budget * 100) if budget > 0 else None
            status = "✅" if (pct is not None and pct < 85) else ("⚠️" if pct is not None and pct < 100 else "🔴")
            rows.append({"Category": cat, "Budget": fmt_inr(budget), "Actual": fmt_inr(actual),
                         "Used %": f"{pct:.0f}%" if pct is not None else "—", "Status": status})

        if rows:
            budget_df = pd.DataFrame(rows)
            st.dataframe(budget_df, use_container_width=True, hide_index=True)

            # Grouped bar
            cats   = [r["Category"] for r in rows]
            buds   = [st.session_state.budgets.get(c, 0) for c in cats]
            acts   = [actuals.get(c, 0) for c in cats]
            fig_bv = go.Figure(data=[
                go.Bar(name="Budget",  x=cats, y=buds, marker_color="#7c3aed", opacity=0.5),
                go.Bar(name="Actual",  x=cats, y=acts, marker_color="#f43f5e"),
            ])
            fig_bv.update_layout(barmode="group", **PLOTLY_DARK)
            st.plotly_chart(fig_bv, use_container_width=True)
        else:
            st.info("No matching categories found. Make sure you've synced tags and set budgets above.")
