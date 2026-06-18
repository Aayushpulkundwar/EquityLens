import os
import pandas as pd
from pdf_report import generate_pdf_report

# Sample data for comparison
annual_data = {
    "revenue": [50000000, 45000000, 47000000],
    "net_income": [8000000, 6000000, 7000000],
    "roe": [0.12, 0.10, 0.11],
}
quarterly_data = {
    "revenue": [12000000, 13000000, 12500000],
    "net_income": [2000000, 2100000, 1900000],
    "roe": [0.11, 0.115, 0.108],
}
annual_df = pd.DataFrame(annual_data, index=["Target", "PeerA", "PeerB"])
quarterly_df = pd.DataFrame(quarterly_data, index=["Target", "PeerA", "PeerB"])

comparison = {"annual": annual_df, "quarterly": quarterly_df}

valuations = {
    "dcf": 120.0,
    "graham": 95.0,
    "graham_number": 100.0,
    "market_price": 110.0,
    "valuation_status": "BUY",
    "peg": 1.2,
    "ev_ebitda": 12.5,
    "p_fcf": 18.0,
    "relative_interpretation": "fair"
}

risks = ["High debt levels", "Market volatility"]
recommendation = "BUY"
justification = "Strong cash flow and reasonable valuation multiples."
news = []  # empty list for simplicity

if __name__ == "__main__":
    output_path = os.path.join("reports", "sample_report.pdf")
    generate_pdf_report(
        ticker="TEST",
        comparison=comparison,
        valuations=valuations,
        risks=risks,
        recommendation=recommendation,
        justification=justification,
        news=news,
        output_path=output_path,
    )
    print(f"Report generated at {output_path}")
