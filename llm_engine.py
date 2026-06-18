import os
import json
import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import requests

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
    price = vals_for_display.get("market_price")
    status = vals_for_display.get("valuation_status")

    dcf_str = f"${dcf:,.2f}" if isinstance(dcf, (int, float)) else "N/A"
    price_str = f"${price:,.2f}" if isinstance(price, (int, float)) else "N/A"

    report_lines.extend([
        "4. VALUATION SUMMARY (DCF-BASED)",
        f"   - DCF Estimated Value: {dcf_str}",
        f"   - Market Price: {price_str}",
        f"   - Valuation Status: {status}",
        "",
    ])
    
    # 5. RELATIVE VALUATION
    # (Removed per user request – only DCF model retained)
    # No relative valuation metrics are displayed.
    
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
        dcf_val = valuation_engine.dcf_valuation(val_inputs.get("fcf_series"))
        shares = info.get("sharesOutstanding")
        if dcf_val is not None and shares and shares > 0:
            dcf_val = dcf_val / shares
    else:
        val_inputs = {}
        dcf_val = None

    # Compute risks and recommendation
    risks = risk_detector.detect_risks(enriched_metrics or {}, val_inputs, comparison_data)
    rec_result = recommendation_engine.generate_recommendation(
        current_price=current_price,
        dcf_val=dcf_val,
        risks=risks,
    )

    
    rec_decision = rec_result["recommendation"]
    justification = rec_result["justification"]
    valuation_status = rec_result["valuation_status"]
    
    # Obtain formatted latest performance metrics for reporting
    latest_summary = metrics_engine.format_latest_metrics_summary(enriched_metrics or {})
    annual_metrics = latest_summary.get('annual', {})
    
    vals_for_display = {
        "dcf": dcf_val,
        "market_price": current_price,
        "valuation_status": valuation_status,
        # Key performance metrics
        "revenue_growth_yoy": annual_metrics.get('revenue_growth_yoy'),
        "ebit_margin": annual_metrics.get('ebit_margin'),
        "net_profit_margin": annual_metrics.get('net_profit_margin'),
        "roe": annual_metrics.get('roe'),
        "free_cash_flow": annual_metrics.get('free_cash_flow'),
        "fcf_margin": annual_metrics.get('fcf_margin'),
    }
    

    
    # (Placeholder) PDF generation will be moved after LLM commentary
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    # Build concise analyst commentary adhering to style guidelines
    # Valuation phrasing based on status
    if valuation_status == "Undervalued":
        valuation_phrase = "trades below its intrinsic value"
    elif valuation_status == "Overvalued":
        valuation_phrase = "trades above its intrinsic value"
    else:
        valuation_phrase = "appears fairly valued"
    # Compose 3–5 sentence paragraph without metric lists or repetition
    llm_commentary = (
        f"{target_ticker} shows limited growth and thin margins, indicating competitive pressure. "
        f"Its cash‑flow generation is modest, constraining financial flexibility. "
        f"The DCF assessment {valuation_phrase}, and with {len(risks)} risk factor(s) identified, a cautious stance is advisable."
    )
    # ------- STOCK OVERVIEW -------
    # Build a concise overview for console output
    overview_lines = []
    overview_lines.append(f"STOCK OVERVIEW: {target_ticker}")
    # Market position (simple placeholder based on revenue relative to peers)
    try:
        peer_revenues = [comp['revenue'] for comp in comparison_data.values() if isinstance(comp.get('revenue'), (int, float))]
        company_rev = vals_for_display.get('revenue') or 0
        if peer_revenues:
            median_rev = sorted(peer_revenues)[len(peer_revenues)//2]
            position = "above" if company_rev > median_rev else "below" if company_rev < median_rev else "on par with"
            overview_lines.append(f"Market position: {position} peers (revenue)")
    except Exception:
        overview_lines.append("Market position: N/A")
    # Growth standing (YoY revenue growth)
    yoy = vals_for_display.get('revenue_growth_yoy')
    if isinstance(yoy, (int, float)):
        growth = "high" if yoy > 15 else "moderate" if yoy > 5 else "low"
        overview_lines.append(f"Growth standing: {growth} YoY ({yoy:.2f}%)")
    else:
        overview_lines.append("Growth standing: N/A")
    # Profitability (EBIT margin)
    ebit_margin = vals_for_display.get('ebit_margin')
    if isinstance(ebit_margin, (int, float)):
        profitability = "high" if ebit_margin > 30 else "moderate" if ebit_margin > 15 else "low"
        overview_lines.append(f"Profitability: {profitability} EBIT margin ({ebit_margin:.2f}%)")
    else:
        overview_lines.append("Profitability: N/A")
    # Efficiency (ROE)
    roe = vals_for_display.get('roe')
    if isinstance(roe, (int, float)):
        efficiency = "high" if roe > 20 else "moderate" if roe > 10 else "low"
        overview_lines.append(f"Efficiency: {efficiency} ROE ({roe:.2f}%)")
    else:
        overview_lines.append("Efficiency: N/A")
    # Cash flow strength
    fcf = vals_for_display.get('free_cash_flow')
    fcf_margin = vals_for_display.get('fcf_margin')
    if isinstance(fcf_margin, (int, float)):
        cash_strength = "strong" if fcf_margin > 20 else "moderate" if fcf_margin > 10 else "weak"
        overview_lines.append(f"Cash flow strength: {cash_strength} (FCF margin {fcf_margin:.2f}%)")
    else:
        overview_lines.append("Cash flow strength: N/A")
    # Valuation status
    overview_lines.append(f"Valuation status: {vals_for_display.get('valuation_status', 'N/A')}")

    # Print the stock overview (max 7 lines)
    print("\n".join(overview_lines))

    # ------- RECENT COMPANY NEWS -------
    def get_company_news(company_name: str, limit: int = 5) -> List[str]:
        """Fetch latest news headlines for a company.
        Tries NewsAPI if NEWSAPI_KEY env var is set, otherwise falls back to a simple RSS Google News feed.
        Returns a list of headline strings.
        """
        api_key = os.getenv('NEWSAPI_KEY')
        headers = {}
        if api_key:
            try:
                url = "https://newsapi.org/v2/everything"
                params = {
                    'q': company_name,
                    'pageSize': limit,
                    'sortBy': 'publishedAt',
                    'apiKey': api_key,
                }
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return [article.get('title', '') for article in data.get('articles', [])][:limit]
            except Exception as e:
                logger.warning(f"NewsAPI request failed: {e}")
        # Fallback: RSS feed via Google News
        try:
            rss_url = f"https://news.google.com/rss/search?q={company_name.replace(' ', '+')}"
            resp = requests.get(rss_url, timeout=10)
            if resp.status_code == 200:
                # Very simple extraction without external libs
                import re
                titles = re.findall(r"<title>(.*?)</title>", resp.text)
                # First title is the feed title, skip it
                return [t for t in titles[1:limit+1] if t]
        except Exception as e:
            logger.warning(f"RSS news fetch failed: {e}")
        return []

    news_headlines = get_company_news(target_ticker)
    if news_headlines:
        print("\nRECENT COMPANY NEWS:")
        for hl in news_headlines:
            print(f"- {hl}")
    else:
        print("\nRECENT COMPANY NEWS: No recent headlines found.")

    # ------- FULL FINANCIAL REPORT (PDF) -------
    # Placeholder for moved PDF generation

    # Generate LLM commentary before PDF generation
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
            response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
            llm_commentary = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate report via OpenAI: {e}")
    # Fallback deterministic commentary if LLM APIs unavailable or failed
    if not llm_commentary:
        try:
            from pdf_report import generate_llm_output
            llm_commentary = generate_llm_output(vals_for_display, risks, rec_decision, comparison_data)
        except Exception as e:
            logger.error(f"Failed to generate deterministic LLM commentary: {e}")

    # Generate the PDF report, now including LLM commentary
    pdf_path = pdf_report.generate_pdf_report(
        ticker=target_ticker,
        comparison=comparison_data,
        valuations=vals_for_display,
        risks=risks,
        recommendation=rec_decision,
        justification=justification,
        news=metadata.get("news", []) or [],
        llm_commentary=llm_commentary
    )

    # Optionally print LLM output for console
    print("\nLLM OUTPUT:\n")
    print(llm_commentary if llm_commentary else "No LLM commentary generated.")

    return pdf_path

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
- Market Price: {vals_for_display.get('market_price')}
- Valuation Status: {vals_for_display.get('valuation_status')}
- Financial Risks Detected: {risks}

Please structure the output as follows:
1. EXECUTIVE SUMMARY: High-level overview of the financial health of {target_ticker} aligning with a recommendation of {recommendation}.
2. FINANCIAL PERFORMANCE SUMMARY: Analysis of Revenue Growth (YoY, QoQ), EBIT/Profit Margins, ROE, and Free Cash Flow.
3. PEER COMPARISON SUMMARY: Strengths and weaknesses relative to the peer group.
"""
    return prompt
