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

def dcf_valuation(fcf: pd.Series, growth_rate: float = 0.02, discount_rate: float = 0.10, years: int = 5) -> Optional[float]:
    """Discounted Cash Flow valuation using a 5‑year projection.
    Parameters
    ----------
    fcf: pd.Series
        Free cash flow series (most recent last).
    growth_rate: float, default 0.02
        Annual growth rate for projection.
    discount_rate: float, default 0.10
        Discount rate (WACC).
    years: int, default 5
        Number of years to project.
    Returns
    -------
    float or None
        Present value of projected cash flows plus terminal value, or None on invalid input.
    """
    if fcf is None or fcf.empty:
        logger.warning("DCF: Free cash flow series is empty.")
        return None
    if discount_rate <= growth_rate:
        logger.warning("DCF: discount_rate must be greater than growth_rate.")
        return None
    
    recent_fcf = fcf.dropna().iloc[-1]
    
    # Historical growth rate if available
    if len(fcf.dropna()) >= 2:
        growth_rates = fcf.pct_change().dropna()
        avg_growth = growth_rates.mean()
        proj_growth = avg_growth if not np.isnan(avg_growth) else growth_rate
    else:
        proj_growth = growth_rate
        
    cash_flows = []
    current_fcf = recent_fcf
    for i in range(1, years + 1):
        current_fcf *= (1 + proj_growth)
        cash_flows.append(current_fcf / ((1 + discount_rate) ** i))
        
    terminal_cash = current_fcf * (1 + growth_rate)
    terminal_value = terminal_cash / (discount_rate - growth_rate)
    terminal_value_discounted = terminal_value / ((1 + discount_rate) ** years)
    
    dcf_value = sum(cash_flows) + terminal_value_discounted
    return float(dcf_value)

# --------------------------------------------------------------------

def prepare_valuation_inputs(metadata: Dict[str, Any], enriched_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Collect all values needed for valuation functions.
    Returns a dict with keys used by the functions above; missing values are set to None.
    """
    return {
        "fcf_series": enriched_metrics.get("annual", {}).get("free_cash_flow"),
    }
