import streamlit as st
        debit_df = df[
            df["type"] == "DEBIT"
        ]

        credit_df = df[
            df["type"] == "CREDIT"
        ]

        total_debit = (
            debit_df["amount"].sum()
        )

        total_credit = (
            credit_df["amount"].sum()
        )

        total_transactions = len(df)

        unique_receivers = (
            df["receiver_name"]
            .dropna()
            .nunique()
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total Transactions",
            total_transactions
        )

        col2.metric(
            "Total Debit",
            f"₹{total_debit:,.2f}"
        )

        col3.metric(
            "Total Credit",
            f"₹{total_credit:,.2f}"
        )

        col4.metric(
            "Unique Receivers",
            unique_receivers
        )

        # =================================================
        # STAGE 3
        # =================================================

        st.header(
            "👤 Stage 3: Last Unique Receiver Transactions"
        )

        unique_df = (

            df[
                [
                    "date",
                    "time",
                    "receiver_name",
                    "amount"
                ]
            ]

            .dropna(
                subset=["receiver_name"]
            )

            .drop_duplicates(
                subset=["receiver_name"],
                keep="last"
            )

            .reset_index(drop=True)
        )

        unique_df = unique_df.rename(
            columns={
                "date": "Last Transaction Date",
                "time": "Last Transaction Time",
                "receiver_name": "Receiver Name",
                "amount": "Amount"
            }
        )

        st.dataframe(
            unique_df,
            use_container_width=True,
            height=500
        )
        )
