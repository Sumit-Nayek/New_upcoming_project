import os
import re
import sqlite3
import tempfile
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Tuple

import gradio as gr
import pandas as pd
import pdfplumber
import matplotlib.pyplot as plt
import plotly.express as px
from transformers import pipeline

# ------------------------------
# 1. DATABASE SETUP
# ------------------------------
DB_PATH = "master_transactions.db"

def init_db():
    """Create the SQLite table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            recipient TEXT,
            type TEXT,
            amount REAL,
            transaction_id TEXT UNIQUE,
            utr_number TEXT,
            source_file TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                tx.get("utr_number"), source_file
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Duplicate transaction_id – skip
            continue
    conn.commit()
    conn.close()
    return inserted

def load_all_transactions() -> pd.DataFrame:
    """Return all transactions as a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
    conn.close()
    return df

# ------------------------------
# 2. PDF EXTRACTION (PhonePe/Paytm/Bank)
# ------------------------------
def extract_transactions_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Extract transactions from PDF.
    Works for PhonePe, Paytm, and standard bank statements.
    Returns list of dicts with keys: date, time, recipient, type, amount, transaction_id, utr_number
    """
    transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')
            for line in lines:
                # Pattern for typical transaction line
                # Example: "01 Apr 2025  10:30  Swiggy  Debit  450.00  T123456789"
                pattern = r"(\d{1,2}\s\w{3}\s\d{4})\s+(\d{2}:\d{2})\s+([A-Za-z0-9\s]+?)\s+(Debit|Credit|Paid|Received)\s+([\d,]+\.?\d*)\s+([A-Z0-9]+)"
                match = re.search(pattern, line)
                if match:
                    date, time, recipient, tx_type, amount_str, tx_id = match.groups()
                    amount = float(amount_str.replace(',', ''))
                    transactions.append({
                        "date": date,
                        "time": time,
                        "recipient": recipient.strip(),
                        "type": tx_type,
                        "amount": amount if tx_type in ["Debit", "Paid"] else -amount,
                        "transaction_id": tx_id,
                        "utr_number": None
                    })
                # Fallback: simpler line parsing
                elif "Debit" in line or "Credit" in line:
                    parts = line.split()
                    # Heuristic: last part is transaction ID, second last is amount, etc.
                    if len(parts) >= 5:
                        amount_str = parts[-2]
                        tx_id = parts[-1]
                        try:
                            amount = float(amount_str.replace(',', ''))
                            transactions.append({
                                "date": parts[0] if len(parts[0]) > 5 else None,
                                "time": None,
                                "recipient": " ".join(parts[1:-3]),
                                "type": "Debit" if "Debit" in line else "Credit",
                                "amount": amount,
                                "transaction_id": tx_id,
                                "utr_number": None
                            })
                        except:
                            pass
    return transactions

# ------------------------------
# 3. ANALYTICS ENGINE
# ------------------------------
def compute_analytics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute key metrics and category breakdown."""
    if df.empty:
        return {"total_spent": 0, "transaction_count": 0, "avg_daily": 0, "top_categories": {}, "top_recipients": []}
    
    # Convert date to datetime
    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date_dt'])
    
    # Debit transactions only (spending)
    spending = df[df['type'].str.lower().isin(['debit', 'paid'])]
    
    total_spent = spending['amount'].sum()
    transaction_count = len(spending)
    
    # Daily average
    if len(spending) > 0:
        days_range = (spending['date_dt'].max() - spending['date_dt'].min()).days
        avg_daily = total_spent / max(days_range, 1)
    else:
        avg_daily = 0
    
    # Simple category mapping
    category_keywords = {
        "Food": ["swiggy", "zomato", "pizza", "restaurant", "starbucks", "dominos"],
        "Shopping": ["amazon", "flipkart", "myntra", "ajio", "mall", "nykaa"],
        "Recharge": ["jio", "airtel", "vi", "recharge", "mobile", "internet"],
        "Bills": ["electricity", "water", "gas", "broadband", "rent"],
        "Travel": ["uber", "ola", "metro", "railway", "flight", "bus"],
        "Entertainment": ["netflix", "prime", "hotstar", "bookmyshow", "spotify"]
    }
    
    category_spend = defaultdict(float)
    for idx, row in spending.iterrows():
        recipient = row['recipient'].lower()
        assigned = False
        for cat, keywords in category_keywords.items():
            if any(kw in recipient for kw in keywords):
                category_spend[cat] += row['amount']
                assigned = True
                break
        if not assigned:
            category_spend["Other"] += row['amount']
    
    # Top recipients
    top_recipients = spending.groupby('recipient')['amount'].sum().sort_values(ascending=False).head(5).to_dict()
    
    return {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "avg_daily": avg_daily,
        "top_categories": dict(category_spend),
        "top_recipients": top_recipients,
        "daily_spending": spending.groupby('date_dt')['amount'].sum().to_dict()
    }

# ------------------------------
# 4. VISUALIZATIONS
# ------------------------------
def create_visualizations(df: pd.DataFrame, analytics: Dict) -> Tuple[plt.Figure, plt.Figure, plt.Figure]:
    """Return spending trend, category pie, and top recipients bar charts."""
    if df.empty:
        fig_empty, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data to display", ha='center')
        return fig_empty, fig_empty, fig_empty
    
    # 1. Spending trend (line plot)
    daily = analytics['daily_spending']
    if daily:
        dates = list(daily.keys())
        amounts = list(daily.values())
        fig_trend, ax = plt.subplots(figsize=(10, 4))
        ax.plot(dates, amounts, marker='o', linestyle='-', color='#1f77b4')
        ax.set_title("Daily Spending Trend", fontsize=14)
        ax.set_xlabel("Date")
        ax.set_ylabel("Amount (₹)")
        plt.xticks(rotation=45)
        plt.tight_layout()
    else:
        fig_trend, ax = plt.subplots()
        ax.text(0.5, 0.5, "Not enough data", ha='center')
    
    # 2. Category pie chart
    categories = analytics['top_categories']
    if categories:
        fig_pie, ax = plt.subplots(figsize=(6, 6))
        ax.pie(categories.values(), labels=categories.keys(), autopct='%1.1f%%', startangle=90)
        ax.set_title("Spending by Category")
        ax.axis('equal')
    else:
        fig_pie, ax = plt.subplots()
        ax.text(0.5, 0.5, "No categories", ha='center')
    
    # 3. Top recipients bar chart
    recipients = analytics['top_recipients']
    if recipients:
        fig_bar, ax = plt.subplots(figsize=(8, 4))
        names = list(recipients.keys())
        amounts = list(recipients.values())
        ax.barh(names, amounts, color='#ff7f0e')
        ax.set_title("Top 5 Recipients by Spending")
        ax.set_xlabel("Amount (₹)")
        ax.invert_yaxis()
        plt.tight_layout()
    else:
        fig_bar, ax = plt.subplots()
        ax.text(0.5, 0.5, "No recipients", ha='center')
    
    return fig_trend, fig_pie, fig_bar

# ------------------------------
# 5. AI SUMMARY (Local Transformer)
# ------------------------------
# Load a small summarization model (cached on first run)
try:
    summarizer = pipeline("summarization", model="Falconsai/text_summarization")
except Exception as e:
    print(f"Warning: Could not load summarizer: {e}")
    summarizer = None

def generate_ai_summary(analytics: Dict) -> str:
    """Produce a natural language summary of the spending."""
    if analytics["transaction_count"] == 0:
        return "No transactions found. Upload a PDF to see your financial summary."
    
    total = analytics["total_spent"]
    count = analytics["transaction_count"]
    avg = analytics["avg_daily"]
    top_cats = analytics["top_categories"]
    top_recip = analytics["top_recipients"]
    
    # Build plain text summary
    category_text = ""
    if top_cats:
        sorted_cats = sorted(top_cats.items(), key=lambda x: x[1], reverse=True)
        top_cat_names = [c[0] for c in sorted_cats[:3]]
        category_text = f"Top spending categories: {', '.join(top_cat_names)}."
    
    recipient_text = ""
    if top_recip:
        top_rec_name = list(top_recip.keys())[0]
        recipient_text = f"Highest payment was to {top_rec_name}."
    
    prompt = (
        f"In the last period, you spent ₹{total:,.2f} across {count} transactions. "
        f"Average daily spend: ₹{avg:,.2f}. {category_text} {recipient_text}"
    )
    
    # If summarizer is available, generate a more fluent summary
    if summarizer:
        try:
            result = summarizer(prompt, max_length=100, min_length=20, do_sample=False)
            return result[0]['summary_text']
        except:
            return prompt
    else:
        return prompt

# ------------------------------
# 6. MAIN GRADIO APP
# ------------------------------
def process_pdf(file):
    """Core function: extract, store, analyze, visualize, summarize."""
    if file is None:
        return "Please upload a PDF file.", None, None, None, None
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file.read())
        tmp_path = tmp_file.name
    
    try:
        # Extract transactions
        transactions = extract_transactions_from_pdf(tmp_path)
        if not transactions:
            return "No transactions found in the PDF. Check format.", None, None, None, None
        
        # Save to database
        inserted = save_transactions(transactions, source_file=file.name)
        
        # Load all historical data
        df = load_all_transactions()
        
        # Compute analytics
        analytics = compute_analytics(df)
        
        # Generate charts
        fig_trend, fig_pie, fig_bar = create_visualizations(df, analytics)
        
        # Generate AI summary
        summary = generate_ai_summary(analytics)
        
        # Prepare metrics display as HTML cards
        metrics_html = f"""
        <div style="display: flex; gap: 20px; margin-bottom: 20px;">
            <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; flex:1; text-align:center;">
                <h3>💰 Total Spent</h3>
                <p style="font-size: 28px;">₹{analytics['total_spent']:,.2f}</p>
            </div>
            <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; flex:1; text-align:center;">
                <h3>🧾 Transactions</h3>
                <p style="font-size: 28px;">{analytics['transaction_count']}</p>
            </div>
            <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; flex:1; text-align:center;">
                <h3>📅 Avg Daily Spend</h3>
                <p style="font-size: 28px;">₹{analytics['avg_daily']:,.2f}</p>
            </div>
        </div>
        """
        
        return metrics_html, fig_trend, fig_pie, fig_bar, summary
    
    except Exception as e:
        return f"Error processing PDF: {str(e)}", None, None, None, None
    finally:
        os.unlink(tmp_path)

# Build Gradio interface
with gr.Blocks(title="Finance AI Dashboard", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 💵 Financial Transaction Analyzer")
    gr.Markdown("Upload your PhonePe, Paytm, or bank statement PDF. The app will extract transactions, store them, and show AI-powered insights.")
    
    with gr.Row():
        pdf_input = gr.File(label="Upload PDF Statement", file_types=[".pdf"])
    
    with gr.Row():
        metrics_output = gr.HTML(label="Financial Overview")
    
    with gr.Row():
        with gr.Column():
            trend_output = gr.Plot(label="Daily Spending Trend")
        with gr.Column():
            pie_output = gr.Plot(label="Spending by Category")
    
    with gr.Row():
        bar_output = gr.Plot(label="Top Recipients")
    
    with gr.Row():
        summary_output = gr.Textbox(label="🤖 AI-Generated Summary", lines=6)
    
    pdf_input.upload(
        fn=process_pdf,
        inputs=pdf_input,
        outputs=[metrics_output, trend_output, pie_output, bar_output, summary_output]
    )
    
    gr.Examples(
        examples=[],  # You can add sample PDFs here
        inputs=pdf_input,
        label="No sample provided – upload your own PDF"
    )

if __name__ == "__main__":
    demo.launch()