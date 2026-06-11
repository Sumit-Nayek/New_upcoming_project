
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
#         # Removes double spaces, strips ends, applies Title Case
#         # =================================================
#         if "receiver_name" in df.columns:
#             df["receiver_name"] = (
#                 df["receiver_name"]
#                 .str.replace(r'\s+', ' ', regex=True) # Collapse multiple spaces into one
#                 .str.strip()                          # Remove leading/trailing whitespaces
#                 .str.title()                          # Convert to Title Case (e.g. "JOHN DOE" -> "John Doe")
#             )

#         if "parsed_date" in df.columns:
#             df = df.sort_values(by="parsed_date")
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
#             " Summary", 
#             "👤 Unique Receivers", 
#             "🏷️ Tag Purposes"
#         ])

#         # --- TAB 1: ALL TRANSACTIONS ---
#         with tab1:
#             st.header("Extracted Transactions")
#             st.dataframe(df, use_container_width=True, height=400)
#             st.download_button(
#                 label="⬇ Download CSV",
#                 data=df.to_csv(index=False).encode("utf-8"),
#                 file_name="transactions.csv",
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
#                 df[["date", "time", "receiver_name", "amount"]]
#                 .dropna(subset=["receiver_name"])
#                 .drop_duplicates(subset=["receiver_name"], keep="last")
#                 .reset_index(drop=True)
#                 .rename(columns={
#                     "date": "Last Transaction Date",
#                     "time": "Last Transaction Time",
#                     "receiver_name": "Receiver Name",
#                     "amount": "Amount"
#                 })
#             )
#             st.dataframe(unique_df, use_container_width=True, height=400)

#         # --- TAB 4: MANUAL PURPOSE TAGGING ---
#         # --- TAB 4: MANUAL PURPOSE TAGGING ---
#         with tab4:
#             st.header("Tag Receiver Purpose")
            
#             # Base table for tagging
#             tagging_base_df = (
#                 df[["date", "time", "receiver_name", "amount"]]
#                 .dropna(subset=["receiver_name"])
#                 .drop_duplicates(subset=["receiver_name"], keep="last")
#                 .reset_index(drop=True)
#             )

#             # Initialize session state for tags if it doesn't exist
#             if "tagged_df" not in st.session_state:
#                 tagging_base_df["purpose"] = "Unassigned"
#                 st.session_state.tagged_df = tagging_base_df.copy()

#             purpose_options = [
#                 "Food", "Travel", "Recharge", "Shopping", "Medical", 
#                 "Education", "Entertainment", "Bills", "Rent", "Fuel", 
#                 "Investment", "Transfer", "Family", "Salary", "Other"
#             ]

#             # ==========================================
#             # SMART DROPDOWN LOGIC
#             # ==========================================
#             # 1. Toggle to hide receivers that are already tagged
#             hide_tagged = st.checkbox("Hide already tagged receivers", value=True)
            
#             if hide_tagged:
#                 filtered_df = st.session_state.tagged_df[
#                     st.session_state.tagged_df["purpose"] == "Unassigned"
#                 ]
#             else:
#                 filtered_df = st.session_state.tagged_df

#             receiver_list = filtered_df["receiver_name"].tolist()
            
#             # 2. Check if the list is empty (User finished tagging)
#             if not receiver_list and hide_tagged:
#                 st.success("🎉 All receivers have been tagged!")
#             else:
#                 col_a, col_b = st.columns(2)
#                 with col_a:
#                     selected_receiver = st.selectbox("Select Receiver Name", receiver_list)
#                 with col_b:
#                     selected_purpose = st.selectbox("Select Purpose", purpose_options)

#                 if st.button("✅ Save Purpose Tag"):
#                     # Update the purpose in session state
#                     st.session_state.tagged_df.loc[
#                         st.session_state.tagged_df["receiver_name"] == selected_receiver,
#                         "purpose"
#                     ] = selected_purpose
                    
#                     # Use toast instead of success so the message survives the rerun
#                     st.toast(f"✅ Tagged {selected_receiver} as {selected_purpose}")
                    
#                     # 3. Force an immediate UI refresh to update the dropdown
#                     st.rerun()

#             # ==========================================
#             # DISPLAY AND DOWNLOAD
#             # ==========================================
#             st.subheader("📋 Tagged Receiver Table")
#             st.dataframe(st.session_state.tagged_df, use_container_width=True, height=400)

#             st.download_button(
#                 label="⬇ Download Tagged CSV",
#                 data=st.session_state.tagged_df.to_csv(index=False).encode("utf-8"),
#                 file_name="tagged_receivers.csv",
#                 mime="text/csv"
#             )
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
            "📊 Summary", 
            "👤 Unique Receivers", 
            "🏷️ Tag Purposes"
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

        # --- TAB 4: MANUAL PURPOSE TAGGING & SYNC ---
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

            # ==========================================
            # SMART DROPDOWN LOGIC
            # ==========================================
            hide_tagged = st.checkbox("Hide already tagged receivers", value=True)
            
            if hide_tagged:
                filtered_df = st.session_state.tagged_df[
                    st.session_state.tagged_df["purpose"] == "Unassigned"
                ]
            else:
                filtered_df = st.session_state.tagged_df

            receiver_list = filtered_df["receiver_name"].tolist()
            
            if not receiver_list and hide_tagged:
                st.success("🎉 All receivers have been tagged! You can now sync them to the master file.")
            else:
                col_a, col_b = st.columns(2)
                with col_a:
                    selected_receiver = st.selectbox("Select Receiver Name", receiver_list)
                with col_b:
                    selected_purpose = st.selectbox("Select Purpose", purpose_options)

                if st.button("✅ Save Purpose Tag"):
                    # Update the purpose in session state
                    st.session_state.tagged_df.loc[
                        st.session_state.tagged_df["receiver_name"] == selected_receiver,
                        "purpose"
                    ] = selected_purpose
                    
                    st.toast(f"✅ Tagged {selected_receiver} as {selected_purpose}")
                    st.rerun()

            st.subheader("📋 Unique Receivers List")
            st.dataframe(st.session_state.tagged_df, use_container_width=True, height=300)

            # ==========================================
            # MASTER FILE SYNC & DOWNLOAD
            # ==========================================
            st.divider()
            st.subheader("🔄 Apply Tags to Master File")
            st.write("Click below to apply your tags to every single transaction in your original file.")

            if st.button("🚀 Sync Tags to All Transactions"):
                # 1. Create a dictionary mapping of {Receiver: Purpose}
                tag_mapping = dict(
                    zip(
                        st.session_state.tagged_df["receiver_name"], 
                        st.session_state.tagged_df["purpose"]
                    )
                )
                
                # 2. Copy the original DataFrame and map the purposes
                master_df = df.copy()
                master_df["purpose"] = master_df["receiver_name"].map(tag_mapping).fillna("Unassigned")
                
                # 3. Store in session state to persist it
                st.session_state.master_df = master_df
                st.success("✅ Master file successfully updated with all your tags!")

            # If the master file exists in session state, display it and provide the download button
            if "master_df" in st.session_state:
                st.subheader("📊 Fully Tagged Master File")
                st.dataframe(st.session_state.master_df, use_container_width=True, height=400)

                st.download_button(
                    label="⬇ Download Fully Tagged Master CSV",
                    data=st.session_state.master_df.to_csv(index=False).encode("utf-8"),
                    file_name="master_transactions_tagged.csv",
                    mime="text/csv",
                    type="primary" # Highlights the button in Streamlit
                )
