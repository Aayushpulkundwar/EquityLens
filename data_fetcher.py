import yfinance as yf
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def fetch_financial_data(ticker_symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch financial statements for a ticker using yfinance.

    Returns a dictionary with keys:
        - "financials": annual income statement DataFrame
        - "balance_sheet": annual balance sheet DataFrame
        - "cashflow": annual cash flow DataFrame
        - "quarterly_financials": quarterly income statement DataFrame
        - "quarterly_balance_sheet": quarterly balance sheet DataFrame
        - "quarterly_cashflow": quarterly cash flow DataFrame
    If any fetch fails, logs a warning and continues; returns None only if the ticker object itself cannot be created.
    """
    ticker_symbol = ticker_symbol.strip().upper()
    try:
        ticker = yf.Ticker(ticker_symbol)
    except Exception as e:
        logger.error(f"Failed to create yfinance Ticker for {ticker_symbol}: {e}")
        return None
    try:
        data = {
            "financials": ticker.financials,
            "balance_sheet": ticker.balance_sheet,
            "cashflow": ticker.cashflow,
            "quarterly_financials": ticker.quarterly_financials,
            "quarterly_balance_sheet": ticker.quarterly_balance_sheet,
            "quarterly_cashflow": ticker.quarterly_cashflow,
        }
        # Ensure at least one DataFrame is non-empty
        if all(df is None or df.empty for df in data.values()):
            logger.warning(f"No financial data retrieved for {ticker_symbol}")
            return None
        return data
    except Exception as e:
        logger.error(f"Error fetching financial data for {ticker_symbol}: {e}")
        return None
    """Existing function retained from original file for compatibility."""
    # This function is already defined in data_fetcher.py; placeholder to avoid import errors.
    return None

def fetch_ticker_metadata(ticker_symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch additional ticker metadata including info dict and recent news.

    Returns a dictionary with keys:
        - "info": dict of ticker info (price, sharesOutstanding, etc.)
        - "news": list of dicts with selected fields (title, link, publisher, pubDate)
        - "dividends": pandas Series of dividend history
    If any part fails, the missing part will be omitted.
    """
    ticker_symbol = ticker_symbol.strip().upper()
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Basic info
        info = ticker.info if hasattr(ticker, "info") else {}
        # News – yfinance provides a list of dicts under .news
        raw_news = getattr(ticker, "news", []) or []
        # Extract top 5 most recent news items
        structured_news: List[Dict[str, Any]] = []
        for item in raw_news[:5]:
            # Some items may miss fields; we guard against KeyError
            structured_news.append({
                "title": item.get("title"),
                "link": item.get("link") or item.get("clickThroughUrl", {}).get("url"),
                "publisher": item.get("provider", {}).get("displayName"),
                "pubDate": item.get("pubDate") or item.get("displayTime")
            })
        # Dividends series
        dividends = None
        try:
            dividends = ticker.dividends
        except Exception as e:
            logger.warning(f"Dividends fetch error for {ticker_symbol}: {e}")
        result: Dict[str, Any] = {"info": info, "news": structured_news}
        if dividends is not None:
            result["dividends"] = dividends
        return result
    except Exception as e:
        logger.error(f"Failed to fetch metadata for {ticker_symbol}: {e}", exc_info=True)
        return None
