import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Helper to safely extract a numeric value from a dict or pandas series
def _safe_get(value: Any) -> Optional[float]:
    """Extract a float from various possible containers, returning None on failure."""
    try:
        if value is None:
            return None
        if isinstance(value, (int, float, np.number)):
            return float(value)
        if isinstance(value, pd.Series):
            # Take the most recent non‑null entry
            val = value.dropna().iloc[-1]
            return float(val)
        if isinstance(value, dict):
            # Look for first numeric entry
            for v in value.values():
                if isinstance(v, (int, float, np.number)):
                    return float(v)
        return None
    except Exception:
        return None

# -------------------------- Intrinsic Valuation --------------------------

def dcf_valuation(
    fcf: pd.Series,
    shares_outstanding: Optional[int] = None,
    growth_rate: Optional[float] = None,
    discount_rate: float = 0.09,
    terminal_growth: float = 0.03,
    years: int = 5,
    growth_adj: float = 0.0,
    compute_sensitivity: bool = True,
) -> Dict[str, Any]:
    """Discounted Cash Flow (DCF) valuation.

    2️⃣ Discount each projected FCF to present value.
    3️⃣ Compute a terminal value using a modest terminal growth rate.
    4️⃣ Discount the terminal value.
    5️⃣ Sum to obtain *total enterprise value*.
    6️⃣ If ``shares_outstanding`` is provided, derive an *intrinsic per‑share value*.
    7️⃣ Perform sanity checks and optionally return a sensitivity range.

    Parameters
    ----------
    fcf: pd.Series
        Historical free cash flow series (most recent last).
    shares_outstanding: int, optional
        Number of shares to convert total value to per‑share.
    growth_rate: float, optional
        Base annual growth rate. If omitted, the function derives an average historic rate and caps it at 15%.
    discount_rate: float, default 0.09
        Discount rate (WACC). Must be greater than growth_rate.
    terminal_growth: float, default 0.03
        Long‑term growth used for terminal value (2‑4% typical).
    years: int, default 5
        Projection horizon.
    growth_adj: float, default 0.0
        Adjustment applied to the base growth rate for sensitivity analysis.
        Use +0.02 for bullish case, -0.02 for bearish case.

    Returns
    -------
    dict
        ``{"intrinsic_per_share": float | None,
          "total_value": float | None,
          "sanity_flag": str | None,
          "low_per_share": float | None,
          "high_per_share": float | None}``
    """
    # Validate inputs
    if fcf is None or fcf.empty:
        logger.warning("DCF: Free cash flow series is empty.")
        return {"intrinsic_per_share": None, "total_value": None, "sanity_flag": None, "low_per_share": None, "high_per_share": None}

    if discount_rate <= 0:
        logger.warning("DCF: discount_rate must be positive.")
        return {"intrinsic_per_share": None, "total_value": None, "sanity_flag": None, "low_per_share": None, "high_per_share": None}

    # Determine base growth rate (historical average) if not supplied
    recent_fcf = fcf.dropna().iloc[-1]
    if growth_rate is None:
        if len(fcf.dropna()) >= 2:
            hist_growth = fcf.pct_change().dropna().mean()
            base_growth = hist_growth if not np.isnan(hist_growth) else 0.0
        else:
            base_growth = 0.0
        # Cap at 15% and ensure non‑negative
        growth_rate = min(max(base_growth, 0.0), 0.15)
    else:
        # Enforce cap regardless of user input
        growth_rate = min(max(growth_rate, 0.0), 0.15)

    # Apply optional sensitivity adjustment
    adj_growth = min(max(growth_rate + growth_adj, 0.0), 0.15)

    # Projection loop
    cash_flows = []
    projected_fcf = recent_fcf
    for i in range(1, years + 1):
        projected_fcf *= (1 + adj_growth)
        pv = projected_fcf / ((1 + discount_rate) ** i)
        cash_flows.append(pv)

    # Terminal value based on the *adjusted* growth rate for consistency
    terminal_fcf = projected_fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** years)

    total_value = sum(cash_flows) + pv_terminal

    # Derive per‑share if shares outstanding are known
    intrinsic_per_share = None
    if shares_outstanding and shares_outstanding > 0:
        intrinsic_per_share = total_value / shares_outstanding

    # Sanity checks (these are lightweight, final decision made elsewhere)
    sanity_flag = None
    # The calling code will supply market_price for comparison; we only flag obvious issues here
    if intrinsic_per_share is not None and intrinsic_per_share < 0:
        sanity_flag = "Invalid DCF output"

    # Sensitivity extremes (bull/bear) – only if shares are known
    low_per_share = high_per_share = None
    if shares_outstanding and shares_outstanding > 0:
        def _compute_per_share(adj: float) -> Optional[float]:
            adj_growth = min(max(growth_rate + adj, 0.0), 0.15)
            # projection
            cash_flows_adj = []
            proj_fcf = recent_fcf
            for i in range(1, years + 1):
                proj_fcf *= (1 + adj_growth)
                pv = proj_fcf / ((1 + discount_rate) ** i)
                cash_flows_adj.append(pv)
            terminal_fcf_adj = proj_fcf * (1 + terminal_growth)
            terminal_value_adj = terminal_fcf_adj / (discount_rate - terminal_growth)
            pv_terminal_adj = terminal_value_adj / ((1 + discount_rate) ** years)
            total_adj = sum(cash_flows_adj) + pv_terminal_adj
            return total_adj / shares_outstanding if shares_outstanding else None
        high_per_share = _compute_per_share(0.02)  # bull
        low_per_share = _compute_per_share(-0.02)  # bear

    return {
        "intrinsic_per_share": intrinsic_per_share,
        "total_value": total_value,
        "sanity_flag": sanity_flag,
        "low_per_share": low_per_share,
        "high_per_share": high_per_share,
    }

def prepare_valuation_inputs(metadata: Dict[str, Any], enriched_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Collect valuation inputs.

    Returns a dictionary with keys used by ``dcf_valuation``. Missing values are set to ``None``.
    """
    info = metadata.get("info", {}) if metadata else {}
    shares = info.get("sharesOutstanding")
    return {
        "fcf_series": enriched_metrics.get("annual", {}).get("free_cash_flow"),
        "shares_outstanding": shares,
    }
