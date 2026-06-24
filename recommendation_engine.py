import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def get_fundamental_strength(
    growth_vs_peers: str,
    profitability_vs_peers: str,
    fcf_positive: bool,
) -> str:
    """Compute fundamental strength classification.

    Args:
        growth_vs_peers: "outperforming" or "underperforming"
        profitability_vs_peers: "outperforming" or "underperforming"
        fcf_positive: Boolean indicating positive free cash flow.

    Returns:
        One of "strong", "moderate", "weak".
    """
    score = 0
    if growth_vs_peers == "outperforming":
        score += 1
    if profitability_vs_peers == "outperforming":
        score += 1
    if fcf_positive:
        score += 1

    if score >= 2:
        return "strong"
    elif score == 1:
        return "moderate"
    else:
        return "weak"


def get_risk_level(risk_count: int) -> str:
    """Classify risk level based on the number of risk flags.

    Args:
        risk_count: Integer count of identified risks (0+).

    Returns:
        One of "low", "moderate", "high".
    """
    if risk_count >= 4:
        return "high"
    if 2 <= risk_count <= 3:
        return "moderate"
    return "low"


def get_recommendation(
    valuation_status: str,
    risk_count: int,
    growth_vs_peers: str,
    profitability_vs_peers: str,
    fcf_positive: bool,
) -> Dict[str, Any]:
    """Strict recommendation engine following the prescribed decision matrix.

    Args:
        valuation_status: "Undervalued" or "Overvalued".
        risk_count: Number of risk items.
        growth_vs_peers: "outperforming" or "underperforming".
        profitability_vs_peers: "outperforming" or "underperforming".
        fcf_positive: Boolean flag for positive free cash flow.

    Returns:
        Dictionary with keys:
            - "recommendation": "BUY", "HOLD", or "AVOID".
            - "justification": Short explanation.
            - "valuation_status": Echo of the input valuation status.
            - "fundamental_strength": Computed fundamental strength.
            - "risk_level": Computed risk level.
    """
    # Compute derived attributes
    fundamentals = get_fundamental_strength(growth_vs_peers, profitability_vs_peers, fcf_positive)
    risk_level = get_risk_level(risk_count)

    # Primary recommendation logic (Step 1)
    if risk_level == "high":
        primary = "HOLD" if valuation_status == "Undervalued" else "AVOID"
    elif valuation_status == "Overvalued":
        primary = "AVOID" if fundamentals == "weak" else "HOLD"
    elif valuation_status == "Undervalued":
        primary = "BUY" if fundamentals == "strong" and risk_level == "low" else "HOLD"
    else:
        primary = "HOLD"

    # Directional bias logic (Step 2)
    bias: Optional[str] = None
    if primary not in ("BUY", "AVOID") and risk_level != "high":
        if valuation_status == "Overvalued" and fundamentals == "strong" and risk_level == "low":
            bias = "CAUTIOUS BUY"
        elif valuation_status == "Undervalued" and risk_level == "moderate" and fundamentals != "weak":
            bias = "CAUTIOUS BUY"
        elif valuation_status == "Overvalued" and fundamentals == "moderate":
            bias = "CAUTIOUS SELL"

    # Final recommendation assembly (Step 3)
    recommendation = f"{primary} / {bias}" if bias else primary

    # Build justification
    justification_parts: List[str] = []
    # Valuation insight
    if valuation_status == "Undervalued":
        justification_parts.append("DCF indicates the stock is undervalued.")
    elif valuation_status == "Overvalued":
        justification_parts.append("DCF indicates the stock is overvalued.")
    else:
        justification_parts.append("DCF indicates the stock is fairly valued.")
    # Business quality
    justification_parts.append(
        f"Fundamentals are {fundamentals} (growth {growth_vs_peers}, profitability {profitability_vs_peers}, "
        f"{'positive' if fcf_positive else 'negative'} free cash flow)."
    )
    # Risk impact
    justification_parts.append(f"Risk level is {risk_level} ({risk_count} flagged risk{'s' if risk_count != 1 else ''}).")

    justification = " ".join(justification_parts)

    return {
        "recommendation": recommendation,
        "justification": justification,
        "valuation_status": valuation_status,
        "fundamental_strength": fundamentals,
        "risk_level": risk_level,
    }


def generate_recommendation(
    current_price: Optional[float],
    dcf_val: Optional[float],
    risks: List[str],
    growth_vs_peers: str,
    profitability_vs_peers: str,
    fcf_positive: bool,
) -> Dict[str, Any]:
    """Legacy wrapper kept for backward compatibility.

    It derives the valuation_status from price vs DCF and forwards all parameters
    to the strict recommendation engine.
    """
    if current_price is None or dcf_val is None or current_price <= 0 or dcf_val <= 0:
        return {
            "recommendation": "HOLD",
            "justification": "Insufficient price or DCF data for a deterministic recommendation.",
            "valuation_status": "N/A",
        }
    valuation_status = "Undervalued" if current_price < dcf_val else "Overvalued" if current_price > dcf_val else "Fairly Valued"
    return get_recommendation(
        valuation_status=valuation_status,
        risk_count=len(risks),
        growth_vs_peers=growth_vs_peers,
        profitability_vs_peers=profitability_vs_peers,
        fcf_positive=fcf_positive,
    )
