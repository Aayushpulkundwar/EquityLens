import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import data_fetcher
import data_processor
import metrics_engine

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Predefined peer lists for standard tickers
PEER_MAPPING = {
    "AAPL": ["MSFT", "GOOGL", "META"],
    "MSFT": ["AAPL", "GOOGL", "ORCL"],
    "GOOGL": ["MSFT", "AAPL", "META"],
    "GOOG": ["MSFT", "AAPL", "META"],
    "META": ["GOOGL", "AAPL", "NFLX"],
    "TSLA": ["F", "GM", "TM"],
    "NVDA": ["AMD", "INTC", "QCOM"],
    "AMD": ["NVDA", "INTC", "QCOM"],
    "RELIANCE.NS": ["IOC.NS", "BPCL.NS", "HINDPETRO.NS"],
    "TCS.NS": ["INFY.NS", "WIPRO.NS", "HCLTECH.NS"],
    "INFY.NS": ["TCS.NS", "WIPRO.NS", "HCLTECH.NS"]
}

def get_peers_for_ticker(ticker: str) -> List[str]:
    """
    Returns a list of hardcoded peer tickers for a given target ticker.
    Falls back to a default list of tech giants if the ticker is unknown.
    """
    ticker_upper = ticker.strip().upper()
    # Provide a reasonable tech-giant default if ticker isn't mapped
    return PEER_MAPPING.get(ticker_upper, ["AAPL", "MSFT", "GOOGL"])

def fetch_and_compute_company_metrics(ticker_symbol: str) -> Optional[Dict[str, Any]]:
    """
    Runs the pipeline for a single ticker to obtain the latest processed metrics.
    
    Args:
        ticker_symbol (str): Stock ticker to run.
        
    Returns:
        Optional[Dict[str, Any]]: Latest annual and quarterly metrics summary.
    """
    try:
        raw_data = data_fetcher.fetch_financial_data(ticker_symbol)
        if not raw_data:
            return None
            
        processed_data = data_processor.process_statement_data(raw_data)
        if not processed_data:
            return None
            
        enriched_data = metrics_engine.compute_financial_metrics(processed_data)
        if not enriched_data:
            return None
            
        summary = metrics_engine.format_latest_metrics_summary(enriched_data)
        return summary
    except Exception as e:
        logger.error(f"Error getting metrics for {ticker_symbol} during peer comparison: {e}")
        return None

def generate_peer_comparison(target_ticker: str, peer_tickers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Compares the target ticker's latest financial metrics side-by-side with its peers.
    
    Args:
        target_ticker (str): The primary ticker to analyze.
        peer_tickers (List[str], optional): Explicit list of peer tickers. If None, uses default mappings.
        
    Returns:
        Dict[str, Any]: Contains comparison DataFrames for annual and quarterly metrics.
    """
    target_ticker = target_ticker.strip().upper()
    if peer_tickers is None:
        peer_tickers = get_peers_for_ticker(target_ticker)
        # Ensure target is not in peers list
        peer_tickers = [p for p in peer_tickers if p != target_ticker]
        
    logger.info(f"Generating peer comparison for target {target_ticker} against peers: {peer_tickers}")
    
    # Get target metrics
    target_metrics = fetch_and_compute_company_metrics(target_ticker)
    if not target_metrics:
        logger.error(f"Failed to fetch metrics for target ticker {target_ticker}")
        return {}
        
    # Get peer metrics (skip any peers that fail)
    peer_metrics_map = {}
    for peer in peer_tickers:
        peer = peer.strip().upper()
        metrics = fetch_and_compute_company_metrics(peer)
        if metrics:
            peer_metrics_map[peer] = metrics
        else:
            logger.warning(f"Could not retrieve peer metrics for {peer}. Skipping.")
            
    # Compile comparison
    comparison = {
        "target": target_ticker,
        "peers_attempted": peer_tickers,
        "peers_successful": list(peer_metrics_map.keys()),
        "annual": {},
        "quarterly": {}
    }
    
    for timeframe in ["annual", "quarterly"]:
        timeframe_comp = {}
        
        # Add target
        target_tf = target_metrics.get(timeframe, {})
        if target_tf:
            timeframe_comp[target_ticker] = target_tf
            
        # Add successful peers
        for peer, metrics in peer_metrics_map.items():
            peer_tf = metrics.get(timeframe, {})
            if peer_tf:
                timeframe_comp[peer] = peer_tf
                
        # Convert side-by-side dict into DataFrame
        if timeframe_comp:
            df_comp = pd.DataFrame(timeframe_comp)
            comparison[timeframe] = df_comp
        else:
            comparison[timeframe] = pd.DataFrame()
            
    return comparison

if __name__ == "__main__":
    # Test peer comparison
    target = "AAPL"
    print(f"Generating peer comparison for {target}...")
    comp = generate_peer_comparison(target)
    
    for timeframe in ["annual", "quarterly"]:
        df = comp.get(timeframe)
        print(f"\n--- Side-by-Side {timeframe.upper()} Comparison DataFrame ---")
        if df is not None and not df.empty:
            print(df)
        else:
            print("No data available.")
