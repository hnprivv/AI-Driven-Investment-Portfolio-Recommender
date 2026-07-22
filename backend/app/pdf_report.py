import datetime
import io as _io

import pandas as pd
import plotly.express as px
from fpdf import FPDF


def generate_pdf_report(username: str, user: dict, overview: dict) -> bytes:
    """Mirrors pages/1_Overview.py's generate_pdf_report exactly, just fed from
    the /portfolio/overview computation instead of Streamlit session state."""

    profile = overview["profile"]
    curve = overview["curve"]
    holdings_by_category = overview["holdings_by_category"]
    holdings = overview["holdings"]

    # Equity curve chart image
    curve_img_bytes = None
    if curve:
        _curve_df = pd.DataFrame({
            "Date": pd.to_datetime([p["date"] for p in curve]),
            "Portfolio Value": [p["value"] for p in curve],
        })
        _fig_c = px.line(
            _curve_df, x="Date", y="Portfolio Value",
            template="plotly_white", color_discrete_sequence=["#F59E0B"],
        )
        _fig_c.add_hline(y=1.0, line_dash="dot", line_color="rgba(0,0,0,0.3)")
        _fig_c.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            font=dict(color="#111111", family="Arial"),
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(gridcolor="rgba(0,0,0,0.08)", linecolor="rgba(0,0,0,0.2)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0.08)", linecolor="rgba(0,0,0,0.2)"),
        )
        curve_img_bytes = _fig_c.to_image(format="png", width=900, height=350, scale=2)

    # Allocation pie chart image — only built if the user has holdings to break down
    alloc_img_bytes = None
    if holdings_by_category:
        _fig_a = px.pie(
            values=list(holdings_by_category.values()),
            names=list(holdings_by_category.keys()),
            color_discrete_sequence=["#F59E0B", "#FCD34D", "#B45309", "#78350F"],
        )
        _fig_a.update_layout(
            paper_bgcolor="#FFFFFF",
            font=dict(color="#111111", family="Arial"),
            legend=dict(font=dict(color="#111111")),
            margin=dict(l=20, r=20, t=20, b=20),
        )
        alloc_img_bytes = _fig_a.to_image(format="png", width=600, height=400, scale=2)

    # Build PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 12, "AIPRS Portfolio Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 96)
    pdf.cell(0, 5,
        f"Generated for {username}  |  "
        f"{datetime.datetime.now(datetime.timezone.utc).strftime('%d %B %Y, %H:%M UTC')}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.ln(4)
    pdf.set_draw_color(217, 119, 6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Investor Profile
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 8, "Investor Profile", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    profile_rows = [
        ("Risk Profile", overview["risk_profile"]),
        ("Age", str(profile["age"])),
        ("Annual Income Range", str(profile["income_range"])),
        ("Investment Horizon", str(profile["investment_horizon"])),
        ("Experience Level", str(profile["experience"])),
        ("Primary Goal", str(profile["goals"])),
        ("Risk Tolerance Score", f"{profile['risk_tolerance']} / 10"),
    ]
    for label, value in profile_rows:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(90, 90, 96)
        pdf.cell(90, 7, label)
        pdf.set_text_color(17, 17, 17)
        pdf.cell(90, 7, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_draw_color(217, 119, 6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Portfolio Metrics
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 8, f"Portfolio Metrics  ({overview['metrics_source']})", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    metric_cols = [
        ("Total Return (1Y)", f"{overview['total_return']:.2%}"),
        ("Annualised Volatility", f"{overview['ann_vol']:.2%}"),
        ("Sharpe Ratio", f"{overview['sharpe']:.2f}"),
    ]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(90, 90, 96)
    for label, _ in metric_cols:
        pdf.cell(63, 6, label)
    pdf.ln()
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(17, 17, 17)
    for _, value in metric_cols:
        pdf.cell(63, 9, value)
    pdf.ln(12)
    pdf.set_draw_color(217, 119, 6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Equity curve
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 8, "Portfolio Performance (1Y)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    if curve_img_bytes:
        pdf.image(_io.BytesIO(curve_img_bytes), x=10, w=190)
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(90, 90, 96)
        pdf.cell(0, 5, f"Figure: Growth of your portfolio over the past year ({overview['metrics_source']}).",
                  new_x="LMARGIN", new_y="NEXT", align="C")
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(90, 90, 96)
        pdf.cell(0, 8, "Chart unavailable - market data could not be fetched.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_draw_color(217, 119, 6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Asset Allocation
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 8, "Your Asset Allocation", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    if alloc_img_bytes:
        pdf.image(_io.BytesIO(alloc_img_bytes), x=30, w=150)
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(90, 90, 96)
        pdf.cell(0, 5, "Figure: Breakdown of your entered holdings by asset class.",
                  new_x="LMARGIN", new_y="NEXT", align="C")
    else:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(90, 90, 96)
        pdf.multi_cell(0, 6,
            "No holdings entered yet, so an allocation breakdown isn't available. "
            "Add your holdings on the Overview page, or visit AI Recommendations "
            "for a personalized suggested allocation.")
    pdf.ln(4)

    # Holdings
    if holdings:
        pdf.set_draw_color(217, 119, 6)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(245, 158, 11)
        pdf.cell(0, 8, "Your Holdings", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(90, 90, 96)
        pdf.cell(80, 7, "Ticker")
        pdf.cell(60, 7, "Market")
        pdf.cell(50, 7, "Weight", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for h in holdings:
            pdf.set_text_color(17, 17, 17)
            pdf.cell(80, 7, h["ticker"])
            pdf.cell(60, 7, h.get("market", "US"))
            pdf.cell(50, 7, f"{h['weight']:.1f}%", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Disclaimer page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 8, "Legal Disclaimer", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(60, 60, 64)
    pdf.multi_cell(0, 6,
        "AIPRS is an academic Final Year Project built for research and educational demonstration. "
        "It is not a licensed financial advisory service, investment platform, or brokerage, and is "
        "not regulated by any financial authority. All outputs in this report - including portfolio "
        "metrics, performance charts, asset allocations, and any recommendations - are produced for "
        "educational and demonstration purposes only. They do not constitute financial advice or "
        "regulated financial guidance. AIPRS and its developers accept no responsibility or liability "
        "whatsoever for any financial loss arising from actions taken based on anything contained in "
        "this report. Always consult a qualified and licensed financial advisor before making any "
        "investment decisions.\n\n"
        "AI-Powered Portfolio Recommendation System (AIPRS)  |  Academic Final Year Project  |  "
        "aiprs.support@gmail.com"
    )

    return bytes(pdf.output())
