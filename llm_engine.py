import os
import logging
from typing import Dict, Any, Optional
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Lazy imports/checks for Google Generative AI and OpenAI
HAS_GEMINI = False
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    pass

HAS_OPENAI = False
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    pass

def generate_fallback_report(
    target_ticker: str,
    comparison_data: Dict[str, Any],
    vals_for_display: Dict[str, Any],
    risks: list,
    recommendation: str,
    justification: str,
    pdf_path: str
) -> str:
    """
    Generates a structured, deterministic text report when no LLM API key is available.
    """
    logger.info("Generating fallback deterministic report (No API key found).")
    
    annual_df = comparison_data.get("annual")
    if annual_df is None:
        annual_df = pd.DataFrame()
        
    quarterly_df = comparison_data.get("quarterly")
    if quarterly_df is None:
        quarterly_df = pd.DataFrame()
        
    peers = comparison_data.get("peers_successful", [])
    
    report_lines = [
        f"==================================================================",
        f"FINANCIAL ANALYSIS REPORT: {target_ticker}",
        f"==================================================================",
        ""
    ]
    
    # 1. EXECUTIVE SUMMARY
    report_lines.append("1. EXECUTIVE SUMMARY")
    if not annual_df.empty and target_ticker in annual_df.columns:
        target_ann = annual_df[target_ticker]
        rev = target_ann.get('revenue')
        rev_growth = target_ann.get('revenue_growth_yoy')
        net_margin = target_ann.get('net_profit_margin')
        
        rev_str = f"${rev:,.2f}" if pd.notna(rev) else "N/A"
        growth_str = f"{rev_growth*100:.2f}%" if pd.notna(rev_growth) else "N/A"
        margin_str = f"{net_margin*100:.2f}%" if pd.notna(net_margin) else "N/A"
        
        report_lines.append(
            f"   {target_ticker} has reported annual revenue of {rev_str} with a YoY growth rate of {growth_str} "
            f"and a net profit margin of {margin_str}. The financial analysis indicates a status of {recommendation} "
            f"for investors based on deterministic valuation and risk assessment."
        )
    else:
        report_lines.append(f"   Financial data for {target_ticker} is limited. A recommendation of {recommendation} is assigned based on available indicators.")
    report_lines.append("")
    
    # 2. FINANCIAL PERFORMANCE SUMMARY
    report_lines.append("2. FINANCIAL PERFORMANCE SUMMARY")
    if not annual_df.empty and target_ticker in annual_df.columns:
        target_ann = annual_df[target_ticker]
        report_lines.extend([
            f"   Annual Performance:",
            f"   - Revenue: ${target_ann.get('revenue', 0):,.2f}" if pd.notna(target_ann.get('revenue')) else "   - Revenue: N/A",
            f"   - YoY Revenue Growth: {target_ann.get('revenue_growth_yoy', 0)*100:.2f}%" if pd.notna(target_ann.get('revenue_growth_yoy')) else "   - YoY Revenue Growth: N/A",
            f"   - EBIT Margin: {target_ann.get('ebit_margin', 0)*100:.2f}%" if pd.notna(target_ann.get('ebit_margin')) else "   - EBIT Margin: N/A",
            f"   - Net Profit Margin: {target_ann.get('net_profit_margin', 0)*100:.2f}%" if pd.notna(target_ann.get('net_profit_margin')) else "   - Net Profit Margin: N/A",
            f"   - Return on Equity (ROE): {target_ann.get('roe', 0)*100:.2f}%" if pd.notna(target_ann.get('roe')) else "   - Return on Equity (ROE): N/A",
            f"   - Free Cash Flow: ${target_ann.get('free_cash_flow', 0):,.2f}" if pd.notna(target_ann.get('free_cash_flow')) else "   - Free Cash Flow: N/A",
            f"   - FCF Margin: {target_ann.get('fcf_margin', 0)*100:.2f}%" if pd.notna(target_ann.get('fcf_margin')) else "   - FCF Margin: N/A",
        ])
    if not quarterly_df.empty and target_ticker in quarterly_df.columns:
        target_q = quarterly_df[target_ticker]
        report_lines.extend([
            f"   Quarterly Performance:",
            f"   - Date: {target_q.get('date', 'N/A')}",
            f"   - Revenue: ${target_q.get('revenue', 0):,.2f}" if pd.notna(target_q.get('revenue')) else "   - Revenue: N/A",
            f"   - QoQ Revenue Growth: {target_q.get('revenue_growth_qoq', 0)*100:.2f}%" if pd.notna(target_q.get('revenue_growth_qoq')) else "   - QoQ Revenue Growth: N/A",
            f"   - YoY Revenue Growth: {target_q.get('revenue_growth_yoy', 0)*100:.2f}%" if pd.notna(target_q.get('revenue_growth_yoy')) else "   - YoY Revenue Growth: N/A",
            f"   - EBIT Margin: {target_q.get('ebit_margin', 0)*100:.2f}%" if pd.notna(target_q.get('ebit_margin')) else "   - EBIT Margin: N/A",
            f"   - Net Profit Margin: {target_q.get('net_profit_margin', 0)*100:.2f}%" if pd.notna(target_q.get('net_profit_margin')) else "   - Net Profit Margin: N/A",
            f"   - Annualized ROE: {target_q.get('roe_annualized', 0)*100:.2f}%" if pd.notna(target_q.get('roe_annualized')) else "   - Annualized ROE: N/A",
            f"   - Free Cash Flow: ${target_q.get('free_cash_flow', 0):,.2f}" if pd.notna(target_q.get('free_cash_flow')) else "   - Free Cash Flow: N/A",
        ])
    report_lines.append("")
    
    # 3. PEER COMPARISON SUMMARY
    report_lines.append("3. PEER COMPARISON SUMMARY")
    if peers:
        report_lines.append(f"   Peer Analysis relative to: {', '.join(peers)}")
        if annual_df is not None and not annual_df.empty:
            metrics_subset = ["revenue_growth_yoy", "ebit_margin", "net_profit_margin", "roe", "fcf_margin"]
            valid_metrics = [m for m in metrics_subset if m in annual_df.index]
            df_sub = annual_df.loc[valid_metrics]
            for idx, row in df_sub.iterrows():
                row_str = f"     * {idx.upper():<20} | "
                for col in df_sub.columns:
                    val = row[col]
                    if pd.isna(val):
                        row_str += f"{col}: N/A | "
                    elif "margin" in idx or "growth" in idx or "roe" in idx:
                        row_str += f"{col}: {val*100:.2f}% | "
                    else:
                        row_str += f"{col}: ${val:,.0f} | "
                report_lines.append(row_str)
    else:
        report_lines.append("   No peer tickers were successfully analyzed for comparison.")
    report_lines.append("")
    
    # 4. VALUATION SUMMARY
    dcf = vals_for_display.get("dcf")
    graham = vals_for_display.get("graham")
    graham_num = vals_for_display.get("graham_number")
    price = vals_for_display.get("market_price")
    status = vals_for_display.get("valuation_status")
    
    dcf_str = f"${dcf:,.2f}" if isinstance(dcf, (int, float)) else "N/A"
    graham_str = f"${graham:,.2f}" if isinstance(graham, (int, float)) else "N/A"
    graham_num_str = f"${graham_num:,.2f}" if isinstance(graham_num, (int, float)) else "N/A"
    price_str = f"${price:,.2f}" if isinstance(price, (int, float)) else "N/A"
    
    report_lines.extend([
        "4. VALUATION SUMMARY",
        f"   - DCF Estimated Value: {dcf_str}",
        f"   - Graham Formula Value: {graham_str}",
        f"   - Graham Number: {graham_num_str}",
        f"   - Market Price: {price_str}",
        f"   - Valuation Status: {status}",
        ""
    ])
    
    # 5. RELATIVE VALUATION
    peg = vals_for_display.get("peg")
    ev_ebitda = vals_for_display.get("ev_ebitda")
    p_fcf = vals_for_display.get("p_fcf")
    interpretation = vals_for_display.get("relative_interpretation")
    
    peg_str = f"{peg:.2f}" if isinstance(peg, (int, float)) else "N/A"
    ev_ebitda_str = f"{ev_ebitda:.2f}" if isinstance(ev_ebitda, (int, float)) else "N/A"
    p_fcf_str = f"{p_fcf:.2f}" if isinstance(p_fcf, (int, float)) else "N/A"
    
    report_lines.extend([
        "5. RELATIVE VALUATION",
        f"   - PEG Ratio: {peg_str}",
        f"   - EV/EBITDA: {ev_ebitda_str}",
        f"   - Price-to-Free-Cash-Flow (P/FCF): {p_fcf_str}",
        f"   - Short interpretation: {interpretation}",
        ""
    ])
    
    # 6. RISK ANALYSIS
    report_lines.append("6. RISK ANALYSIS")
    if risks:
        for r in risks:
            report_lines.append(f"   - {r}")
    else:
        report_lines.append("   - No significant financial risks detected.")
    report_lines.append("")
    
    # 7. FINAL RECOMMENDATION
    report_lines.extend([
        "7. FINAL RECOMMENDATION",
        f"   - Recommendation: {recommendation}",
        f"   - Justification: {justification}",
        "",
        f"Note: PDF report has been generated at: {pdf_path}",
        ""
    ])
    
    return "\n".join(report_lines)

def generate_financial_report(target_ticker: str, comparison_data: Dict[str, Any], recommendation: Optional[str] = None) -> str:
    target_ticker = target_ticker.strip().upper()
    global HAS_GEMINI, HAS_OPENAI
    
    # 1. Fetch metadata and historical financials
    import data_fetcher
    import data_processor
    import metrics_engine
    import valuation_engine
    import risk_detector
    import recommendation_engine
    import pdf_report
    
    metadata = data_fetcher.fetch_ticker_metadata(target_ticker) or {}
    raw_data = data_fetcher.fetch_financial_data(target_ticker)
    
    # Run target's financials to get enriched series for DCF/margins
    if raw_data:
        processed_data = data_processor.process_statement_data(raw_data)
        enriched_metrics = metrics_engine.compute_financial_metrics(processed_data)
    else:
        processed_data = None
        enriched_metrics = None
        
    # Get current price
    info = metadata.get("info", {}) if metadata else {}
    current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("navPrice")
    if not current_price:
        try:
            import yfinance as yf
            t = yf.Ticker(target_ticker)
            h = t.history(period="1d")
            if not h.empty:
                current_price = float(h['Close'].iloc[-1])
        except Exception:
            current_price = None

    # Compute valuations
    if enriched_metrics:
        val_inputs = valuation_engine.prepare_valuation_inputs(metadata, enriched_metrics)
        dcf_val = valuation_engine.calculate_dcf(val_inputs.get("fcf_series"))
        
        shares = info.get("sharesOutstanding")
        if dcf_val is not None and shares and shares > 0:
            dcf_val = dcf_val / shares
            
        pe_ratio = val_inputs.get("pe_ratio")
        eps = val_inputs.get("eps")
        book_value = val_inputs.get("book_value")
        
        growth_rate = val_inputs.get("revenue_growth_yoy")
        g_rate_pct = growth_rate * 100 if growth_rate is not None else 0.0
        
        graham_val = valuation_engine.calculate_benjamin_graham(
            earnings_growth_rate=g_rate_pct,
            eps=eps,
            book_value=book_value
        )
        
        graham_num = valuation_engine.calculate_graham_number(
            eps=eps,
            book_value_per_share=book_value
        )
        
        gordon_val = valuation_engine.calculate_gordon_growth(val_inputs.get("dividend"))
        
        peg_val = valuation_engine.calculate_peg_ratio(
            pe_ratio=pe_ratio,
            earnings_growth_rate=val_inputs.get("revenue_growth_yoy")
        )
        
        ev_ebitda_val = valuation_engine.calculate_ev_ebitda(
            ev=val_inputs.get("ev"),
            ebitda=val_inputs.get("ebitda")
        )
        
        fcf_series = val_inputs.get("fcf_series")
        latest_fcf = None
        if isinstance(fcf_series, pd.Series) and not fcf_series.dropna().empty:
            latest_fcf = float(fcf_series.dropna().iloc[-1])
        p_fcf_val = valuation_engine.calculate_price_to_fcf(
            market_cap=val_inputs.get("market_cap"),
            fcf=latest_fcf
        )
    else:
        val_inputs = {}
        dcf_val = None
        graham_val = None
        graham_num = None
        gordon_val = None
        peg_val = None
        ev_ebitda_val = None
        p_fcf_val = None

    # Compute risks and recommendation
    risks = risk_detector.detect_risks(enriched_metrics or {}, val_inputs, comparison_data)
    
    valuations_dict = {
        "dcf": dcf_val,
        "graham": graham_val,
        "graham_number": graham_num,
        "gordon": gordon_val,
    }
    relative_vals = {
        "peg": peg_val,
        "ev_ebitda": ev_ebitda_val,
        "p_fcf": p_fcf_val
    }
    
    rec_result = recommendation_engine.generate_recommendation(
        current_price=current_price,
        valuations=valuations_dict,
        relative_valuations=relative_vals,
        risks=risks
    )
    
    rec_decision = rec_result["recommendation"]
    justification = rec_result["justification"]
    valuation_status = rec_result["valuation_status"]
    relative_interpretation = rec_result["relative_interpretation"]
    
    vals_for_display = {
        "dcf": dcf_val,
        "graham": graham_val,
        "graham_number": graham_num,
        "gordon": gordon_val,
        "market_price": current_price,
        "valuation_status": valuation_status,
        "peg": peg_val,
        "ev_ebitda": ev_ebitda_val,
        "p_fcf": p_fcf_val,
        "relative_interpretation": relative_interpretation
    }
    
    # Generate the PDF report
    news = metadata.get("news", []) or []
    pdf_path = pdf_report.generate_pdf_report(
        ticker=target_ticker,
        comparison=comparison_data,
        valuations=vals_for_display,
        risks=risks,
        recommendation=rec_decision,
        justification=justification,
        news=news
    )

    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    llm_commentary = ""
    
    # Try using Gemini first
    if HAS_GEMINI and gemini_key:
        logger.info("Generating report commentary using Gemini LLM...")
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = construct_prompt(target_ticker, comparison_data, vals_for_display, risks, rec_decision, justification)
            response = model.generate_content(prompt)
            llm_commentary = response.text
        except Exception as e:
            logger.error(f"Failed to generate report via Gemini: {e}")
            
    # Try using OpenAI second
    if not llm_commentary and HAS_OPENAI and openai_key:
        logger.info("Generating report commentary using OpenAI LLM...")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            
            prompt = construct_prompt(target_ticker, comparison_data, vals_for_display, risks, rec_decision, justification)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional financial analyst. Write structured, concise financial reports with no fluff."},
                    {"role": "user", "content": prompt}
                ]
            )
            llm_commentary = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate report via OpenAI: {e}")
            
    if llm_commentary:
        # Construct the final report combining LLM commentary (Sections 1-3) and deterministic sections (4-7)
        # Ensure LLM did not try to output sections 4-7
        clean_commentary = llm_commentary.split("4. VALUATION SUMMARY")[0].split("4. Valuation Summary")[0]
        
        report_lines = [
            f"==================================================================",
            f"FINANCIAL ANALYSIS REPORT: {target_ticker}",
            f"==================================================================",
            "",
            clean_commentary.strip(),
            "",
            "4. VALUATION SUMMARY",
            f"   - DCF Estimated Value: " + (f"${dcf_val:,.2f}" if isinstance(dcf_val, (int, float)) else "N/A"),
            f"   - Graham Formula Value: " + (f"${graham_val:,.2f}" if isinstance(graham_val, (int, float)) else "N/A"),
            f"   - Graham Number: " + (f"${graham_num:,.2f}" if isinstance(graham_num, (int, float)) else "N/A"),
            f"   - Market Price: " + (f"${current_price:,.2f}" if isinstance(current_price, (int, float)) else "N/A"),
            f"   - Valuation Status: {valuation_status}",
            "",
            "5. RELATIVE VALUATION",
            f"   - PEG Ratio: " + (f"{peg_val:.2f}" if isinstance(peg_val, (int, float)) else "N/A"),
            f"   - EV/EBITDA: " + (f"{ev_ebitda_val:.2f}" if isinstance(ev_ebitda_val, (int, float)) else "N/A"),
            f"   - Price-to-Free-Cash-Flow (P/FCF): " + (f"{p_fcf_val:.2f}" if isinstance(p_fcf_val, (int, float)) else "N/A"),
            f"   - Short interpretation: {relative_interpretation}",
            "",
            "6. RISK ANALYSIS",
        ]
        if risks:
            for r in risks:
                report_lines.append(f"   - {r}")
        else:
            report_lines.append("   - No significant financial risks detected.")
        report_lines.extend([
            "",
            "7. FINAL RECOMMENDATION",
            f"   - Recommendation: {rec_decision}",
            f"   - Justification: {justification}",
            "",
            f"Note: PDF report has been generated at: {pdf_path}",
            ""
        ])
        return "\n".join(report_lines)
            
    # Fallback if no LLM APIs configured or they failed
    return generate_fallback_report(
        target_ticker=target_ticker,
        comparison_data=comparison_data,
        vals_for_display=vals_for_display,
        risks=risks,
        recommendation=rec_decision,
        justification=justification,
        pdf_path=pdf_path
    )

def construct_prompt(
    target_ticker: str,
    comparison_data: Dict[str, Any],
    vals_for_display: Dict[str, Any],
    risks: list,
    recommendation: str,
    justification: str
) -> str:
    """
    Formats the comparison dataframes and metrics into a prompt for the LLM.
    """
    annual_df_str = ""
    quarterly_df_str = ""
    
    if isinstance(comparison_data.get("annual"), pd.DataFrame):
        annual_df_str = comparison_data["annual"].to_string()
    if isinstance(comparison_data.get("quarterly"), pd.DataFrame):
        quarterly_df_str = comparison_data["quarterly"].to_string()
        
    prompt = f"""
You are a senior financial analyst. Generate professional, concise commentary for {target_ticker} based on the side-by-side comparative data provided below.

CRITICAL INSTRUCTIONS:
- Do NOT perform any mathematical calculations yourself. Use the provided metrics exactly.
- Keep the commentary concise, clean, and structured (use markdown headings).
- Do NOT output any content for sections 4, 5, 6, or 7. ONLY output sections 1, 2, and 3.
- Do NOT add filler or generic definitions.
- Adhere strictly to the deterministic recommendation of: {recommendation} and justification: "{justification}". Integrate these findings into your summary commentary without changing them.

--- ANNUAL COMPARATIVE DATA ---
{annual_df_str}

--- QUARTERLY COMPARATIVE DATA ---
{quarterly_df_str}

--- DETECTED METRICS AND VALUATION SUMMARY (FOR CONTEXT) ---
- DCF Estimated Value: {vals_for_display.get('dcf')}
- Graham Formula Value: {vals_for_display.get('graham')}
- Graham Number: {vals_for_display.get('graham_number')}
- Market Price: {vals_for_display.get('market_price')}
- Valuation Status: {vals_for_display.get('valuation_status')}
- PEG Ratio: {vals_for_display.get('peg')}
- EV/EBITDA: {vals_for_display.get('ev_ebitda')}
- Price/FCF: {vals_for_display.get('p_fcf')}
- Short Interpretation: {vals_for_display.get('relative_interpretation')}
- Financial Risks Detected: {risks}

Please structure the output as follows:
1. EXECUTIVE SUMMARY: High-level overview of the financial health of {target_ticker} aligning with a recommendation of {recommendation}.
2. FINANCIAL PERFORMANCE SUMMARY: Analysis of Revenue Growth (YoY, QoQ), EBIT/Profit Margins, ROE, and Free Cash Flow.
3. PEER COMPARISON SUMMARY: Strengths and weaknesses relative to the peer group.
"""
    return prompt
