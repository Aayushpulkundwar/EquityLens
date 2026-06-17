import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def generate_recommendation(
    current_price: Optional[float],
    valuations: Dict[str, Any],
    relative_valuations: Dict[str, Any],
    risks: List[str]
) -> Dict[str, Any]:
    """Deterministic recommendation based on valuation, relative metrics, and risk assessment.
    Returns a dictionary with keys:
      - "recommendation": "BUY", "HOLD", or "AVOID"
      - "justification": A 2-3 line explanation of the decision
      - "valuation_status": "Undervalued", "Fairly Valued", "Overvalued", or "N/A"
      - "relative_interpretation": "cheap" or "expensive"
    """
    if current_price is None or current_price <= 0:
        return {
            "recommendation": "HOLD",
            "justification": "Recommendation is HOLD because the current market price is unavailable, preventing a proper margin of safety calculation.",
            "valuation_status": "N/A",
            "relative_interpretation": "expensive"
        }

    # 1. Valuation Status
    intrinsic_vals = []
    for key in ["dcf", "graham", "graham_number"]:
        val = valuations.get(key)
        if isinstance(val, (int, float)) and val > 0:
            intrinsic_vals.append(val)
    
    intrinsic_average = sum(intrinsic_vals) / len(intrinsic_vals) if intrinsic_vals else None
    
    if intrinsic_average is not None:
        margin_of_safety = (intrinsic_average - current_price) / intrinsic_average
        if margin_of_safety >= 0.15:
            valuation_status = "Undervalued"
        elif margin_of_safety <= -0.15:
            valuation_status = "Overvalued"
        else:
            valuation_status = "Fairly Valued"
    else:
        margin_of_safety = 0.0
        valuation_status = "N/A"

    # 2. Relative Valuation Interpretation (cheap vs expensive)
    cheap_signals = 0
    total_signals = 0
    
    peg = relative_valuations.get("peg")
    if peg is not None:
        total_signals += 1
        if peg < 1.5:
            cheap_signals += 1
            
    ev_ebitda = relative_valuations.get("ev_ebitda")
    if ev_ebitda is not None:
        total_signals += 1
        if ev_ebitda < 15.0:
            cheap_signals += 1
            
    p_fcf = relative_valuations.get("p_fcf")
    if p_fcf is not None:
        total_signals += 1
        if p_fcf < 20.0:
            cheap_signals += 1
            
    if total_signals > 0:
        relative_interpretation = "cheap" if (cheap_signals / total_signals) >= 0.5 else "expensive"
    else:
        relative_interpretation = "expensive" # conservative fallback

    # 3. Decision Logic
    num_risks = len(risks)
    
    if valuation_status == "Undervalued" and relative_interpretation == "cheap" and num_risks <= 1:
        rec = "BUY"
        justification = (
            f"The stock is BUY rated as it is currently undervalued relative to its intrinsic value of "
            f"${intrinsic_average:.2f} (market price: ${current_price:.2f}) and shows attractive relative valuation metrics "
            f"({relative_interpretation}) with minimal risk factor profile ({num_risks} risk(s) flagged)."
        )
    elif valuation_status == "Overvalued" or num_risks >= 3:
        rec = "AVOID"
        int_avg_val = intrinsic_average if intrinsic_average is not None else 0.0
        justification = (
            f"The stock is AVOID rated because it is overvalued compared to its intrinsic value of "
            f"${int_avg_val:.2f} (market price: ${current_price:.2f}) "
            f"and/or has significant financial risk exposure ({num_risks} risk(s) flagged)."
        )
    else:
        rec = "HOLD"
        justification = (
            f"The stock is HOLD rated because it is trading near its fair value or displays conflicting metrics. "
            f"While relative valuation is {relative_interpretation}, we have flagged {num_risks} risk factor(s) "
            f"which suggests a neutral or wait-and-see stance is appropriate."
        )

    return {
        "recommendation": rec,
        "justification": justification,
        "valuation_status": valuation_status,
        "relative_interpretation": relative_interpretation
    }
