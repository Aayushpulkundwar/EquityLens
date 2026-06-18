import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def generate_recommendation(
    current_price: Optional[float],
    dcf_val: Optional[float],
    risks: List[str]
) -> Dict[str, Any]:
    """Deterministic recommendation based on DCF valuation and risk assessment.
    
    Returns a dictionary with keys:
      - "recommendation": "BUY", "HOLD", or "AVOID"
      - "justification": A dynamic explanation of the decision matching computed values
      - "valuation_status": "Undervalued", "Fairly Valued", "Overvalued", or "N/A"
    """
    if current_price is None or current_price <= 0 or dcf_val is None or dcf_val <= 0:
        return {
            "recommendation": "HOLD",
            "justification": "Recommendation is HOLD because either the current market price or the DCF valuation is unavailable.",
            "valuation_status": "N/A"
        }

    # 1. Valuation Status Fix (Undervalued if price < dcf_val, Overvalued if price > dcf_val)
    if current_price < dcf_val:
        valuation_status = "Undervalued"
    elif current_price > dcf_val:
        valuation_status = "Overvalued"
    else:
        valuation_status = "Fairly Valued"

    # 2. Decision Logic & Dynamic Justifications
    num_risks = len(risks)
    
    if valuation_status == "Undervalued":
        if num_risks >= 3:
            rec = "HOLD"
            justification = "The stock is trading below its intrinsic value, indicating potential upside, but risks reduce confidence."
        else:
            rec = "BUY"
            justification = f"The stock is trading below its intrinsic value, indicating potential upside with low risk ({num_risks} risk(s) flagged)."
    elif valuation_status == "Overvalued":
        rec = "AVOID"
        justification = "The stock is trading above its intrinsic value, suggesting limited upside and downside risk."
    else:  # Fairly Valued
        rec = "HOLD"
        justification = "The stock is trading near its intrinsic value, suggesting fair valuation and balanced risk-reward profile."

    return {
        "recommendation": rec,
        "justification": justification,
        "valuation_status": valuation_status
    }
