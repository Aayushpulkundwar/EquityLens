import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Helper to safely extract a numeric value from a dict or series
def _safe_get(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float, np.number)):
            return float(value)
        # If a pandas Series or DataFrame column, take the latest non‑null
        if isinstance(value, pd.Series):
            val = value.dropna().iloc[-1]
            return float(val)
        if isinstance(value, dict):
            # Expect a dict with a numeric entry
            for v in value.values():
                if isinstance(v, (int, float, np.number)):
                    return float(v)
        return None
    except Exception:
        return None

# -------------------------- Intrinsic Valuation --------------------------

def calculate_dcf(fcf: pd.Series, wacc: float = 0.10, terminal_growth: float = 0.02, years: int = 5) -> Optional[float]:
    """Discounted Cash Flow valuation.
    fcf – Series of free cash flow indexed by date (most recent last).
    Returns the present value of projected cash flows plus terminal value.
    Returns None if inputs are invalid.
    """
    if fcf is None or fcf.empty:
        logger.warning("DCF: Free cash flow series is empty.")
        return None
    if wacc <= 0:
        logger.warning("DCF: WACC must be positive.")
        return None
    # Use the most recent FCF as base and grow it at the average historical growth rate if possible
    recent_fcf = fcf.dropna().iloc[-1]
    # Historical growth rate (YoY) if we have at least two points
    if len(fcf.dropna()) >= 2:
        growth_rates = fcf.pct_change().dropna()
        avg_growth = growth_rates.mean()
        proj_growth = avg_growth if not np.isnan(avg_growth) else terminal_growth
    else:
        proj_growth = terminal_growth
    # Project cash flows
    cash_flows = []
    for i in range(1, years + 1):
        cash = recent_fcf * ((1 + proj_growth) ** i)
        cash_flows.append(cash / ((1 + wacc) ** i))
    # Terminal value using Gordon growth on last projected cash flow
    terminal_cash = recent_fcf * ((1 + proj_growth) ** (years + 1))
    terminal_value = terminal_cash / (wacc - terminal_growth)
    terminal_value_discounted = terminal_value / ((1 + wacc) ** (years + 1))
    dcf_value = sum(cash_flows) + terminal_value_discounted
    return float(dcf_value)


def calculate_gordon_growth(dividend: pd.Series, discount_rate: float = 0.10, growth_rate: float = 0.02) -> Optional[float]:
    """Gordon (Dividend Discount) Model.
    dividend – Series of dividend per share; uses the most recent value.
    Returns None if dividend data unavailable.
    """
    recent_div = _safe_get(dividend)
    if recent_div is None or recent_div <= 0:
        logger.warning("Gordon Growth: No valid dividend data.")
        return None
    if discount_rate <= growth_rate:
        logger.warning("Gordon Growth: discount_rate must be > growth_rate.")
        return None
    value = recent_div / (discount_rate - growth_rate)
    return float(value)


def calculate_benjamin_graham(earnings_growth_rate: Optional[float] = None, eps: Optional[float] = None, book_value: Optional[float] = None) -> Optional[float]:
    """Revised Benjamin Graham formula:
        V = EPS * (8.5 + 2 * g) * 4.4 / Y
    where g = expected growth rate in percent (e.g. 5.0 for 5%) and Y = AAA corporate bond yield in percent (e.g. 4.4).
    Returns None if required inputs are missing.
    """
    if eps is None:
        logger.warning("Benjamin Graham: EPS missing.")
        return None
    g = earnings_growth_rate if earnings_growth_rate is not None else 0.0
    Y = 4.4  # assumed AAA corporate bond yield (4.4%)
    V = eps * (8.5 + 2 * g) * 4.4 / Y
    return float(V)


def calculate_graham_number(eps: Optional[float] = None, book_value_per_share: Optional[float] = None) -> Optional[float]:
    """Graham Number = sqrt(22.5 * EPS * Book Value per Share).
    Returns None if inputs missing.
    """
    if eps is None or book_value_per_share is None:
        logger.warning("Graham Number: EPS or book value per share missing.")
        return None
    return float(np.sqrt(22.5 * eps * book_value_per_share))

# -------------------------- Relative Valuation --------------------------

def calculate_peg_ratio(pe_ratio: Optional[float] = None, earnings_growth_rate: Optional[float] = None) -> Optional[float]:
    """PEG = P/E divided by annual earnings growth rate (as a percentage).
    Returns None if inputs missing or growth_rate <= 0.
    """
    if pe_ratio is None or earnings_growth_rate is None or earnings_growth_rate <= 0:
        logger.warning("PEG: Missing or invalid inputs.")
        return None
    return float(pe_ratio / (earnings_growth_rate * 100))


def calculate_ev_ebitda(ev: Optional[float] = None, ebitda: Optional[float] = None) -> Optional[float]:
    if ev is None or ebitda is None or ebitda == 0:
        logger.warning("EV/EBITDA: Missing or zero EBITDA.")
        return None
    return float(ev / ebitda)


def calculate_price_to_fcf(market_cap: Optional[float] = None, fcf: Optional[float] = None) -> Optional[float]:
    if market_cap is None or fcf is None or fcf == 0:
        logger.warning("P/FCF: Missing or zero free cash flow.")
        return None
    return float(market_cap / fcf)

# --------------------------------------------------------------------

def prepare_valuation_inputs(metadata: Dict[str, Any], enriched_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Collect all values needed for valuation functions.
    Returns a dict with keys used by the functions above; missing values are set to None.
    """
    info = metadata.get("info", {}) if metadata else {}
    # Latest annual metrics (already numeric via metrics_engine)
    annual = enriched_metrics.get("annual", {}) if enriched_metrics else {}
    # Helper to get field from metrics dict safely
    def get_metric(key: str) -> Optional[float]:
        val = annual.get(key)
        return _safe_get(val)

    # Extract required numbers
    eps = info.get("trailingEps") or info.get("forwardEps")
    book_val = info.get("bookValue")
    market_cap = info.get("marketCap") or (info.get("currentPrice") * info.get("sharesOutstanding") if info.get("currentPrice") and info.get("sharesOutstanding") else None)
    ev = info.get("enterpriseValue")
    ebitda = info.get("ebitda")
    dividend = info.get("dividendRate") or info.get("dividendYield")
    pe_ratio = info.get("trailingPE")
    # Revenue growth rate (YoY) from metrics if available
    revenue_growth_yoy = get_metric("revenue_growth_yoy")
    # Convert to decimal for functions expecting decimal (e.g., PEG expects %)
    return {
        "eps": _safe_get(eps),
        "book_value": _safe_get(book_val),
        "market_cap": _safe_get(market_cap),
        "ev": _safe_get(ev),
        "ebitda": _safe_get(ebitda),
        "dividend": _safe_get(dividend),
        "pe_ratio": _safe_get(pe_ratio),
        "revenue_growth_yoy": revenue_growth_yoy,
        "fcf_series": enriched_metrics.get("annual", {}).get("free_cash_flow"),
    }
