# import streamlit as st
# import pdfplumber
# import pandas as pd
# import re
# from datetime import datetime

# # ====================================================
# # PAGE CONFIG
# # ===================================================

# st.set_page_config(
#     page_title="Financial Transaction Analyzer",
#     page_icon="💰",
#     layout="wide"
# )

# # =======================================
# # HELPER FUNCTION
# # ========================================

# def clean_amount(value):

#     try:
#         return float(
#             str(value)
#             .replace("₹", "")
#             .replace(",", "")
#             .strip()
#         )

#     except:
#         return 0.0


# # =========================================================
# # TRANSACTION EXTRACTOR
# # =========================================================

# class TransactionExtractor:

#     def __init__(self, uploaded_file):

#         self.uploaded_file = uploaded_file
#         self.transactions = []

#     # =====================================================
#     # MAIN EXTRACTION
#     # =====================================================

#     def extract_transactions(self):

#         with pdfplumber.open(self.uploaded_file) as pdf:

#             for page_num, page in enumerate(pdf.pages, start=1):

#                 text = page.extract_text()

#                 if not text:
#                     continue

#                 lines = text.split("\n")

#                 page_transactions = self.process_page(
#                     lines,
#                     page_num
#                 )

#                 if page_transactions:
#                     self.transactions.extend(page_transactions)

#         return self.create_dataframe()

#     # =====================================================
#     # PROCESS PAGE
#     # =====================================================

#     def process_page(self, lines, page_num):

#         transactions = []

#         i = 0

#         while i < len(lines):

#             line = lines[i].strip()

#             if self.looks_like_transaction(line):

#                 transaction = self.extract_transaction(
#                     lines,
#                     i,
#                     page_num
#                 )

#                 if transaction:
#                     transactions.append(transaction)

#                 i += 1

#             else:
#                 i += 1

#         return transactions

#     # =====================================================
#     # DETECT TRANSACTION LINE
#     # =====================================================

#     def looks_like_transaction(self, line):

#         date_patterns = [

#             r'[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}',

#             r'[A-Z][a-z]{3,4}\s+\d{1,2},\s+\d{4}',

#             r'\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}',

#             r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
#         ]

#         has_date = False

#         for pattern in date_patterns:

#             if re.search(pattern, line):
#                 has_date = True
#                 break

#         has_amount = "₹" in line

#         return has_date and has_amount

#     # =====================================================
#     # EXTRACT TRANSACTION
#     # =====================================================

#     def extract_transaction(
#         self,
#         lines,
#         start_idx,
#         page_num
#     ):

#         try:

#             line1 = lines[start_idx].strip()

#             transaction = {
#                 "page_number": page_num,
#                 "date": None,
#                 "time": None,
#                 "receiver_name": None,
#                 "type": None,
#                 "amount": 0.0
#             }

#             # =================================================
#             # DATE
#             # =================================================

#             date_match = re.search(
#                 r'([A-Z][a-z]{2,4}\s+\d{1,2},\s+\d{4})',
#                 line1
#             )

#             if date_match:

#                 raw_date = date_match.group(1)

#                 raw_date = raw_date.replace(
#                     "Sept",
#                     "Sep"
#                 )

#                 transaction["date"] = raw_date

#                 try:

#                     transaction["parsed_date"] = datetime.strptime(
#                         raw_date,
#                         '%b %d, %Y'
#                     )

#                 except:

#                     transaction["parsed_date"] = None

#             # =================================================
#             # TIME
#             # =================================================

#             time_match = re.search(
#                 r'(\d{1,2}:\d{2}\s*[ap]m)',
#                 line1.lower()
#             )

#             if time_match:

#                 transaction["time"] = (
#                     time_match.group(1)
#                 )

#             if not transaction["time"]:

#                 for offset in [1, 2, 3]:

#                     if start_idx + offset < len(lines):

#                         next_line = lines[
#                             start_idx + offset
#                         ].strip()

#                         time_match = re.search(
#                             r'(\d{1,2}:\d{2}\s*[ap]m)',
#                             next_line.lower()
#                         )

#                         if time_match:

#                             transaction["time"] = (
#                                 time_match.group(1)
#                             )

#                             break

#             # =================================================
#             # TYPE
#             # =================================================

#             line_upper = line1.upper()

#             if (
#                 "CREDIT" in line_upper
#                 or "RECEIVED FROM" in line_upper
#             ):

#                 transaction["type"] = "CREDIT"

#             elif (
#                 "DEBIT" in line_upper
#                 or "PAID TO" in line_upper
#             ):

#                 transaction["type"] = "DEBIT"

#             else:

#                 transaction["type"] = "UNKNOWN"

#             # =================================================
#             # RECEIVER NAME
#             # =================================================

#             debit_match = re.findall(
#                 r"Paid to\s+(.+?)(?:\s+DEBIT|\s+₹|$)",
#                 line1,
#                 re.IGNORECASE
#             )

#             credit_match = re.findall(
#                 r"Received from\s+(.+?)(?:\s+CREDIT|\s+₹|$)",
#                 line1,
#                 re.IGNORECASE
#             )

#             if debit_match:

#                 transaction["receiver_name"] = (
#                     debit_match[-1].strip()
#                 )

#             elif credit_match:
#                 transaction["receiver_name"] = (
#                     credit_match[-1].strip()
#                 )
#             # =================================================
#             # AMOUNT
#             # =================================================

#             rupee_matches = re.findall(
#                 r"₹\s*([\d,]+(?:\.\d{1,2})?)",
#                 line1
#             )

#             if rupee_matches:

#                 transaction["amount"] = clean_amount(
#                     rupee_matches[-1]
#                 )

#             else:

#                 transaction["amount"] = 0.0

#             return transaction

#         except Exception:
#             return None

#     # =====================================================
#     # CREATE DATAFRAME
#     # =====================================================

#     def create_dataframe(self):

#         if not self.transactions:
#             return pd.DataFrame()

#         df = pd.DataFrame(self.transactions)

#         required_columns = [
#             "date",
#             "time",
#             "receiver_name",
#             "type",
#             "amount"
#         ]

#         for col in required_columns:

#             if col not in df.columns:
#                 df[col] = None

#         df["type"] = (
#             df["type"]
#             .astype(str)
#             .str.upper()
#             .str.strip()
#         )

#         df["amount"] = pd.to_numeric(
#             df["amount"],
#             errors="coerce"
#         ).fillna(0)

#         if "parsed_date" in df.columns:

#             df = df.sort_values(
#                 by="parsed_date"
#             )

#         return df.reset_index(drop=True)


# # =========================================================
# # STREAMLIT UI
# # =========================================================

# st.title("💰 Financial Transaction Analyzer")

# uploaded_file = st.file_uploader(
#     "Upload PDF File",
#     type=["pdf"]
# )

# # =========================================================
# # PROCESS FILE
# # =========================================================

# if uploaded_file:

#     with st.spinner("Extracting transactions..."):

#         extractor = TransactionExtractor(
#             uploaded_file
#         )

#         df = extractor.extract_transactions()

#     if df.empty:

#         st.error(
#             "No transactions found in the PDF."
#         )

#     else:

#         # =================================================
#         # BUTTONS
#         # =================================================

#         st.subheader("📂 Analysis Sections")

#         col1, col2, col3 = st.columns(3)

#         with col1:
#             show_stage1 = st.button(
#                 "📌 Show Extracted Transactions"
#             )

#         with col2:
#             show_stage2 = st.button(
#                 "📊 Show Summary"
#             )

#         with col3:
#             show_stage3 = st.button(
#                 "👤 Show Unique Receivers"
#             )

#         # =================================================
#         # STAGE 1
#         # =================================================

#         if show_stage1:

#             st.header(
#                 "📌 Stage 1: Extracted Transactions"
#             )

#             st.dataframe(
#                 df,
#                 use_container_width=True,
#                 height=450
#             )

#         # =================================================
#         # STAGE 2
#         # =================================================

#         if show_stage2:

#             st.header(
#                 "📊 Stage 2: Summary"
#             )

#             debit_df = df[
#                 df["type"] == "DEBIT"
#             ]

#             credit_df = df[
#                 df["type"] == "CREDIT"
#             ]

#             total_debit = (
#                 debit_df["amount"].sum()
#             )

#             total_credit = (
#                 credit_df["amount"].sum()
#             )

#             total_transactions = len(df)

#             unique_receivers = (
#                 df["receiver_name"]
#                 .dropna()
#                 .nunique()
#             )

#             c1, c2, c3, c4 = st.columns(4)

#             c1.metric(
#                 "Total Transactions",
#                 total_transactions
#             )

#             c2.metric(
#                 "Total Debit",
#                 f"₹{total_debit:,.2f}"
#             )

#             c3.metric(
#                 "Total Credit",
#                 f"₹{total_credit:,.2f}"
#             )

#             c4.metric(
#                 "Unique Receivers",
#                 unique_receivers
#             )

#         # =================================================
#         # STAGE 3
#         # =================================================

#         if show_stage3:

#             st.header(
#                 "👤 Stage 3: Last Unique Receiver Transactions"
#             )

#             unique_df = (

#                 df[
#                     [
#                         "date",
#                         "time",
#                         "receiver_name",
#                         "amount"
#                     ]
#                 ]

#                 .dropna(
#                     subset=["receiver_name"]
#                 )

#                 .drop_duplicates(
#                     subset=["receiver_name"],
#                     keep="last"
#                 )

#                 .reset_index(drop=True)
#             )

#             unique_df = unique_df.rename(
#                 columns={
#                     "date": "Last Transaction Date",
#                     "time": "Last Transaction Time",
#                     "receiver_name": "Receiver Name",
#                     "amount": "Amount"
#                 }
#             )

#             st.dataframe(
#                 unique_df,
#                 use_container_width=True,
#                 height=500
#             )

#         # =================================================
#         # DOWNLOAD CSV
#         # =================================================

#         st.download_button(
#             label="⬇ Download CSV",
#             data=df.to_csv(index=False).encode("utf-8"),
#             file_name="transactions.csv",
#             mime="text/csv"
#         )
#         # =========================================================
#         # STAGE 4 : MANUAL PURPOSE TAGGING
#         # ADD THIS BELOW STAGE 3 IN STREAMLIT
#         # =========================================================
        
#         st.header(
#             "🏷️ Stage 4: Tag Receiver Purpose"
#         )
        
#         # ---------------------------------------------------------
#         # CREATE UNIQUE RECEIVER TABLE
#         # ---------------------------------------------------------
        
#         tagging_df = (
        
#             df[
#                 [
#                     "date",
#                     "time",
#                     "receiver_name",
#                     "amount"
#                 ]
#             ]
        
#             .dropna(
#                 subset=["receiver_name"]
#             )
        
#             .drop_duplicates(
#                 subset=["receiver_name"],
#                 keep="last"
#             )
        
#             .reset_index(drop=True)
#         )
        
#         # ---------------------------------------------------------
#         # SESSION STATE
#         # ---------------------------------------------------------
        
#         if "tagged_df" not in st.session_state:
        
#             tagging_df["purpose"] = "Unassigned"
        
#             st.session_state.tagged_df = tagging_df.copy()
        
#         # ---------------------------------------------------------
#         # PURPOSE OPTIONS
#         # ---------------------------------------------------------
        
#         purpose_options = [
        
#             "Food",
#             "Travel",
#             "Recharge",
#             "Shopping",
#             "Medical",
#             "Education",
#             "Entertainment",
#             "Bills",
#             "Rent",
#             "Fuel",
#             "Investment",
#             "Transfer",
#             "Family",
#             "Salary",
#             "Other"
#         ]
        
#         # ---------------------------------------------------------
#         # SELECT RECEIVER
#         # ---------------------------------------------------------
        
#         receiver_list = st.session_state.tagged_df[
#             "receiver_name"
#         ].tolist()
        
#         selected_receiver = st.selectbox(
#             "Select Receiver Name",
#             receiver_list
#         )
        
#         # ---------------------------------------------------------
#         # SELECT PURPOSE
#         # ---------------------------------------------------------
        
#         selected_purpose = st.selectbox(
#             "Select Purpose",
#             purpose_options
#         )
        
#         # ---------------------------------------------------------
#         # SAVE BUTTON
#         # ---------------------------------------------------------
        
#         if st.button("✅ Save Purpose Tag"):
        
#             st.session_state.tagged_df.loc[
#                 st.session_state.tagged_df[
#                     "receiver_name"
#                 ] == selected_receiver,
#                 "purpose"
#             ] = selected_purpose
        
#             st.success(
#                 f"Purpose updated for {selected_receiver}"
#             )
        
#         # ---------------------------------------------------------
#         # DISPLAY UPDATED TABLE
#         # ---------------------------------------------------------
        
#         st.subheader(
#             "📋 Tagged Receiver Table"
#         )
        
#         st.dataframe(
#             st.session_state.tagged_df,
#             use_container_width=True,
#             height=500
#         )
        
#         # ---------------------------------------------------------
#         # DOWNLOAD TAGGED CSV
#         # ---------------------------------------------------------
        
#         tagged_csv = (
#             st.session_state.tagged_df
#             .to_csv(index=False)
#             .encode("utf-8")
#         )
        
#         st.download_button(
#             label="⬇ Download Tagged CSV",
#             data=tagged_csv,
#             file_name="tagged_receivers.csv",
#             mime="text/csv"
#         )
import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime

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
        # Removes double spaces, strips ends, applies Title Case
        # =================================================
        if "receiver_name" in df.columns:
            df["receiver_name"] = (
                df["receiver_name"]
                .str.replace(r'\s+', ' ', regex=True) # Collapse multiple spaces into one
                .str.strip()                          # Remove leading/trailing whitespaces
                .str.title()                          # Convert to Title Case (e.g. "JOHN DOE" -> "John Doe")
            )

        if "parsed_date" in df.columns:
            df = df.sort_values(by="parsed_date")
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
        tab1, tab2, tab3, tab4 = st.tabs([
            "📌 Extracted Transactions", 
            " Summary", 
            "👤 Unique Receivers", 
            "🏷️ Tag Purposes"
        ])

        # --- TAB 1: ALL TRANSACTIONS ---
        with tab1:
            st.header("Extracted Transactions")
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button(
                label="⬇ Download CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="transactions.csv",
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
                df[["date", "time", "receiver_name", "amount"]]
                .dropna(subset=["receiver_name"])
                .drop_duplicates(subset=["receiver_name"], keep="last")
                .reset_index(drop=True)
                .rename(columns={
                    "date": "Last Transaction Date",
                    "time": "Last Transaction Time",
                    "receiver_name": "Receiver Name",
                    "amount": "Amount"
                })
            )
            st.dataframe(unique_df, use_container_width=True, height=400)

        # --- TAB 4: MANUAL PURPOSE TAGGING ---
        with tab4:
            st.header("Tag Receiver Purpose")
            
            # Base table for tagging
            tagging_base_df = (
                df[["date", "time", "receiver_name", "amount"]]
                .dropna(subset=["receiver_name"])
                .drop_duplicates(subset=["receiver_name"], keep="last")
                .reset_index(drop=True)
            )

            # Initialize session state for tags if it doesn't exist
            if "tagged_df" not in st.session_state:
                tagging_base_df["purpose"] = "Unassigned"
                st.session_state.tagged_df = tagging_base_df.copy()

            purpose_options = [
                "Food", "Travel", "Recharge", "Shopping", "Medical", 
                "Education", "Entertainment", "Bills", "Rent", "Fuel", 
                "Investment", "Transfer", "Family", "Salary", "Other"
            ]

            receiver_list = st.session_state.tagged_df["receiver_name"].tolist()
            
            col_a, col_b = st.columns(2)
            with col_a:
                selected_receiver = st.selectbox("Select Receiver Name", receiver_list)
            with col_b:
                selected_purpose = st.selectbox("Select Purpose", purpose_options)

            if st.button("✅ Save Purpose Tag"):
                st.session_state.tagged_df.loc[
                    st.session_state.tagged_df["receiver_name"] == selected_receiver,
                    "purpose"
                ] = selected_purpose
                st.success(f"Purpose updated for {selected_receiver}")

            st.subheader("📋 Tagged Receiver Table")
            st.dataframe(st.session_state.tagged_df, use_container_width=True, height=400)

            st.download_button(
                label="⬇ Download Tagged CSV",
                data=st.session_state.tagged_df.to_csv(index=False).encode("utf-8"),
                file_name="tagged_receivers.csv",
                mime="text/csv"
            )
