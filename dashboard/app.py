"""
TransactSafe — Fraud Analyst Dashboard
==========================================
A Streamlit dashboard querying the gold-layer tables (fct_flagged_transactions,
dim_account_risk_scores, mart_monthly_compliance_summary) to give a fraud
analyst a working view into pipeline output.

Run locally:
    streamlit run dashboard/app.py

Deploy: push to GitHub, then connect the repo at https://share.streamlit.io
"""

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="TransactSafe — Fraud Detection Dashboard",
    page_icon="🛡️",
    layout="wide",
)

DB_PATH = "../bronze/bronze.duckdb"


@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH, read_only=True)


@st.cache_data(ttl=300)
def load_data():
    con = get_connection()
    flagged = con.sql("SELECT * FROM fct_flagged_transactions").df()
    risk_scores = con.sql("SELECT * FROM dim_account_risk_scores").df()
    monthly = con.sql("SELECT * FROM mart_monthly_compliance_summary ORDER BY month").df()
    return flagged, risk_scores, monthly


def main():
    st.title("🛡️ TransactSafe — Fraud Detection Dashboard")
    st.caption(
        "A data pipeline project demonstrating bronze/silver/gold architecture, "
        "rule-based fraud detection, and account risk scoring. "
        "[View the full project on GitHub](https://github.com/Obaydawan/banking-lakehouse-pipeline)"
    )

    try:
        flagged_df, risk_df, monthly_df = load_data()
    except Exception as e:
        st.error(f"Could not load data: {e}")
        st.info("Make sure the pipeline has been run at least once (dbt run) before launching this dashboard.")
        return

    # --- Top-level metrics ---
    total_accounts = len(risk_df)
    flagged_accounts = len(risk_df[risk_df["risk_tier"] != "None"])
    high_risk_accounts = len(risk_df[risk_df["risk_tier"] == "High"])
    total_flagged_txns = len(flagged_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Accounts", f"{total_accounts:,}")
    col2.metric("Accounts with Any Flag", f"{flagged_accounts:,}")
    col3.metric("High Risk Accounts", f"{high_risk_accounts:,}")
    col4.metric("Flagged Transactions", f"{total_flagged_txns:,}")

    st.divider()

    # --- Risk tier distribution ---
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Risk Tier Distribution")
        tier_counts = risk_df["risk_tier"].value_counts().reset_index()
        tier_counts.columns = ["risk_tier", "count"]
        tier_order = ["None", "Low", "Medium", "High"]
        tier_counts["risk_tier"] = pd.Categorical(tier_counts["risk_tier"], categories=tier_order, ordered=True)
        tier_counts = tier_counts.sort_values("risk_tier")

        fig = px.bar(
            tier_counts,
            x="risk_tier",
            y="count",
            color="risk_tier",
            color_discrete_map={"None": "#2ecc71", "Low": "#f1c40f", "Medium": "#e67e22", "High": "#e74c3c"},
            labels={"risk_tier": "Risk Tier", "count": "Number of Accounts"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Flag Type Breakdown")
        flag_counts = pd.DataFrame({
            "Flag Type": ["Velocity Fraud", "Geographic Anomaly", "Amount Outlier"],
            "Count": [
                flagged_df["is_velocity_flag"].sum(),
                flagged_df["is_geo_flag"].sum(),
                flagged_df["is_outlier_flag"].sum(),
            ],
        })
        fig2 = px.pie(flag_counts, names="Flag Type", values="Count", hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # --- Monthly compliance trend ---
    st.subheader("Monthly Compliance Trend")
    if not monthly_df.empty:
        fig3 = px.line(
            monthly_df,
            x="month",
            y="flagged_rate_pct",
            markers=True,
            labels={"month": "Month", "flagged_rate_pct": "Flagged Rate (%)"},
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(monthly_df, use_container_width=True)
    else:
        st.info("No monthly data available yet.")

    st.divider()

    # --- High risk accounts table ---
    st.subheader("Highest Risk Accounts")
    high_risk_df = risk_df[risk_df["risk_tier"].isin(["High", "Medium"])].sort_values(
        "risk_score", ascending=False
    )
    st.dataframe(
        high_risk_df[
            ["account_id", "risk_score", "risk_tier", "velocity_flags", "geo_flags", "outlier_flags", "total_transactions"]
        ],
        use_container_width=True,
    )

    st.divider()

    # --- Flagged transactions explorer ---
    st.subheader("Flagged Transactions Explorer")

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        flag_filter = st.multiselect(
            "Filter by flag type",
            options=["Velocity", "Geographic", "Outlier"],
            default=[],
        )
    with filter_col2:
        min_amount = st.number_input("Minimum amount", min_value=0.0, value=0.0, step=100.0)

    filtered = flagged_df.copy()
    if "Velocity" in flag_filter:
        filtered = filtered[filtered["is_velocity_flag"]]
    if "Geographic" in flag_filter:
        filtered = filtered[filtered["is_geo_flag"]]
    if "Outlier" in flag_filter:
        filtered = filtered[filtered["is_outlier_flag"]]
    filtered = filtered[filtered["amount"] >= min_amount]

    st.dataframe(
        filtered[
            ["transaction_id", "account_id", "timestamp", "amount", "country",
             "merchant_category", "is_velocity_flag", "is_geo_flag", "is_outlier_flag"]
        ].sort_values("timestamp", ascending=False),
        use_container_width=True,
        height=400,
    )
    st.caption(f"Showing {len(filtered):,} of {len(flagged_df):,} flagged transactions")


if __name__ == "__main__":
    main()
