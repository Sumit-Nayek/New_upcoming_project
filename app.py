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
# HELPER FUNCTION
# =========================================================


def clean_amount(value):

    try:
        return float(
            str(value)
            .replace("₹", "")
            .replace(",", "")
            .strip()
        )

    except:
        return 0.0


# =========================================================
# TRANSACTION EXTRACTOR
# =========================================================


class TransactionExtractor:

    def __init__(self, uploaded_file):

        self.uploaded_file = uploaded_file
        self.transactions = []

    # =====================================================
    # MAIN EXTRACTION
    # =====================================================

    def extract_transactions(self):

        with pdfplumber.open(self.uploaded_file) as pdf:

            for page_num, page in enumerate(pdf.pages, start=1):

                text = page.extract_text()

                if not text:
                    continue

                lines = text.split("\n")

                page_transactions = self.process_page(
                    lines,
                    page_num
                )
        )
