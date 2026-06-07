
# 💰 Financial Transaction Analyzer

A fast, interactive web application built with Streamlit that extracts, analyzes, and categorizes transaction data from bank statement PDFs. 

By leveraging pre-compiled regular expressions and cached data processing, this tool instantly parses complex financial documents into readable tables, provides high-level financial summaries, and allows users to manually tag transactions by category for better expense tracking.

## ✨ Features

* **Automated PDF Parsing:** Quickly reads and extracts text from multi-page PDF bank statements using `pdfplumber`.
* **Smart Data Extraction:** Uses optimized, pre-compiled regex to accurately identify dates, times, transaction types (Credit/Debit), receiver/sender names, and amounts.
* **Performance Optimized:** Utilizes Streamlit's `@st.cache_data` to ensure the PDF is only processed once, making UI interactions (like switching tabs or tagging) instantaneous.
* **Interactive Dashboard:** * **Extracted Transactions:** View the raw data in a clean data frame.
  * **Summary Metrics:** At-a-glance view of total transactions, total debit, total credit, and unique receiver counts.
  * **Unique Receivers:** Tracks the most recent transaction details for each unique receiver.
  * **Manual Tagging System:** Assign specific purposes (e.g., Food, Rent, Salary, Bills) to unique receivers and save the categorized data.
* **Export Ready:** Download both your raw extracted transactions and your newly tagged receiver lists as CSV files for use in Excel or other accounting software.

## 🛠️ Prerequisites

Ensure you have Python 3.7 or higher installed on your machine. You will need the following Python libraries:

* `streamlit`
* `pdfplumber`
* `pandas`


**Access the App:**
Your default web browser should automatically open the app at `http://localhost:8501`.

## 📖 How to Use

1. **Upload a Statement:** Click on the **"Upload PDF File"** button and select a valid bank statement PDF.
2. **Review Extracted Data (Tab 1):** Once processed, view the extracted dates, times, types, and amounts. You can download this raw data as a CSV.
3. **Check the Summary (Tab 2):** View your total spending (Debit) versus income (Credit).
4. **Tag Your Expenses (Tab 4):** * Go to the **"Tag Purposes"** tab.
* Select a receiver from the dropdown list.
* Assign a category (e.g., "Food", "Travel", "Investment").
* Click **"Save Purpose Tag"**.
* Download your finalized, categorized list as a CSV when you are done.



## 🧩 Code Architecture Overview

* **Regex Compilation:** Regular expressions are compiled globally at the start of the script to drastically reduce execution time during the line-by-line text parsing.
* **`TransactionExtractor` Class:** Handles the core logic of reading the PDF, splitting it into lines, identifying which lines contain transactions, and safely extracting the specific data points using regex groups.
* **Streamlit Session State:** Used in the manual tagging phase to preserve user inputs (tags) across reruns without losing data.

## ⚠️ Notes & Limitations

* **Regex Dependency:** The extraction accuracy relies on the specific formatting of the bank statement. If your bank uses a highly unconventional date format or doesn't use the "₹" symbol, the regex patterns in the code may need slight adjustments.
* **Local Processing:** All data processing happens locally on your machine. No financial data is sent to external servers.

*** App Link- https://newupcomingprjt-zkbebb7fsoaeg3buz8v6cl.streamlit.app/
