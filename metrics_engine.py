import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """
    Safely divides two Pandas Series, returning NaN where denominator is zero or missing.
    """
    # Replace 0 with NaN in the denominator to avoid division by zero
    clean_denom = denominator.replace(0, np.nan)
    return numerator / clean_denom

def calculate_time_based_growth(df: pd.DataFrame, target_col: str, months_offset: int, max_days_diff: int) -> pd.Series:
    growth_series = pd.Series(index=df.index, dtype=float)
    if df.empty or target_col not in df.columns:
        return growth_series
        
    for date in df.index:
        # Calculate the historical date we want to compare against
        target_date = date - pd.DateOffset(months=months_offset)
        # Find the closest date index
        diffs = abs(df.index - target_date)
        if len(diffs) > 0:
            closest_idx = diffs.argmin()
            closest_date = df.index[closest_idx]
            
            # Ensure the closest date is within acceptable bounds
            if diffs[closest_idx] <= pd.Timedelta(days=max_days_diff):
                val_current = df.loc[date, target_col]
                val_prior = df.loc[closest_date, target_col]
                
                if pd.notna(val_current) and pd.notna(val_prior) and val_prior != 0:
                    growth_series.loc[date] = (val_current / val_prior) - 1.0
                    
    return growth_series

def compute_financial_metrics(processed_data: Dict[str, pd.DataFrame]) -> Optional[Dict[str, pd.DataFrame]]:
    if not processed_data:
        logger.error("No processed data provided to compute_financial_metrics.")
        return None
        
    enriched_data = {}
    
    for timeframe in ["annual", "quarterly"]:
        try:
            df = processed_data.get(timeframe)
            if df is None or df.empty:
                logger.warning(f"Empty DataFrame for timeframe: {timeframe}")
                continue
                
            # Create a copy to avoid SettingWithCopyWarning
            m_df = df.copy()
            
            # 1. Margins
            m_df["ebit_margin"] = safe_divide(m_df["ebit"], m_df["revenue"])
            m_df["net_profit_margin"] = safe_divide(m_df["net_income"], m_df["revenue"])
            m_df["fcf_margin"] = safe_divide(m_df["free_cash_flow"], m_df["revenue"])
            
            # 2. Return on Equity (ROE)
            m_df["roe"] = safe_divide(m_df["net_income"], m_df["equity"])
            
            # 3. Revenue Growth (QoQ, YoY)
            if timeframe == "annual":
                # For annual data, YoY is comparing to the row immediately prior (12 months ago)
                m_df["revenue_growth_yoy"] = calculate_time_based_growth(m_df, "revenue", months_offset=12, max_days_diff=30)
                m_df["revenue_growth_qoq"] = np.nan # Not applicable for annual
            else:
                # For quarterly data, QoQ is 3 months ago, YoY is 12 months ago
                m_df["revenue_growth_qoq"] = calculate_time_based_growth(m_df, "revenue", months_offset=3, max_days_diff=15)
                m_df["revenue_growth_yoy"] = calculate_time_based_growth(m_df, "revenue", months_offset=12, max_days_diff=30)
                
                # Annualize quarterly ROE to make it comparable to annual ROE
                m_df["roe_annualized"] = m_df["roe"] * 4
                
            enriched_data[timeframe] = m_df
            logger.info(f"Successfully computed metrics for {timeframe} data.")
            
        except Exception as e:
            logger.error(f"Error computing metrics for {timeframe} data: {e}", exc_info=True)
            return None
            
    return enriched_data

def format_latest_metrics_summary(enriched_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    summary = {"annual": {}, "quarterly": {}}
    
    for timeframe in ["annual", "quarterly"]:
        df = enriched_data.get(timeframe)
        if df is None or df.empty:
            continue
            
        # Get the latest row with non-null values
        latest_date = df.index[-1]
        row = df.loc[latest_date]
        
        # Convert date to string format
        date_str = latest_date.strftime("%Y-%m-%d")
        
        # Helper to convert numpy type to float/None for safety
        def clean_val(val):
            return float(val) if pd.notna(val) else None
            
        metrics = {
            "date": date_str,
            "revenue": clean_val(row.get("revenue")),
            "ebit": clean_val(row.get("ebit")),
            "ebit_margin": clean_val(row.get("ebit_margin")),
            "net_income": clean_val(row.get("net_income")),
            "net_profit_margin": clean_val(row.get("net_profit_margin")),
            "equity": clean_val(row.get("equity")),
            "roe": clean_val(row.get("roe")),
            "free_cash_flow": clean_val(row.get("free_cash_flow")),
            "fcf_margin": clean_val(row.get("fcf_margin")),
            "revenue_growth_yoy": clean_val(row.get("revenue_growth_yoy")),
            "revenue_growth_qoq": clean_val(row.get("revenue_growth_qoq"))
        }
        
        if timeframe == "quarterly" and "roe_annualized" in row:
            metrics["roe_annualized"] = clean_val(row.get("roe_annualized"))
            
        summary[timeframe] = metrics
        
    return summary

if __name__ == "__main__":
    # Test metrics engine using AAPL data
    import data_fetcher
    import data_processor
    import json
    
    print("Testing metrics engine with AAPL...")
    raw = data_fetcher.fetch_financial_data("AAPL")
    if raw:
        processed = data_processor.process_statement_data(raw)
        if processed:
            enriched = compute_financial_metrics(processed)
            if enriched:
                for tf, df in enriched.items():
                    print(f"\n--- Enriched {tf.upper()} DataFrame ---")
                    cols_to_print = ["revenue", "revenue_growth_yoy", "revenue_growth_qoq", "ebit_margin", "net_profit_margin", "roe", "free_cash_flow", "fcf_margin"]
                    # Filter existing columns
                    print(df[[c for c in cols_to_print if c in df.columns]])
                    
                summary = format_latest_metrics_summary(enriched)
                print("\n--- Latest Metrics Summary ---")
                print(json.dumps(summary, indent=2))
            else:
                print("Failed to compute metrics.")
        else:
            print("Failed to process data.")
    else:
        print("Failed to fetch raw data.")
