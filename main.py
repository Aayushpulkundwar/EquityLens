import argparse
import sys
import logging
from typing import Optional, List
import pandas as pd
import peer_comparison
import llm_engine

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def format_df_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Formats raw numeric metrics in the comparison DataFrame into human-readable 
    strings (e.g. percentages or currency formats).
    """
    if df is None or df.empty:
        return df
        
    display_df = df.copy()
    for col in display_df.columns:
        if col == "date":
            continue
            
        for idx in display_df.index:
            val = display_df.loc[idx, col]
            if pd.isna(val):
                display_df.loc[idx, col] = "N/A"
            elif "margin" in str(idx) or "growth" in str(idx) or "roe" in str(idx):
                display_df.loc[idx, col] = f"{val*100:.2f}%"
            elif idx in ["revenue", "ebit", "net_income", "equity", "free_cash_flow"]:
                display_df.loc[idx, col] = f"${val:,.0f}"
                
    return display_df

def run_pipeline(ticker: str, peers: Optional[List[str]] = None, include_peers: bool = True) -> int:
   
    ticker = ticker.strip().upper()
    
    print("\n" + "=" * 65)
    print(f"FINANCIAL ANALYSIS AGENT SUMMARY FOR: {ticker}")
    print("=" * 65)
    
    # 1. Fetch and process metrics (including peers if requested)
    if include_peers:
        print("Gathering financial metrics and peer comparisons...")
        comparison = peer_comparison.generate_peer_comparison(ticker, peers)
    else:
        print("Gathering financial metrics for target ticker...")
        comparison = peer_comparison.generate_peer_comparison(ticker, peer_tickers=[])
        
    if not comparison or not comparison.get("target"):
        print(f"\nError: Could not retrieve or compute metrics for {ticker}.")
        return 1
        
    # 2. Print comparative metrics tables
    print("\n" + "-" * 30 + " FINANCIAL STATS COMPARISON " + "-" * 30)
    for timeframe in ["annual", "quarterly"]:
        df = comparison.get(timeframe)
        if df is not None and not df.empty:
            print(f"\n[{timeframe.upper()} PERFORMANCE COMPARISON]")
            # Apply neat formatting
            display_df = format_df_for_display(df)
            
            # Print with aligned columns
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            print(display_df)
        else:
            print(f"\nNo {timeframe} metrics available.")
            
    # 3. Generate and display LLM report
    print("\nGenerating Financial Report Summary...")
    report = llm_engine.generate_financial_report(ticker, comparison)
    
    print("\n" + "=" * 65)
    print("FINANCIAL REPORT & INSIGHTS")
    print("=" * 65 + "\n")
    print(report)
    print("\n" + "=" * 65)
    
    return 0

def main():
    parser = argparse.ArgumentParser(
        description="Financial Analysis Agent: Evaluates financial metrics and compiles report summaries."
    )
    parser.add_argument("ticker", type=str, help="Target stock ticker (e.g. AAPL, MSFT, TSLA).")
    parser.add_argument(
        "--peers", "-p", 
        type=str, 
        help="Optional comma-separated list of peer tickers (e.g. 'AMD,INTC,QCOM')."
    )
    parser.add_argument(
        "--no-peers", 
        action="store_true", 
        help="Skip peer group retrieval and only evaluate target stock metrics."
    )
    
    args = parser.parse_args()
    
    peers_list = None
    if args.peers:
        peers_list = [p.strip() for p in args.peers.split(",") if p.strip()]
        
    sys.exit(run_pipeline(args.ticker, peers=peers_list, include_peers=not args.no_peers))

if __name__ == "__main__":
    main()
