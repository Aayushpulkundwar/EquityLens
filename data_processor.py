import pandas as pd
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FIELD_MAPPINGS = {
    "revenue": ["Total Revenue", "Operating Revenue", "Revenue"],
    "ebit": ["EBIT", "Operating Income", "Operating Income Loss"],
    "net_income": [
        "Net Income",
        "Net Income Common Stockholders",
        "Net Income Continuous Operations",
        "Net Income From Continuing Operation Net Minority Interest"
    ],
    "equity": [
        "Stockholders Equity",
        "Common Stock Equity",
        "Total Equity Gross Minority Interest",
        "Total Stockholders Equity"
    ],
    "operating_cash_flow": [
        "Operating Cash Flow",
        "Cash Flow From Continuing Operating Activities",
        "Net Cash Provided By Operating Activities"
    ],
    "capex": [
        "Capital Expenditure",
        "Capital Expenditures",
        "Purchase Of PPE",
        "Net PPE Purchase And Sale"
    ],
    "free_cash_flow": ["Free Cash Flow", "Free Cash Flow Fcf"]
}

def safe_extract(df_t: pd.DataFrame, keys: list, field_name: str) -> pd.Series:
    if df_t is None or df_t.empty:
        return pd.Series(dtype=float)
        
    for key in keys:
        if key in df_t.columns:
            logger.debug(f"Extracted {field_name} using key: '{key}'")
            return df_t[key]
            
    logger.debug(f"Could not find any matching keys for {field_name} in columns: {list(df_t.columns)}")
    return pd.Series(index=df_t.index, dtype=float)

def process_statement_data(raw_data: Dict[str, pd.DataFrame]) -> Optional[Dict[str, pd.DataFrame]]:
    if not raw_data:
        logger.error("No raw data provided to process_statement_data.")
        return None
        
    processed = {}
    
    # Normalize annual and quarterly statement indices and clean them
    for timeframe in ["annual", "quarterly"]:
        try:
            if timeframe == "annual":
                fin = raw_data.get("financials")
                bs = raw_data.get("balance_sheet")
                cf = raw_data.get("cashflow")
            else:
                fin = raw_data.get("quarterly_financials")
                bs = raw_data.get("quarterly_balance_sheet")
                cf = raw_data.get("quarterly_cashflow")
                
            # Transpose so dates are rows and statements are columns
            fin_t = fin.T if (fin is not None and not fin.empty) else pd.DataFrame()
            bs_t = bs.T if (bs is not None and not bs.empty) else pd.DataFrame()
            cf_t = cf.T if (cf is not None and not cf.empty) else pd.DataFrame()
            
            # Normalize date indices to timezone-naive datetime objects for alignment
            for df_t in [fin_t, bs_t, cf_t]:
                if not df_t.empty:
                    df_t.index = pd.to_datetime(df_t.index).normalize()
                    
            # Safe extraction of individual series
            revenue = safe_extract(fin_t, FIELD_MAPPINGS["revenue"], "revenue")
            ebit = safe_extract(fin_t, FIELD_MAPPINGS["ebit"], "ebit")
            net_income = safe_extract(fin_t, FIELD_MAPPINGS["net_income"], "net_income")
            
            equity = safe_extract(bs_t, FIELD_MAPPINGS["equity"], "equity")
            
            ocf = safe_extract(cf_t, FIELD_MAPPINGS["operating_cash_flow"], "operating_cash_flow")
            capex = safe_extract(cf_t, FIELD_MAPPINGS["capex"], "capex")
            fcf = safe_extract(cf_t, FIELD_MAPPINGS["free_cash_flow"], "free_cash_flow")
            
            # Outer join concatenation along columns axis
            combined_df = pd.concat({
                "revenue": revenue,
                "ebit": ebit,
                "net_income": net_income,
                "equity": equity,
                "operating_cash_flow": ocf,
                "capex": capex,
                "free_cash_flow": fcf
            }, axis=1, sort=False)
            
            # Sort oldest to newest
            combined_df = combined_df.sort_index(ascending=True)
            
            # Ensure elements are numeric
            for col in combined_df.columns:
                combined_df[col] = pd.to_numeric(combined_df[col], errors="coerce")
                
            # Fallback for Free Cash Flow calculation
            computed_fcf = combined_df["operating_cash_flow"] - combined_df["capex"].abs()
            combined_df["free_cash_flow"] = combined_df["free_cash_flow"].fillna(computed_fcf)
            
            processed[timeframe] = combined_df
            logger.info(f"Successfully cleaned and normalized {timeframe} data. Shape: {combined_df.shape}")
            
        except Exception as e:
            logger.error(f"Error processing {timeframe} data: {e}", exc_info=True)
            return None
            
    return processed

if __name__ == "__main__":
    # Test data processing using AAPL
    import data_fetcher
    print("Fetching and processing data for test ticker: AAPL")
    raw = data_fetcher.fetch_financial_data("AAPL")
    if raw:
        processed = process_statement_data(raw)
        if processed:
            for tf, df in processed.items():
                print(f"\n--- Standardized {tf.upper()} DataFrame (oldest to newest) ---")
                print(df)
        else:
            print("Failed standardizing data.")
    else:
        print("Failed fetching raw data.")
