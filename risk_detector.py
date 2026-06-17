import logging
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)

def _get_latest_value(source: Any, key: str) -> Optional[float]:
    """Helper to safely get the latest float value from a DataFrame or dict."""
    if source is None:
        return None
    try:
        if isinstance(source, pd.DataFrame):
            if key in source.columns and not source[key].dropna().empty:
                return float(source[key].dropna().iloc[-1])
            elif key in source.index and not source.loc[key].dropna().empty:
                # In case it is transposed
                return float(source.loc[key].dropna().iloc[-1])
            return None
        elif isinstance(source, dict):
            val = source.get(key)
            if val is not None:
                return float(val)
        return None
    except Exception:
        return None

def detect_risks(
    enriched_metrics: Dict[str, Any],
    valuation_inputs: Dict[str, Any],
    comparison: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Detect common financial risk flags based on company metrics and peers.
    Returns a list of human‑readable risk descriptions.
    """
    risks: List[str] = []
    
    annual_source = enriched_metrics.get("annual")
    quarterly_source = enriched_metrics.get("quarterly")
    
    # 1. Negative or slowing revenue growth
    # YoY growth
    rev_growth = _get_latest_value(annual_source, "revenue_growth_yoy")
    if rev_growth is not None:
        if rev_growth < 0:
            risks.append(f"Negative annual revenue growth ({rev_growth*100:.2f}%)")
        elif rev_growth < 0.02:
            risks.append(f"Slowing annual revenue growth ({rev_growth*100:.2f}% < 2%)")
            
    # Negative QoQ growth (quarterly revenue growth)
    qoq_growth = _get_latest_value(quarterly_source, "revenue_growth_qoq")
    if qoq_growth is not None and qoq_growth < 0:
        risks.append(f"Negative quarterly revenue growth (QoQ: {qoq_growth*100:.2f}%)")

    # 2. Weak margins
    net_margin = _get_latest_value(annual_source, "net_profit_margin")
    ebit_margin = _get_latest_value(annual_source, "ebit_margin")
    if net_margin is not None and net_margin < 0.05:
        risks.append(f"Weak net profit margin ({net_margin*100:.2f}% < 5%)")
    if ebit_margin is not None and ebit_margin < 0.08:
        risks.append(f"Weak EBIT margin ({ebit_margin*100:.2f}% < 8%)")

    # 3. Low or negative FCF
    fcf = valuation_inputs.get("fcf_series")
    if isinstance(fcf, pd.Series) and not fcf.dropna().empty:
        latest_fcf = fcf.dropna().iloc[-1]
        if latest_fcf <= 0:
            risks.append("Negative free cash flow")
        else:
            # FCF margin
            fcf_margin = _get_latest_value(annual_source, "fcf_margin")
            if fcf_margin is not None and fcf_margin < 0.03:
                risks.append(f"Weak free cash flow margin ({fcf_margin*100:.2f}% < 3%)")
                
    # Overvaluation signals
    pe = valuation_inputs.get("pe_ratio")
    if pe is not None and pe > 30:
        risks.append(f"High P/E ratio ({pe:.2f} > 30)")
        
    # 4. Underperformance vs peers
    if comparison:
        target_ticker = comparison.get("target")
        annual_df = comparison.get("annual")
        if annual_df is not None and not annual_df.empty and target_ticker in annual_df.columns:
            peer_cols = [c for c in annual_df.columns if c != target_ticker]
            if peer_cols:
                for metric in ["revenue_growth_yoy", "net_profit_margin", "roe", "fcf_margin"]:
                    if metric in annual_df.index:
                        target_val = annual_df.loc[metric, target_ticker]
                        peer_vals = annual_df.loc[metric, peer_cols].dropna()
                        if pd.notna(target_val) and not peer_vals.empty:
                            peer_median = peer_vals.median()
                            if target_val < peer_median:
                                metric_name = metric.replace('_', ' ').title().replace('Yoy', 'YoY')
                                risks.append(f"Underperforming peers on {metric_name} ({target_val*100:.2f}% vs peer median {peer_median*100:.2f}%)")
                                
    return risks
