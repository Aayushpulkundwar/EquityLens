import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def _safe_get(metric_dict: Dict[str, Any], key: str) -> Any:
    """Helper to safely retrieve a metric value, returning None if missing or NaN."""
    val = metric_dict.get(key)
    if val is None:
        return None
    try:
        # Pandas may return numpy nan; treat as None
        if isinstance(val, float) and (val != val):  # NaN check
            return None
        return val
    except Exception:
        return None


def generate_stock_overview(company_metrics: Dict[str, Any], peer_metrics: List[Dict[str, Any]]) -> Dict[str, str]:
    """Compute a high‑level stock overview for a company.

    Parameters
    ----------
    company_metrics: dict
        Metrics for the target company. Expected keys include:
        ``revenue_growth_yoy``, ``net_profit_margin``, ``roe``, ``free_cash_flow`` and ``fcf_margin``.
    peer_metrics: list of dict
        List of metric dictionaries for peer companies (same keys as ``company_metrics``).

    Returns
    -------
    dict
        ``{"market_position": str, "growth_standing": str, "profitability_standing": str,
        "efficiency_standing": str, "cashflow_strength": str}``
        Missing or unparsable data yields the string ``"Data not available"`` for that field.
    """
    # Initialise result with defaults
    result = {
        "market_position": "Data not available",
        "growth_standing": "Data not available",
        "profitability_standing": "Data not available",
        "efficiency_standing": "Data not available",
        "cashflow_strength": "Data not available",
    }

    # ---------------------------------------------------------------------
    # 1. MARKET POSITION (compare revenue growth, EBIT margin, ROE)
    # ---------------------------------------------------------------------
    try:
        # Gather company values
        comp_rev_growth = _safe_get(company_metrics, "revenue_growth_yoy")
        comp_ebit_margin = _safe_get(company_metrics, "ebit_margin")
        comp_roe = _safe_get(company_metrics, "roe")

        # If any of the three core metrics are missing we cannot compute market position
        if any(v is None for v in (comp_rev_growth, comp_ebit_margin, comp_roe)):
            raise ValueError("Missing core metrics for market position")

        # Build peer value lists, ignoring missing entries
        peer_rev_growth = [_safe_get(p, "revenue_growth_yoy") for p in peer_metrics]
        peer_ebit_margin = [_safe_get(p, "ebit_margin") for p in peer_metrics]
        peer_roe = [_safe_get(p, "roe") for p in peer_metrics]

        # Helper to compute whether company outperforms the median of peers for a metric
        def outperforms(company_val, peer_vals):
            filtered = [v for v in peer_vals if v is not None]
            if not filtered:
                return None
            median = sorted(filtered)[len(filtered) // 2]
            return company_val > median

        outs = []
        for comp_val, peers in (
            (comp_rev_growth, peer_rev_growth),
            (comp_ebit_margin, peer_ebit_margin),
            (comp_roe, peer_roe),
        ):
            res = outperforms(comp_val, peers)
            if res is None:
                continue
            outs.append(res)

        # Determine position based on how many metrics the company outperforms
        if len(outs) == 3:
            if all(outs):
                result["market_position"] = "Leader"
            elif not any(outs):
                result["market_position"] = "Lagging"
            else:
                result["market_position"] = "Competitive"
        elif outs:
            if all(outs):
                result["market_position"] = "Leader"
            elif not any(outs):
                result["market_position"] = "Lagging"
            else:
                result["market_position"] = "Competitive"
        else:
            result["market_position"] = "Data not available"
    except Exception as e:
        logger.debug(f"Market position calculation failed: {e}")
        result["market_position"] = "Data not available"

    # ---------------------------------------------------------------------
    # 2. GROWTH STANDING (YoY revenue growth)
    # ---------------------------------------------------------------------
    try:
        yoy = _safe_get(company_metrics, "revenue_growth_yoy")
        if yoy is None:
            raise ValueError("Missing YoY growth")
        # Convert to percent for thresholds (input may be decimal like 0.0643)
        percent = yoy * 100 if yoy < 10 else yoy
        if percent > 20:
            result["growth_standing"] = "High"
        elif 10 <= percent <= 20:
            result["growth_standing"] = "Moderate"
        elif 0 <= percent < 10:
            result["growth_standing"] = "Low"
        else:
            result["growth_standing"] = "Negative"
    except Exception as e:
        logger.debug(f"Growth standing calculation failed: {e}")
        result["growth_standing"] = "Data not available"

    # ---------------------------------------------------------------------
    # 3. PROFITABILITY STANDING (net profit margin)
    # ---------------------------------------------------------------------
    try:
        margin = _safe_get(company_metrics, "net_profit_margin")
        if margin is None:
            raise ValueError("Missing net profit margin")
        percent = margin * 100 if margin < 10 else margin
        if percent > 30:
            result["profitability_standing"] = "High"
        elif 20 <= percent <= 30:
            result["profitability_standing"] = "Strong"
        elif 10 <= percent < 20:
            result["profitability_standing"] = "Moderate"
        else:
            result["profitability_standing"] = "Weak"
    except Exception as e:
        logger.debug(f"Profitability standing calculation failed: {e}")
        result["profitability_standing"] = "Data not available"

    # ---------------------------------------------------------------------
    # 4. EFFICIENCY STANDING (ROE)
    # ---------------------------------------------------------------------
    try:
        roe_val = _safe_get(company_metrics, "roe")
        if roe_val is None:
            raise ValueError("Missing ROE")
        percent = roe_val * 100 if roe_val < 10 else roe_val
        if percent > 25:
            result["efficiency_standing"] = "Excellent"
        elif 15 <= percent <= 25:
            result["efficiency_standing"] = "Strong"
        elif 10 <= percent < 15:
            result["efficiency_standing"] = "Average"
        else:
            result["efficiency_standing"] = "Weak"
    except Exception as e:
        logger.debug(f"Efficiency standing calculation failed: {e}")
        result["efficiency_standing"] = "Data not available"

    # ---------------------------------------------------------------------
    # 5. CASH FLOW STRENGTH (FCF and margin)
    # ---------------------------------------------------------------------
    try:
        fcf = _safe_get(company_metrics, "free_cash_flow")
        fcf_margin = _safe_get(company_metrics, "fcf_margin")
        if fcf is None or fcf_margin is None:
            raise ValueError("Missing cash flow data")
        margin_percent = fcf_margin * 100 if fcf_margin < 10 else fcf_margin
        if fcf > 0 and margin_percent > 20:
            result["cashflow_strength"] = "Strong"
        elif fcf > 0:
            result["cashflow_strength"] = "Stable"
        else:
            result["cashflow_strength"] = "Weak"
    except Exception as e:
        logger.debug(f"Cash flow strength calculation failed: {e}")
        result["cashflow_strength"] = "Data not available"

    return result
