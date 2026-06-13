# import streamlit as st
# import pdfplumber
# import pandas as pd
# import re
# from datetime import datetime

# # =========================================================
# # PAGE CONFIG
# # =========================================================
# st.set_page_config(
#     page_title="Financial Transaction Analyzer",
#     page_icon="💰",
#     layout="wide"
# )

# # =========================================================
# # PRE-COMPILED REGEX (Performance Boost)
# # =========================================================
# DATE_PATTERNS = [
#     re.compile(r'[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}'),
#     re.compile(r'[A-Z][a-z]{3,4}\s+\d{1,2},\s+\d{4}'),
#     re.compile(r'\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}'),
#     re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}')
# ]
# EXTRACT_DATE_REGEX = re.compile(r'([A-Z][a-z]{2,4}\s+\d{1,2},\s+\d{4})')
# EXTRACT_TIME_REGEX = re.compile(r'(\d{1,2}:\d{2}\s*[ap]m)')
# DEBIT_REGEX = re.compile(r"Paid to\s+(.+?)(?:\s+DEBIT|\s+₹|$)", re.IGNORECASE)
# CREDIT_REGEX = re.compile(r"Received from\s+(.+?)(?:\s+CREDIT|\s+₹|$)", re.IGNORECASE)
# RUPEE_REGEX = re.compile(r"₹\s*([\d,]+(?:\.\d{1,2})?)")

# # =========================================================
# # HELPER FUNCTION
# # =========================================================
# def clean_amount(value):
#     try:
#         return float(str(value).replace("₹", "").replace(",", "").strip())
#     except Exception:
#         return 0.0

# # ====================================================
# # TRANSACTION EXTRACTOR
# # ====================================================
# class TransactionExtractor:
#     def __init__(self, uploaded_file):
#         self.uploaded_file = uploaded_file
#         self.transactions = []

#     def extract_transactions(self):
#         with pdfplumber.open(self.uploaded_file) as pdf:
#             for page_num, page in enumerate(pdf.pages, start=1):
#                 text = page.extract_text()
#                 if not text:
#                     continue
#                 lines = text.split("\n")
#                 self.transactions.extend(self.process_page(lines, page_num))
#         return self.create_dataframe()

#     def process_page(self, lines, page_num):
#         transactions = []
#         i = 0
#         while i < len(lines):
#             line = lines[i].strip()
#             if self.looks_like_transaction(line):
#                 transaction = self.extract_transaction(lines, i, page_num)
#                 if transaction:
#                     transactions.append(transaction)
#             i += 1
#         return transactions

#     def looks_like_transaction(self, line):
#         has_date = any(pattern.search(line) for pattern in DATE_PATTERNS)
#         has_amount = "₹" in line
#         return has_date and has_amount

#     def extract_transaction(self, lines, start_idx, page_num):
#         try:
#             line1 = lines[start_idx].strip()
#             transaction = {
#                 "page_number": page_num,
#                 "date": None, "time": None,
#                 "receiver_name": None, "type": "UNKNOWN",
#                 "amount": 0.0
#             }

#             # DATE
#             date_match = EXTRACT_DATE_REGEX.search(line1)
#             if date_match:
#                 raw_date = date_match.group(1).replace("Sept", "Sep")
#                 transaction["date"] = raw_date
#                 try:
#                     transaction["parsed_date"] = datetime.strptime(raw_date, '%b %d, %Y')
#                 except ValueError:
#                     transaction["parsed_date"] = None

#             # TIME
#             line_lower = line1.lower()
#             time_match = EXTRACT_TIME_REGEX.search(line_lower)
#             if time_match:
#                 transaction["time"] = time_match.group(1)
#             else:
#                 for offset in [1, 2, 3]:
#                     if start_idx + offset < len(lines):
#                         next_line_lower = lines[start_idx + offset].strip().lower()
#                         time_match = EXTRACT_TIME_REGEX.search(next_line_lower)
#                         if time_match:
#                             transaction["time"] = time_match.group(1)
#                             break

#             # TYPE
#             line_upper = line1.upper()
#             if "CREDIT" in line_upper or "RECEIVED FROM" in line_upper:
#                 transaction["type"] = "CREDIT"
#             elif "DEBIT" in line_upper or "PAID TO" in line_upper:
#                 transaction["type"] = "DEBIT"

#             # RECEIVER NAME
#             debit_match = DEBIT_REGEX.findall(line1)
#             credit_match = CREDIT_REGEX.findall(line1)
#             if debit_match:
#                 transaction["receiver_name"] = debit_match[-1].strip()
#             elif credit_match:
#                 transaction["receiver_name"] = credit_match[-1].strip()

#             # AMOUNT
#             rupee_matches = RUPEE_REGEX.findall(line1)
#             if rupee_matches:
#                 transaction["amount"] = clean_amount(rupee_matches[-1])

#             return transaction
#         except Exception:
#             return None

#     def create_dataframe(self):
#         if not self.transactions:
#             return pd.DataFrame()
#         df = pd.DataFrame(self.transactions)
#         required_columns = ["date", "time", "receiver_name", "type", "amount"]
#         for col in required_columns:
#             if col not in df.columns:
#                 df[col] = None
        
#         df["type"] = df["type"].astype(str).str.upper().str.strip()
#         df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        
#         # =================================================
#         # NORMALIZED RECEIVER NAME
#         # =================================================
#         if "receiver_name" in df.columns:
#             df["receiver_name"] = (
#                 df["receiver_name"]
#                 .str.replace(r'\s+', ' ', regex=True) 
#                 .str.strip()                          
#                 .str.title()                          
#             )

#         # =================================================
#         # SORT BY DATE AND REMOVE PARSED_DATE
#         # =================================================
#         if "parsed_date" in df.columns:
#             df = df.sort_values(by="parsed_date")
#             df = df.drop(columns=["parsed_date"]) 
            
#         return df.reset_index(drop=True)

# # =========================================================
# # CACHED EXTRACTION (Prevents re-running on every click)
# # =========================================================
# @st.cache_data(show_spinner=False)
# def get_pdf_data(uploaded_file):
#     extractor = TransactionExtractor(uploaded_file)
#     return extractor.extract_transactions()

# # =========================================================
# # STREAMLIT UI
# # =========================================================
# st.title("💰 Financial Transaction Analyzer")

# uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])

# if uploaded_file:
#     with st.spinner("Extracting transactions..."):
#         df = get_pdf_data(uploaded_file)

#     if df.empty:
#         st.error("No transactions found in the PDF.")
#     else:
#         # TABS instead of Buttons for a stable UI
#         tab1, tab2, tab3, tab4 = st.tabs([
#             "📌 Extracted Transactions", 
#             "📊 Summary", 
#             "👤 Unique Receivers", 
#             "🏷️ Tag Purposes"
#         ])

#         # --- TAB 1: ALL TRANSACTIONS ---
#         with tab1:
#             st.header("Extracted Transactions")
#             st.dataframe(df, use_container_width=True, height=400)
#             st.download_button(
#                 label="⬇ Download Raw CSV",
#                 data=df.to_csv(index=False).encode("utf-8"),
#                 file_name="transactions_raw.csv",
#                 mime="text/csv"
#             )

#         # --- TAB 2: SUMMARY ---
#         with tab2:
#             st.header("Summary")
#             total_debit = df[df["type"] == "DEBIT"]["amount"].sum()
#             total_credit = df[df["type"] == "CREDIT"]["amount"].sum()
            
#             c1, c2, c3, c4 = st.columns(4)
#             c1.metric("Total Transactions", len(df))
#             c2.metric("Total Debit", f"₹{total_debit:,.2f}")
#             c3.metric("Total Credit", f"₹{total_credit:,.2f}")
#             c4.metric("Unique Receivers", df["receiver_name"].dropna().nunique())

#         # --- TAB 3: UNIQUE RECEIVERS ---
#         with tab3:
#             st.header("Last Unique Receiver Transactions")
#             unique_df = (
#                 df[["date", "time", "receiver_name", "type", "amount"]]
#                 .dropna(subset=["receiver_name"])
#                 .drop_duplicates(subset=["receiver_name", "type"], keep="last")
#                 .reset_index(drop=True)
#                 .rename(columns={
#                     "date": "Last Transaction Date",
#                     "time": "Last Transaction Time",
#                     "receiver_name": "Receiver/Sender Name",
#                     "type": "Transaction Type",
#                     "amount": "Amount"
#                 })
#             )
#             st.dataframe(unique_df, use_container_width=True, height=400)

#         # --- TAB 4: ISOLATED DEBIT & CREDIT TAGGING & SYNC ---
#         with tab4:
#             st.header("Tag Receiver & Sender Purposes")
            
#             # Purpose Lists (Separated for better UX)
#             debit_purposes = [
#                 "Food", "Travel", "Recharge", "Shopping", "Medical", 
#                 "Education", "Entertainment", "Bills", "Rent", "Fuel", 
#                 "Investment", "Transfer", "Family", "Other"
#             ]
            
#             credit_purposes = [
#                 "Salary", "Business", "Transfer", "Cashback", "Refund", 
#                 "Family", "Investment Return", "Other"
#             ]

#             # ==========================================
#             # SEPARATE DATAFRAMES FOR DEBIT & CREDIT
#             # ==========================================
#             # Initialize DEBIT Tagging State
#             if "debit_tagged_df" not in st.session_state:
#                 debit_base_df = (
#                     df[df["type"] == "DEBIT"][["date", "time", "receiver_name", "amount"]]
#                     .dropna(subset=["receiver_name"])
#                     .drop_duplicates(subset=["receiver_name"], keep="last")
#                     .reset_index(drop=True)
#                 )
#                 debit_base_df["purpose"] = "Unassigned"
#                 st.session_state.debit_tagged_df = debit_base_df.copy()

#             # Initialize CREDIT Tagging State
#             if "credit_tagged_df" not in st.session_state:
#                 credit_base_df = (
#                     df[df["type"] == "CREDIT"][["date", "time", "receiver_name", "amount"]]
#                     .dropna(subset=["receiver_name"])
#                     .drop_duplicates(subset=["receiver_name"], keep="last")
#                     .reset_index(drop=True)
#                 )
#                 credit_base_df["purpose"] = "Unassigned"
#                 st.session_state.credit_tagged_df = credit_base_df.copy()

#             # Global Hide Tagged Toggle
#             hide_tagged = st.checkbox("Hide already tagged records", value=True)

#             # ------------------------------------------
#             # SECTION A: DEBIT TAGGING
#             # ------------------------------------------
#             st.subheader("🔴 Debit Tagging (Money Out)")
            
#             if hide_tagged:
#                 debit_filtered = st.session_state.debit_tagged_df[st.session_state.debit_tagged_df["purpose"] == "Unassigned"]
#             else:
#                 debit_filtered = st.session_state.debit_tagged_df

#             debit_list = debit_filtered["receiver_name"].tolist()
            
#             if not debit_list and len(st.session_state.debit_tagged_df) > 0:
#                 st.success("🎉 All Debit transactions have been tagged!")
#             elif len(st.session_state.debit_tagged_df) == 0:
#                 st.info("No debit transactions found to tag.")
#             else:
#                 col_d1, col_d2 = st.columns(2)
#                 with col_d1:
#                     sel_debit_receiver = st.selectbox("Select Debit Receiver", debit_list, key="debit_rec")
#                 with col_d2:
#                     sel_debit_purpose = st.selectbox("Select Debit Purpose", debit_purposes, key="debit_pur")

#                 if st.button("✅ Save Debit Tag"):
#                     st.session_state.debit_tagged_df.loc[
#                         st.session_state.debit_tagged_df["receiver_name"] == sel_debit_receiver,
#                         "purpose"
#                     ] = sel_debit_purpose
#                     st.toast(f"✅ Tagged DEBIT: {sel_debit_receiver} -> {sel_debit_purpose}")
#                     st.rerun()
            
#             with st.expander("View Tagged Debit List"):
#                 st.dataframe(st.session_state.debit_tagged_df, use_container_width=True)

#             st.divider()

#             # ------------------------------------------
#             # SECTION B: CREDIT TAGGING
#             # ------------------------------------------
#             st.subheader("🟢 Credit Tagging (Money In)")
            
#             if hide_tagged:
#                 credit_filtered = st.session_state.credit_tagged_df[st.session_state.credit_tagged_df["purpose"] == "Unassigned"]
#             else:
#                 credit_filtered = st.session_state.credit_tagged_df

#             credit_list = credit_filtered["receiver_name"].tolist()
            
#             if not credit_list and len(st.session_state.credit_tagged_df) > 0:
#                 st.success("🎉 All Credit transactions have been tagged!")
#             elif len(st.session_state.credit_tagged_df) == 0:
#                 st.info("No credit transactions found to tag.")
#             else:
#                 col_c1, col_c2 = st.columns(2)
#                 with col_c1:
#                     sel_credit_receiver = st.selectbox("Select Credit Sender", credit_list, key="credit_rec")
#                 with col_c2:
#                     sel_credit_purpose = st.selectbox("Select Credit Purpose", credit_purposes, key="credit_pur")

#                 if st.button("✅ Save Credit Tag"):
#                     st.session_state.credit_tagged_df.loc[
#                         st.session_state.credit_tagged_df["receiver_name"] == sel_credit_receiver,
#                         "purpose"
#                     ] = sel_credit_purpose
#                     st.toast(f"✅ Tagged CREDIT: {sel_credit_receiver} -> {sel_credit_purpose}")
#                     st.rerun()

#             with st.expander("View Tagged Credit List"):
#                 st.dataframe(st.session_state.credit_tagged_df, use_container_width=True)

#             # ==========================================
#             # MASTER FILE SYNC & DOWNLOAD
#             # ==========================================
#             st.divider()
#             st.subheader("🔄 Apply Tags to Master File")
#             st.write("Click below to apply your Debit and Credit tags safely to the main extracted file.")

#             if st.button("🚀 Sync Tags to All Transactions"):
#                 # 1. Create mapping dictionaries
#                 debit_mapping = dict(zip(
#                     st.session_state.debit_tagged_df["receiver_name"], 
#                     st.session_state.debit_tagged_df["purpose"]
#                 ))
#                 credit_mapping = dict(zip(
#                     st.session_state.credit_tagged_df["receiver_name"], 
#                     st.session_state.credit_tagged_df["purpose"]
#                 ))
                
#                 # 2. Copy original dataframe
#                 master_df = df.copy()
#                 master_df["purpose"] = "Unassigned"
                
#                 # 3. Apply mappings safely based strictly on Type
#                 debit_mask = master_df["type"] == "DEBIT"
#                 master_df.loc[debit_mask, "purpose"] = master_df.loc[debit_mask, "receiver_name"].map(debit_mapping).fillna("Unassigned")
                
#                 credit_mask = master_df["type"] == "CREDIT"
#                 master_df.loc[credit_mask, "purpose"] = master_df.loc[credit_mask, "receiver_name"].map(credit_mapping).fillna("Unassigned")
                
#                 # 4. Store in session state
#                 st.session_state.master_df = master_df
#                 st.success("✅ Master file successfully updated with both Debit and Credit tags!")

#             # If master file exists, show download
#             if "master_df" in st.session_state:
#                 st.subheader("📊 Fully Tagged Master File")
#                 st.dataframe(st.session_state.master_df, use_container_width=True, height=400)

#                 st.download_button(
#                     label="⬇ Download Fully Tagged Master CSV",
#                     data=st.session_state.master_df.to_csv(index=False).encode("utf-8"),
#                     file_name="master_transactions_fully_tagged.csv",
#                     mime="text/csv",
#                     type="primary"
#                 )
import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
import plotly.express as px

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Financial Transaction Analyzer",
    page_icon="💰",
    layout="wide"
)

# =========================================================
# PRE-COMPILED REGEX (Performance Boost)
# =========================================================
DATE_PATTERNS = [
    re.compile(r'[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}'),
    re.compile(r'[A-Z][a-z]{3,4}\s+\d{1,2},\s+\d{4}'),
    re.compile(r'\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}'),
    re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}')
]
EXTRACT_DATE_REGEX = re.compile(r'([A-Z][a-z]{2,4}\s+\d{1,2},\s+\d{4})')
EXTRACT_TIME_REGEX = re.compile(r'(\d{1,2}:\d{2}\s*[ap]m)')
DEBIT_REGEX = re.compile(r"Paid to\s+(.+?)(?:\s+DEBIT|\s+₹|$)", re.IGNORECASE)
CREDIT_REGEX = re.compile(r"Received from\s+(.+?)(?:\s+CREDIT|\s+₹|$)", re.IGNORECASE)
RUPEE_REGEX = re.compile(r"₹\s*([\d,]+(?:\.\d{1,2})?)")

# =========================================================
# HELPER FUNCTION
# =========================================================
def clean_amount(value):
    try:
        return float(str(value).replace("₹", "").replace(",", "").strip())
    except Exception:
        return 0.0

# ====================================================
# TRANSACTION EXTRACTOR
# ====================================================
class TransactionExtractor:
    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file
        self.transactions = []

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
                transaction = self.extract_transaction(lines, i, page_num)
                if transaction:
                    transactions.append(transaction)
            i += 1
        return transactions

    def looks_like_transaction(self, line):
        has_date = any(pattern.search(line) for pattern in DATE_PATTERNS)
        has_amount = "₹" in line
        return has_date and has_amount

    def extract_transaction(self, lines, start_idx, page_num):
        try:
            line1 = lines[start_idx].strip()
            transaction = {
                "page_number": page_num,
                "date": None, "time": None,
                "receiver_name": None, "type": "UNKNOWN",
                "amount": 0.0
            }

            # DATE
            date_match = EXTRACT_DATE_REGEX.search(line1)
            if date_match:
                raw_date = date_match.group(1).replace("Sept", "Sep")
                transaction["date"] = raw_date
                try:
                    transaction["parsed_date"] = datetime.strptime(raw_date, '%b %d, %Y')
                except ValueError:
                    transaction["parsed_date"] = None

            # TIME
            line_lower = line1.lower()
            time_match = EXTRACT_TIME_REGEX.search(line_lower)
            if time_match:
                transaction["time"] = time_match.group(1)
            else:
                for offset in [1, 2, 3]:
                    if start_idx + offset < len(lines):
                        next_line_lower = lines[start_idx + offset].strip().lower()
                        time_match = EXTRACT_TIME_REGEX.search(next_line_lower)
                        if time_match:
                            transaction["time"] = time_match.group(1)
                            break

            # TYPE
            line_upper = line1.upper()
            if "CREDIT" in line_upper or "RECEIVED FROM" in line_upper:
                transaction["type"] = "CREDIT"
            elif "DEBIT" in line_upper or "PAID TO" in line_upper:
                transaction["type"] = "DEBIT"

            # RECEIVER NAME
            debit_match = DEBIT_REGEX.findall(line1)
            credit_match = CREDIT_REGEX.findall(line1)
            if debit_match:
                transaction["receiver_name"] = debit_match[-1].strip()
            elif credit_match:
                transaction["receiver_name"] = credit_match[-1].strip()

            # AMOUNT
            rupee_matches = RUPEE_REGEX.findall(line1)
            if rupee_matches:
                transaction["amount"] = clean_amount(rupee_matches[-1])

            return transaction
        except Exception:
            return None

    def create_dataframe(self):
        if not self.transactions:
            return pd.DataFrame()
        df = pd.DataFrame(self.transactions)
        required_columns = ["date", "time", "receiver_name", "type", "amount"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        
        df["type"] = df["type"].astype(str).str.upper().str.strip()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        
        # =================================================
        # NORMALIZED RECEIVER NAME
        # =================================================
        if "receiver_name" in df.columns:
            df["receiver_name"] = (
                df["receiver_name"]
                .str.replace(r'\s+', ' ', regex=True) 
                .str.strip()                          
                .str.title()                          
            )

        # =================================================
        # SORT BY DATE AND REMOVE PARSED_DATE
        # =================================================
        if "parsed_date" in df.columns:
            df = df.sort_values(by="parsed_date")
            df = df.drop(columns=["parsed_date"]) 
            
        return df.reset_index(drop=True)

# =========================================================
# CACHED EXTRACTION (Prevents re-running on every click)
# =========================================================
@st.cache_data(show_spinner=False)
def get_pdf_data(uploaded_file):
    extractor = TransactionExtractor(uploaded_file)
    return extractor.extract_transactions()

# =========================================================
# STREAMLIT UI
# =========================================================
st.title("💰 Financial Transaction Analyzer")

uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])

if uploaded_file:
    with st.spinner("Extracting transactions..."):
        df = get_pdf_data(uploaded_file)

    if df.empty:
        st.error("No transactions found in the PDF.")
    else:
        # TABS instead of Buttons for a stable UI
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📌 Extracted Transactions", 
            "📊 Summary", 
            "👤 Unique Receivers", 
            "🏷️ Tag Purposes",
            "📈 Visualizations"
        ])

        # --- TAB 1: ALL TRANSACTIONS ---
        with tab1:
            st.header("Extracted Transactions")
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="⬇ Download Raw CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="transactions_raw.csv",
                mime="text/csv"
            )

        # --- TAB 2: SUMMARY ---
        with tab2:
            st.header("Summary")
            total_debit = df[df["type"] == "DEBIT"]["amount"].sum()
            total_credit = df[df["type"] == "CREDIT"]["amount"].sum()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Transactions", len(df))
            c2.metric("Total Debit", f"₹{total_debit:,.2f}")
            c3.metric("Total Credit", f"₹{total_credit:,.2f}")
            c4.metric("Unique Receivers", df["receiver_name"].dropna().nunique())

        # --- TAB 3: UNIQUE RECEIVERS ---
        with tab3:
            st.header("Last Unique Receiver Transactions")
            unique_df = (
                df[["date", "time", "receiver_name", "type", "amount"]]
                .dropna(subset=["receiver_name"])
                .drop_duplicates(subset=["receiver_name", "type"], keep="last")
                .reset_index(drop=True)
                .rename(columns={
                    "date": "Last Transaction Date",
                    "time": "Last Transaction Time",
                    "receiver_name": "Receiver/Sender Name",
                    "type": "Transaction Type",
                    "amount": "Amount"
                })
            )
            st.dataframe(unique_df, use_container_width=True, height=400)

        # --- TAB 4: ISOLATED DEBIT & CREDIT TAGGING & SYNC ---
        with tab4:
            st.header("Tag Receiver & Sender Purposes")
            
            # Purpose Lists
            debit_purposes = [
                "Food", "Travel", "Recharge", "Shopping", "Medical", 
                "Education", "Entertainment", "Bills", "Rent", "Fuel", 
                "Investment", "Transfer", "Family", "Other"
            ]
            
            credit_purposes = [
                "Salary", "Business", "Transfer", "Cashback", "Refund", 
                "Family", "Investment Return", "Other"
            ]

            # Initialize States
            if "debit_tagged_df" not in st.session_state:
                debit_base_df = (
                    df[df["type"] == "DEBIT"][["date", "time", "receiver_name", "amount"]]
                    .dropna(subset=["receiver_name"])
                    .drop_duplicates(subset=["receiver_name"], keep="last")
                    .reset_index(drop=True)
                )
                debit_base_df["purpose"] = "Unassigned"
                st.session_state.debit_tagged_df = debit_base_df.copy()

            if "credit_tagged_df" not in st.session_state:
                credit_base_df = (
                    df[df["type"] == "CREDIT"][["date", "time", "receiver_name", "amount"]]
                    .dropna(subset=["receiver_name"])
                    .drop_duplicates(subset=["receiver_name"], keep="last")
                    .reset_index(drop=True)
                )
                credit_base_df["purpose"] = "Unassigned"
                st.session_state.credit_tagged_df = credit_base_df.copy()

            hide_tagged = st.checkbox("Hide already tagged records", value=True)

            # DEBIT TAGGING
            st.subheader("🔴 Debit Tagging (Money Out)")
            if hide_tagged:
                debit_filtered = st.session_state.debit_tagged_df[st.session_state.debit_tagged_df["purpose"] == "Unassigned"]
            else:
                debit_filtered = st.session_state.debit_tagged_df

            debit_list = debit_filtered["receiver_name"].tolist()
            
            if not debit_list and len(st.session_state.debit_tagged_df) > 0:
                st.success("🎉 All Debit transactions have been tagged!")
            elif len(st.session_state.debit_tagged_df) == 0:
                st.info("No debit transactions found to tag.")
            else:
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    sel_debit_receiver = st.selectbox("Select Debit Receiver", debit_list, key="debit_rec")
                with col_d2:
                    sel_debit_purpose = st.selectbox("Select Debit Purpose", debit_purposes, key="debit_pur")

                if st.button("✅ Save Debit Tag"):
                    st.session_state.debit_tagged_df.loc[
                        st.session_state.debit_tagged_df["receiver_name"] == sel_debit_receiver,
                        "purpose"
                    ] = sel_debit_purpose
                    st.toast(f"✅ Tagged DEBIT: {sel_debit_receiver} -> {sel_debit_purpose}")
                    st.rerun()
            
            with st.expander("View Tagged Debit List"):
                st.dataframe(st.session_state.debit_tagged_df, use_container_width=True)

            st.divider()

            # CREDIT TAGGING
            st.subheader("🟢 Credit Tagging (Money In)")
            if hide_tagged:
                credit_filtered = st.session_state.credit_tagged_df[st.session_state.credit_tagged_df["purpose"] == "Unassigned"]
            else:
                credit_filtered = st.session_state.credit_tagged_df

            credit_list = credit_filtered["receiver_name"].tolist()
            
            if not credit_list and len(st.session_state.credit_tagged_df) > 0:
                st.success("🎉 All Credit transactions have been tagged!")
            elif len(st.session_state.credit_tagged_df) == 0:
                st.info("No credit transactions found to tag.")
            else:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    sel_credit_receiver = st.selectbox("Select Credit Sender", credit_list, key="credit_rec")
                with col_c2:
                    sel_credit_purpose = st.selectbox("Select Credit Purpose", credit_purposes, key="credit_pur")

                if st.button("✅ Save Credit Tag"):
                    st.session_state.credit_tagged_df.loc[
                        st.session_state.credit_tagged_df["receiver_name"] == sel_credit_receiver,
                        "purpose"
                    ] = sel_credit_purpose
                    st.toast(f"✅ Tagged CREDIT: {sel_credit_receiver} -> {sel_credit_purpose}")
                    st.rerun()

            with st.expander("View Tagged Credit List"):
                st.dataframe(st.session_state.credit_tagged_df, use_container_width=True)

            # MASTER FILE SYNC
            st.divider()
            st.subheader("🔄 Apply Tags to Master File")
            
            if st.button("🚀 Sync Tags to All Transactions"):
                debit_mapping = dict(zip(st.session_state.debit_tagged_df["receiver_name"], st.session_state.debit_tagged_df["purpose"]))
                credit_mapping = dict(zip(st.session_state.credit_tagged_df["receiver_name"], st.session_state.credit_tagged_df["purpose"]))
                
                master_df = df.copy()
                master_df["purpose"] = "Unassigned"
                
                debit_mask = master_df["type"] == "DEBIT"
                master_df.loc[debit_mask, "purpose"] = master_df.loc[debit_mask, "receiver_name"].map(debit_mapping).fillna("Unassigned")
                
                credit_mask = master_df["type"] == "CREDIT"
                master_df.loc[credit_mask, "purpose"] = master_df.loc[credit_mask, "receiver_name"].map(credit_mapping).fillna("Unassigned")
                
                st.session_state.master_df = master_df
                st.success("✅ Master file successfully updated!")

            if "master_df" in st.session_state:
                st.subheader("📊 Fully Tagged Master File")
                st.dataframe(st.session_state.master_df, use_container_width=True, height=400)
                st.download_button(
                    label="⬇ Download Fully Tagged Master CSV",
                    data=st.session_state.master_df.to_csv(index=False).encode("utf-8"),
                    file_name="master_transactions_fully_tagged.csv",
                    mime="text/csv",
                    type="primary"
                )

        # --- TAB 5: VISUALIZATIONS ---
        with tab5:
            st.header("📈 Financial Analysis & Visualizations")

            # Determine which dataframe to use (Tagged Master if it exists, otherwise Raw)
            viz_df = st.session_state.get("master_df", df).copy()
            
            # Recreate parsed_date for the timeline graph temporarily
            viz_df['temp_date'] = pd.to_datetime(viz_df['date'], format='%b %d, %Y', errors='coerce')

            # Decide what to group the pie charts by
            # If the user clicked "Sync Tags" in Tab 4, we use "purpose". If not, we fall back to "receiver_name"
            grouping_col = "purpose" if "purpose" in viz_df.columns else "receiver_name"

            # ------------------------------------------
            # 1. PIE CHARTS (Debit & Credit)
            # ------------------------------------------
            st.subheader("🍩 Income vs. Expense Distribution")
            
            col_pie1, col_pie2 = st.columns(2)

            with col_pie1:
                st.markdown("#### Debit (Money Out)")
                debit_data = viz_df[viz_df["type"] == "DEBIT"]
                
                if not debit_data.empty:
                    # Group by the category and sum the amounts
                    debit_agg = debit_data.groupby(grouping_col, as_index=False)["amount"].sum()
                    
                    fig_debit = px.pie(
                        debit_agg, 
                        values='amount', 
                        names=grouping_col, 
                        hole=0.4, # Creates the donut style
                        color_discrete_sequence=px.colors.sequential.Reds_r
                    )
                    fig_debit.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_debit, use_container_width=True)
                else:
                    st.info("No debit transactions to display.")

            with col_pie2:
                st.markdown("#### Credit (Money In)")
                credit_data = viz_df[viz_df["type"] == "CREDIT"]
                
                if not credit_data.empty:
                    credit_agg = credit_data.groupby(grouping_col, as_index=False)["amount"].sum()
                    
                    fig_credit = px.pie(
                        credit_agg, 
                        values='amount', 
                        names=grouping_col, 
                        hole=0.4,
                        color_discrete_sequence=px.colors.sequential.Greens_r
                    )
                    fig_credit.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_credit, use_container_width=True)
                else:
                    st.info("No credit transactions to display.")

            st.divider()

            # ------------------------------------------
            # 2. LINE CHART (Trend Over Time)
            # ------------------------------------------
            st.subheader("📉 Cash Flow Trend")
            
            trend_df = viz_df.dropna(subset=['temp_date']).copy()

            if not trend_df.empty:
                time_interval = st.selectbox("Select View Interval", ["Daily", "Weekly", "Monthly"])

                # Map selection to Pandas datetime frequency rules
                freq_map = {"Daily": "D", "Weekly": "W-MON", "Monthly": "ME"}
                
                # Group by the time interval and type (Credit vs Debit)
                time_agg = (
                    trend_df.groupby([pd.Grouper(key='temp_date', freq=freq_map[time_interval]), 'type'])['amount']
                    .sum()
                    .reset_index()
                )

                # Generate interactive line chart
                fig_trend = px.line(
                    time_agg,
                    x='temp_date',
                    y='amount',
                    color='type',
                    markers=True,
                    labels={"temp_date": "Date", "amount": "Amount (₹)", "type": "Transaction Type"},
                    color_discrete_map={"CREDIT": "#28a745", "DEBIT": "#dc3545"} # Green for Credit, Red for Debit
                )
                
                fig_trend.update_layout(hovermode="x unified")
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.warning("Not enough valid dates to plot trends.")
