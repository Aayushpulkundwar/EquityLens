from reportlab.lib.pagesizes import LETTER
import os
import logging
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem, Image

# Import news fetcher
from news_fetcher import get_company_news
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem, Image
import matplotlib
import feedparser
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
import os
import logging
import pandas as pd
import time
import shutil

logger = logging.getLogger(__name__)

def generate_llm_output(valuations: dict, risks: list, recommendation: str, comparison: dict) -> str:
    """Generate a concise, insight‑driven analyst commentary.

    The function synthesizes peer‑relative performance, cash‑flow health, valuation stance, and material risks into a 3‑5 sentence paragraph that aids investment decisions.
    """
    # Extract comparison data
    annual_df = comparison.get('annual')
    ticker = comparison.get('target', '')
    peer_cols = [c for c in (annual_df.columns if annual_df is not None else []) if c != ticker]

    # ----- Peer performance assessment -----
    performance_phrases = []
    if annual_df is not None and not annual_df.empty and ticker in annual_df.columns and peer_cols:
        for metric, label in [
            ("revenue_growth_yoy", "revenue growth"),
            ("ebit_margin", "EBIT margin"),
            ("roe", "ROE")
        ]:
            if metric in annual_df.index:
                company_val = annual_df.loc[metric, ticker]
                peer_median = annual_df.loc[metric, peer_cols].dropna().median()
                if pd.notna(company_val) and pd.notna(peer_median):
                    if company_val > peer_median:
                        performance_phrases.append(f"outperforms peers on {label}")
                    elif company_val < peer_median:
                        performance_phrases.append(f"lags peers on {label}")
    # Build a fluid summary of peer results
    if performance_phrases:
        perf_summary = ", ".join(performance_phrases)
    else:
        perf_summary = "shows mixed performance versus peers"

    # ----- Valuation and cash‑flow -----
    valuation_status = valuations.get('valuation_status', 'N/A').lower()
    fcf = valuations.get('free_cash_flow')
    fcf_desc = "generates positive free cash flow" if fcf and fcf > 0 else "has weak or negative free cash generation"

    # ----- Risk framing -----
    risk_count = len(risks)
    risk_sentence = f"{risk_count} risk factor{'s' if risk_count != 1 else ''} identified" if risk_count else "no material financial risks flagged"
    # Optionally highlight the most salient risk (first one)
    if risks:
        risk_sentence += f", notably {risks[0].lower()}"

    # ----- Compose final commentary (3‑5 sentences) -----
    sentences = [
        f"The company {perf_summary}.",
        f"It {fcf_desc}, supporting operational flexibility.",
        f"From a valuation viewpoint, the stock is considered {valuation_status}.",
        f"{risk_sentence.capitalize()}, suggesting investors weigh these factors against the valuation outlook."
    ]
    # Trim any empty sentences and join
    return " ".join(filter(None, sentences))
    """Generate a concise analyst‑style commentary.

    Builds a 3‑5 line paragraph summarising performance relative to peers,
    valuation outlook, and key risks without repeating raw numbers or using hardcoded phrases.
    """
    annual_df = comparison.get('annual')
    ticker = comparison.get('target', '')
    peer_cols = [c for c in annual_df.columns if c != ticker] if annual_df is not None else []
    
    # Determine peer-relative performance dynamically
    performance_phrases = []
    if annual_df is not None and not annual_df.empty and ticker in annual_df.columns and peer_cols:
        for metric, desc in [("revenue_growth_yoy", "revenue expansion"), ("ebit_margin", "operating profitability"), ("roe", "return on equity")]:
            if metric in annual_df.index:
                val = annual_df.loc[metric, ticker]
                peer_median = annual_df.loc[metric, peer_cols].dropna().median()
                if pd.notna(val) and pd.notna(peer_median):
                    status = "outperforming" if val > peer_median else "underperforming"
                    performance_phrases.append(f"{status} peers in {desc}")
    
    perf_summary = ", while ".join(performance_phrases) if performance_phrases else "showing mixed financial performance relative to peers"
    
    valuation_status = valuations.get('valuation_status', 'N/A').lower()
    fcf = valuations.get('free_cash_flow')
    fcf_desc = "generating positive free cash flow" if fcf and fcf > 0 else "exhibiting weak or negative cash generation"
    
    sentences = [
        f"The company demonstrates peer-relative traits, {perf_summary}.",
        f"Additionally, the firm is {fcf_desc}, which influences operational flexibility.",
        f"From a valuation perspective, the stock is currently classified as {valuation_status}.",
        f"With {len(risks)} financial risk factor(s) identified, investors should weigh this valuation status against prevailing risks."
    ]
    return " ".join(sentences)


def generate_pdf_report(
    ticker: str,
    comparison: dict,
    valuations: dict,
    risks: list,
    recommendation: str,
    justification: str,
    news: list,
    news_feed_url: str = None,
    output_path: str = None,
    llm_commentary: str = "",
    warnings: list = None,
    company_overview: str = "",
) -> str:
    """Create a clean, premium PDF report structured exactly as required.

    Parameters
    ----------
    ticker : str
        Stock ticker.
    comparison : dict
        Peer‑comparison data (contains "annual" and "quarterly" DataFrames).
    valuations : dict
        Calculated valuation numbers and status.
    risks : list
        List of risk strings.
    recommendation : str
        BUY / HOLD / AVOID.
    justification : str
        The 2-3 line deterministic justification.
    news : list of dicts
        Structured news items with title, link, publisher, pubDate.
    output_path : str, optional
        Destination file. If None, saves as "reports/{ticker}_financial_report.pdf".

    Returns
    -------
    str
        Path to the generated PDF.
    """
    # Determine final output path and temporary path
    if output_path is None:
        os.makedirs("reports", exist_ok=True)
        output_path = os.path.join("reports", f"{ticker}_financial_report.pdf")
    else:
        # Ensure directory of output_path exists
        dirname = os.path.dirname(output_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
    # Use a temporary file path to avoid locking issues
    temp_path = output_path + ".tmp"
    
    # --- PREPARE CONTENT ---
    # Ensure any leftover temporary file is removed before creating a new one
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass  # If removal fails, we'll overwrite during build
    # Initialize PDF document using temporary path to avoid file lock issues
    doc = SimpleDocTemplate(temp_path, pagesize=LETTER, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
    
    # Custom styles for premium look
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="PremiumTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1A365D"),
        alignment=0, # Left-aligned
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        name="PremiumH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#2C5282"),
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        name="PremiumH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4A5568"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        name="PremiumBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#2D3748")
    )
    
    rec_box_style = ParagraphStyle(
        name="PremiumRecBox",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#C53030") if recommendation == "AVOID" else colors.HexColor("#22543D") if recommendation == "BUY" else colors.HexColor("#744210")
    )

    elements = []

    # Logo Header (preserve aspect ratio, avoid stretching)
    logo_path = "primus_logo.png"
    if os.path.exists(logo_path):
        # Only set width; height will be scaled automatically to keep original proportions
        elements.append(Image(logo_path, width=200, height=75, hAlign='CENTER'))
        elements.append(Spacer(1, 15))

    # Title Banner
    elements.append(Paragraph(f"FINANCIAL ANALYSIS REPORT: {ticker}", title_style))
    elements.append(Spacer(1, 10))



    # --- WARNINGS BANNER (IF ANOMALIES DETECTED) ---
    if warnings:
        elements.append(Paragraph("WARNING: POTENTIAL DATA ANOMALIES", h2_style))
        for w in warnings:
            elements.append(Paragraph(f"<font color='#C53030'><b>Warning:</b> {w}</font>", body_style))
        elements.append(Spacer(1, 10))

    # --- SECTION 1: ONE-PAGE SUMMARY ---
    elements.append(Paragraph("ONE-PAGE SUMMARY", h2_style))
    summary_items = []
    
    # Calculate strengths relative to peer medians
    strengths = []
    annual_df = comparison.get("annual")
    if annual_df is not None and not annual_df.empty and ticker in annual_df.columns:
        peer_cols = [c for c in annual_df.columns if c != ticker]
        if peer_cols:
            metrics_to_compare = {
                "revenue_growth_yoy": "Revenue Growth (YoY)",
                "ebit_margin": "EBIT Margin",
                "net_profit_margin": "Net Profit Margin",
                "roe": "ROE",
                "fcf_margin": "FCF Margin"
            }
            for m_key, m_name in metrics_to_compare.items():
                if m_key in annual_df.index:
                    target_val = annual_df.loc[m_key, ticker]
                    peer_vals = annual_df.loc[m_key, peer_cols].dropna()
                    if pd.notna(target_val) and not peer_vals.empty:
                        peer_median = peer_vals.median()
                        if target_val > peer_median:
                            strengths.append(f"Outperforming peers on {m_name} ({target_val*100:.2f}% vs peer median {peer_median*100:.2f}%)")

    # Recommendation and valuation status (highlighted in red)
    summary_items.append(ListItem(Paragraph(f"<font color='#B22222'>Recommendation: {recommendation}</font>", body_style), bulletColor=colors.HexColor('#B22222')))
    summary_items.append(ListItem(Paragraph(f"<font color='#B22222'>Valuation status: {valuations.get('valuation_status', 'N/A')}</font>", body_style), bulletColor=colors.HexColor('#B22222')))
    # Strengths (green)
    for s in strengths:
        summary_items.append(ListItem(Paragraph(f"<font color='#228B22'>Strength: {s}</font>", body_style), bulletColor=colors.HexColor('#228B22')))
    # Risks (up to 3, red)
    for r in risks[:3]:
        summary_items.append(ListItem(Paragraph(f"<font color='#B22222'>Risk: {r}</font>", body_style), bulletColor=colors.HexColor('#B22222')))
    elements.append(ListFlowable(summary_items, bulletType='bullet'))
    elements.append(Spacer(1, 10))

    # --- SECTION 1: COMPANY OVERVIEW ---
    elements.append(Paragraph("1. COMPANY OVERVIEW", h1_style))
    if company_overview:
        for p in company_overview.split("\n\n"):
            p_text = p.strip().replace("\n", " ")
            if p_text:
                elements.append(Paragraph(p_text, body_style))
                elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph("Company overview details are not available for this ticker.", body_style))
    elements.append(Spacer(1, 10))

    # --- SECTION 2: METRICS ---
    elements.append(Paragraph("2. FINANCIAL PERFORMANCE & PEER COMPARISON", h1_style))
    
    def df_to_table(df, title):
        if df is None or df.empty:
            return []
        
        # Format headers and cells nicely
        headers = ["Metric"] + list(df.columns)
        table_data = [headers]
        
        for idx, row in df.iterrows():
            formatted_row = [str(idx).replace("_", " ").title()]
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    formatted_row.append("N/A")
                elif "margin" in str(idx) or "growth" in str(idx) or "roe" in str(idx):
                    # Values might already be string formatted like "15.74%" or raw float
                    if isinstance(val, (int, float)):
                        formatted_row.append(f"{val*100:.2f}%")
                    else:
                        formatted_row.append(str(val))
                elif isinstance(val, (int, float)) and abs(val) > 1e6:
                    formatted_row.append(f"${val:,.0f}")
                else:
                    formatted_row.append(str(val))
            table_data.append(formatted_row)
            
        tbl = Table(table_data, hAlign='LEFT')
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2D3748")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
        ]))
        return [Paragraph(title, h2_style), Spacer(1, 4), tbl, Spacer(1, 10)]

    def create_bar_chart(metric, df, ticker):
        """Generate a bar chart PNG. 
        Supports DataFrames where metrics are rows or columns.
        """
        # Ensure charts directory exists
        charts_dir = os.path.join(os.getcwd(), "charts")
        os.makedirs(charts_dir, exist_ok=True)
        # Check if metric is index (rows) or columns
        if metric in df.index:
            values = df.loc[metric]
        elif metric in df.columns:
            values = df[metric]
        else:
            return None
        plt.figure(figsize=(6, 3))
        # Drop NaN values for clean plotting
        plot_values = values.dropna()
        bars = plt.bar(plot_values.index.astype(str), plot_values.values, color="#1A365D")
        plt.title(f"{metric.replace('_', ' ').title()} Comparison")
        plt.xticks(rotation=45, ha='right')
        
        # Apply log scale for absolute currencies (revenue, net income, FCF) if all values are positive
        if metric in ["revenue", "net_income", "free_cash_flow"] and not plot_values.empty:
            if (plot_values > 0).all():
                plt.yscale('log')
                plt.ylabel("Value (Log Scale)")
            else:
                plt.ylabel("Value")
        else:
            plt.ylabel("Percentage" if "margin" in metric or "growth" in metric or "roe" in metric else "Value")

        for bar in bars:
            height = bar.get_height()
            if pd.notna(height):
                # Annotate values cleanly
                if "margin" in metric or "growth" in metric or "roe" in metric:
                    ann_text = f"{height*100:.1f}%" if abs(height) <= 1.0 else f"{height:.1f}%"
                elif abs(height) >= 1e9:
                    ann_text = f"${height/1e9:.1f}B"
                elif abs(height) >= 1e6:
                    ann_text = f"${height/1e6:.1f}M"
                else:
                    ann_text = f"{height:.1f}"
                plt.annotate(ann_text, xy=(bar.get_x() + bar.get_width() / 2, height),
                             xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
                             
        chart_path = os.path.join(charts_dir, f"{ticker}_{metric}.png")
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150)
        plt.close()
        return chart_path

    annual_df = comparison.get("annual")

    def fetch_company_news(company_name: str, limit: int = 5) -> list:
        """Fetch top news headlines for the company using the news_fetcher module."""
        try:
            news_items = get_company_news(company_name)
            # Trim to limit
            return news_items[:limit]
        except Exception as e:
            logger.error(f"Failed to fetch news for {company_name}: {e}")
            return []

    quarterly_df = comparison.get("quarterly")
    
    if annual_df is not None and not annual_df.empty:
        elements.extend(df_to_table(annual_df, "Annual Performance Stats"))
    if quarterly_df is not None and not quarterly_df.empty:
        elements.extend(df_to_table(quarterly_df, "Quarterly Performance Stats"))

    # --- SECTION 2: VALUATION ---
    # Insert bar charts for key metrics after tables
    chart_metrics = ["revenue", "net_income", "roe"]
    for metric in chart_metrics:
        # Choose dataframe where the metric exists as a column
        chart_df = None
        if annual_df is not None and metric in annual_df.index:
            chart_df = annual_df
        elif quarterly_df is not None and metric in quarterly_df.index:
            chart_df = quarterly_df
        if chart_df is not None:
            chart_path = create_bar_chart(metric, chart_df, ticker)
            if chart_path and os.path.exists(chart_path):
                elements.append(Paragraph(f"{metric.replace('_', ' ').title()} Comparison Chart", h2_style))
                elements.append(Spacer(1, 4))
                img = Image(chart_path, width=500, height=300)
                elements.append(img)
                elements.append(Spacer(1, 10))

    # --- SECTION 2: VALUATION SUMMARY ---
    # One Page Summary generation (top priority)
    # Prepare metrics and strengths
    metrics = {}
    # Example strengths extraction (use placeholders if not available)
    strengths = []
    if annual_df is not None:
        # Example: highest revenue growth
        try:
            rev_growth = annual_df.loc['revenue_growth_yoy']
            top_peer = rev_growth.idxmax()
            strengths.append(f"Strong revenue growth YoY compared to peers, leading with {top_peer}")
        except Exception as e:
            logger.error(f"Failed to compute revenue growth strength: {e}")
    elements.append(Paragraph("3. VALUATION SUMMARY (DCF-BASED)", h1_style))

    val_rows = [
        ["DCF Estimated Value", f"${valuations.get('dcf'):,.2f}" if isinstance(valuations.get('dcf'), (int, float)) else "N/A"],
        ["Current Market Price", f"${valuations.get('market_price'):,.2f}" if isinstance(valuations.get('market_price'), (int, float)) else "N/A"],
        ["Valuation Status", str(valuations.get("valuation_status", "N/A"))]
    ]
    
    val_table = Table(val_rows, hAlign='LEFT', colWidths=[200, 150])
    val_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), # Labels in bold
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),      # Values in regular font
        ("FONTNAME", (1, 2), (1, 2), "Helvetica-Bold"),  # Bold for status value
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#F7FAFC")), # Highlight status row
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(val_table)
    elements.append(Spacer(1, 10))

    # --- SECTION 4: NEWS ---
    elements.append(Paragraph("4. RECENT COMPANY NEWS HEADLINES", h1_style))
    # Fetch news relevant to the target ticker
    news_items = get_company_news(ticker)
    static_news = [item.get('title', 'No title') for item in news_items[:5]]
    for idx, title in enumerate(static_news, 1):
        news_text = f"<b>{idx}. {title}</b>"
        elements.append(Paragraph(news_text, body_style))
        elements.append(Spacer(1, 6))
    elements.append(Spacer(1, 10))
    elements.append(Spacer(1, 10))

    # --- SECTION 5: RISKS ---
    elements.append(Paragraph("5. FINANCIAL RISK ANALYSIS", h1_style))
    if risks:
        risk_items = [ListItem(Paragraph(r, body_style), leftIndent=15, bulletOffsetY=-2) for r in risks]
        elements.append(ListFlowable(risk_items, bulletType='bullet', bulletColor=colors.HexColor('#E53E3E')))
    else:
        elements.append(Paragraph("No significant financial risks detected.", body_style))
    elements.append(Spacer(1, 12))

    # --- SECTION 6: RECOMMENDATION ---
    elements.append(Paragraph("6. FINAL DETERMINISTIC RECOMMENDATION", h1_style))
    
    # Banner/Box for recommendation
    bg_color = colors.HexColor("#FED7D7") if recommendation == "AVOID" else colors.HexColor("#C6F6D5") if recommendation == "BUY" else colors.HexColor("#FEFCBF")
    border_color = colors.HexColor("#E53E3E") if recommendation == "AVOID" else colors.HexColor("#38A169") if recommendation == "BUY" else colors.HexColor("#D69E2E")
    
    rec_text = f"RECOMMENDATION: {recommendation}"
    rec_box = Table([[Paragraph(rec_text, rec_box_style)]], colWidths=[530])
    rec_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 1.5, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(rec_box)
    elements.append(Spacer(1, 8))
    
    elements.append(Paragraph(f"<b>Justification:</b> {justification}", body_style))
    # EXECUTIVE SUMMARY SECTION (added at end of report)
    elements.append(Paragraph("EXECUTIVE SUMMARY", h1_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(llm_commentary, body_style))

    # Build document
    try:
        doc.build(elements)
        # Move temporary PDF to final location
        # Safely replace the final PDF, handling existing locked files
        try:
            # os.replace overwrites if destination exists
            os.replace(temp_path, output_path)
        except PermissionError:
            # If the target PDF is locked, save to a timestamped alternative file
            alt_path = output_path.replace('.pdf', f'_alt_{int(time.time())}.pdf')
            shutil.move(temp_path, alt_path)
            logger.warning(f"Target PDF was locked; saved report to alternative path: {alt_path}")
        except Exception as e:
            # Cleanup temp file on unexpected errors
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"Failed to move temporary PDF to final destination: {e}", exc_info=True)
            raise
        logger.info(f"PDF report successfully generated at: {os.path.abspath(output_path)}")
    except Exception as e:
        # Cleanup temp file if exists
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Failed to compile PDF report: {e}", exc_info=True)
        raise

    return os.path.abspath(output_path)
