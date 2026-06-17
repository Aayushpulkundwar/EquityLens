from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib import colors
import os
import logging
import pandas as pd
import time
import shutil

logger = logging.getLogger(__name__)

def generate_pdf_report(
    ticker: str,
    comparison: dict,
    valuations: dict,
    risks: list,
    recommendation: str,
    justification: str,
    news: list,
    output_path: str = None,
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

    # Title Banner
    elements.append(Paragraph(f"FINANCIAL ANALYSIS REPORT: {ticker}", title_style))
    elements.append(Spacer(1, 10))

    # --- SECTION 1: METRICS ---
    elements.append(Paragraph("1. FINANCIAL PERFORMANCE & PEER COMPARISON", h1_style))
    
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

    annual_df = comparison.get("annual")
    quarterly_df = comparison.get("quarterly")
    
    if annual_df is not None and not annual_df.empty:
        elements.extend(df_to_table(annual_df, "Annual Performance Stats"))
    if quarterly_df is not None and not quarterly_df.empty:
        elements.extend(df_to_table(quarterly_df, "Quarterly Performance Stats"))

    # --- SECTION 2: VALUATION ---
    elements.append(Paragraph("2. VALUATION SUMMARY", h1_style))
    
    # Intrinsic Valuations Table
    val_rows = [
        ["Intrinsic Model", "Estimated Value"],
        ["Discounted Cash Flow (DCF)", f"${valuations.get('dcf'):,.2f}" if isinstance(valuations.get('dcf'), (int, float)) else "N/A"],
        ["Benjamin Graham Formula", f"${valuations.get('graham'):,.2f}" if isinstance(valuations.get('graham'), (int, float)) else "N/A"],
        ["Graham Number", f"${valuations.get('graham_number'):,.2f}" if isinstance(valuations.get('graham_number'), (int, float)) else "N/A"],
        ["Current Market Price", f"${valuations.get('market_price'):,.2f}" if isinstance(valuations.get('market_price'), (int, float)) else "N/A"],
        ["Valuation Status", str(valuations.get("valuation_status", "N/A"))]
    ]
    
    val_table = Table(val_rows, hAlign='LEFT')
    val_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 5), (1, 5), "Helvetica-Bold"), # Bold for status row
        ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#F7FAFC")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(val_table)
    elements.append(Spacer(1, 10))

    # --- SECTION 3: RELATIVE VALUATION ---
    elements.append(Paragraph("3. RELATIVE VALUATION SUMMARY", h1_style))
    rel_rows = [
        ["Relative Metric", "Value", "Threshold/Benchmark"],
        ["PEG Ratio", f"{valuations.get('peg'):,.2f}" if isinstance(valuations.get('peg'), (int, float)) else "N/A", "Cheap if < 1.5"],
        ["EV/EBITDA", f"{valuations.get('ev_ebitda'):,.2f}" if isinstance(valuations.get('ev_ebitda'), (int, float)) else "N/A", "Cheap if < 15.0"],
        ["Price-to-Free-Cash-Flow (P/FCF)", f"{valuations.get('p_fcf'):,.2f}" if isinstance(valuations.get('p_fcf'), (int, float)) else "N/A", "Cheap if < 20.0"],
        ["Short Interpretation", str(valuations.get("relative_interpretation", "N/A")).upper(), "Based on valuation benchmarks"]
    ]
    rel_table = Table(rel_rows, hAlign='LEFT')
    rel_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 4), (1, 4), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(rel_table)
    elements.append(Spacer(1, 10))

    # --- SECTION 4: NEWS ---
    elements.append(Paragraph("4. RECENT COMPANY NEWS HEADLINES", h1_style))
    if news:
        for idx, item in enumerate(news[:5], 1):
            title = item.get("title") or "No Title"
            publisher = item.get("publisher") or "Unknown Publisher"
            pub_date = item.get("pubDate") or ""
            link = item.get("link")
            if link and (link.startswith("http://") or link.startswith("https://")):
                news_text = f"<b>{idx}. <a href='{link}' color='#1A365D'>{title}</a></b><br/><font color='#718096'>via {publisher} | {pub_date}</font>"
            else:
                news_text = f"<b>{idx}. {title}</b><br/><font color='#718096'>via {publisher} | {pub_date}</font>"
            elements.append(Paragraph(news_text, body_style))
            elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph("No recent news headlines available.", body_style))
    elements.append(Spacer(1, 10))

    # --- SECTION 5: RISKS ---
    elements.append(Paragraph("5. FINANCIAL RISK ANALYSIS", h1_style))
    if risks:
        risk_items = [ListItem(Paragraph(r, body_style), leftIndent=15, bulletOffsetY=-2) for r in risks]
        elements.append(ListFlowable(risk_items, bulletType='bullet', start='circle', bulletColor=colors.HexColor("#E53E3E")))
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
