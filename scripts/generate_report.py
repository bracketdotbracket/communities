"""
PDF Report Generator
====================
Generates a visual trend analysis report with matplotlib charts
and statistical summaries using reportlab.

Usage:
    python scripts/generate_report.py

Dependencies:
    matplotlib, seaborn, numpy, pandas, reportlab, psycopg2-binary
"""

import sys
import os
from datetime import datetime
from io import BytesIO

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import seaborn as sns
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import analysis_config
from trend_analysis import run_analysis


# ── Chart Theme ──────────────────────────────────────────────

COLORS = {
    "bg": "#0F172A",
    "surface": "#1E293B",
    "primary": "#8B5CF6",
    "secondary": "#EC4899",
    "tertiary": "#10B981",
    "quaternary": "#F59E0B",
    "text": "#E2E8F0",
    "muted": "#94A3B8",
    "grid": "#334155",
}


def apply_chart_theme():
    """Apply dark theme to matplotlib."""
    plt.rcParams.update({
        "figure.facecolor": COLORS["bg"],
        "axes.facecolor": COLORS["surface"],
        "axes.edgecolor": COLORS["grid"],
        "axes.labelcolor": COLORS["text"],
        "text.color": COLORS["text"],
        "xtick.color": COLORS["muted"],
        "ytick.color": COLORS["muted"],
        "grid.color": COLORS["grid"],
        "grid.alpha": 0.3,
        "font.family": "sans-serif",
        "font.size": 10,
    })


def chart_to_image(fig, width=6.5 * inch, height=3.5 * inch) -> Image:
    """Convert matplotlib figure to reportlab Image."""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", pad_inches=0.3)
    buf.seek(0)
    plt.close(fig)
    return Image(buf, width=width, height=height)


# ── Chart Generators ─────────────────────────────────────────

def create_engagement_chart(daily_data: list) -> Image:
    """Create engagement over time area chart."""
    apply_chart_theme()

    import pandas as pd
    df = pd.DataFrame(daily_data)
    df["date"] = pd.to_datetime(df["date"])

    fig, ax = plt.subplots(figsize=(10, 5))

    # Stacked area chart
    ax.fill_between(df["date"], 0, df["likes"], alpha=0.4, color=COLORS["secondary"], label="Likes")
    ax.fill_between(df["date"], df["likes"], df["likes"] + df["comments"],
                     alpha=0.4, color=COLORS["primary"], label="Comments")
    ax.fill_between(df["date"], df["likes"] + df["comments"],
                     df["likes"] + df["comments"] + df["reposts"],
                     alpha=0.4, color=COLORS["tertiary"], label="Reposts")

    # Moving average line
    if "total_ma" in df.columns:
        ax.plot(df["date"], df["total_ma"], color=COLORS["quaternary"],
                linewidth=2, linestyle="--", label="7-day average", zorder=5)

    ax.set_title("Engagement Over Time", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("")
    ax.set_ylabel("Daily Count")
    ax.legend(loc="upper left", framealpha=0.8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.xticks(rotation=45)
    ax.grid(True, alpha=0.2)

    return chart_to_image(fig)


def create_peak_hours_heatmap(peak_data: dict) -> Image:
    """Create activity heatmap by hour and day."""
    apply_chart_theme()

    if not peak_data:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.5, 0.5, "Insufficient data for heatmap",
                ha="center", va="center", fontsize=14, color=COLORS["muted"])
        ax.set_facecolor(COLORS["surface"])
        return chart_to_image(fig)

    import pandas as pd
    df = pd.DataFrame(peak_data)

    fig, ax = plt.subplots(figsize=(10, 4))
    sns.heatmap(
        df, ax=ax, cmap="magma", linewidths=0.5,
        linecolor=COLORS["grid"], cbar_kws={"label": "Activity"},
        xticklabels=[f"{h}:00" for h in range(24)],
    )
    ax.set_title("Peak Activity Hours", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("")
    plt.xticks(rotation=45, fontsize=8)

    return chart_to_image(fig)


def create_forecast_chart(daily_data: list, forecast: dict) -> Image:
    """Create growth forecast chart."""
    apply_chart_theme()

    import pandas as pd
    df = pd.DataFrame(daily_data)
    df["date"] = pd.to_datetime(df["date"])

    fig, ax = plt.subplots(figsize=(10, 5))

    # Historical data
    ax.plot(df["date"], df["total"], color=COLORS["primary"],
            linewidth=2, label="Actual", zorder=3)
    ax.fill_between(df["date"], 0, df["total"], alpha=0.15, color=COLORS["primary"])

    # Forecast
    if forecast.get("forecast"):
        last_date = df["date"].iloc[-1]
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1),
                                        periods=len(forecast["forecast"]), freq="D")
        forecast_values = forecast["forecast"]
        ax.plot(forecast_dates, forecast_values, color=COLORS["quaternary"],
                linewidth=2, linestyle="--", label="Forecast", zorder=3)
        ax.fill_between(forecast_dates, 0, forecast_values,
                         alpha=0.1, color=COLORS["quaternary"])

    trend_emoji = {"growing": "📈", "declining": "📉", "stable": "➡️"}.get(
        forecast.get("trend", ""), "❓"
    )
    ax.set_title(f"Growth Forecast {trend_emoji} ({forecast.get('trend', 'N/A').title()})",
                  fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("")
    ax.set_ylabel("Total Engagement")
    ax.legend(loc="upper left", framealpha=0.8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.grid(True, alpha=0.2)

    return chart_to_image(fig)


def create_health_bar_chart(health_data: list) -> Image:
    """Create community health score bar chart."""
    apply_chart_theme()

    fig, ax = plt.subplots(figsize=(10, max(3, len(health_data) * 0.6)))

    if not health_data:
        ax.text(0.5, 0.5, "No communities to analyze",
                ha="center", va="center", fontsize=14, color=COLORS["muted"])
        return chart_to_image(fig)

    names = [h["name"][:20] for h in health_data[:10]]
    scores = [h["health_score"] for h in health_data[:10]]

    colors = []
    for s in scores:
        if s >= 70:
            colors.append(COLORS["tertiary"])
        elif s >= 40:
            colors.append(COLORS["quaternary"])
        else:
            colors.append(COLORS["secondary"])

    bars = ax.barh(names, scores, color=colors, edgecolor=COLORS["grid"], height=0.6)
    ax.set_xlim(0, 100)
    ax.set_title("Community Health Scores", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Health Score (0-100)")
    ax.invert_yaxis()
    ax.grid(True, axis="x", alpha=0.2)

    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{score}", va="center", fontsize=10, color=COLORS["text"])

    return chart_to_image(fig)


# ── PDF Builder ──────────────────────────────────────────────

def build_pdf(results: dict, output_path: str):
    """Build the complete PDF report."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=HexColor(COLORS["primary"]),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=HexColor(COLORS["muted"]),
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=16,
        textColor=HexColor(COLORS["primary"]),
        spaceBefore=20,
        spaceAfter=10,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=11,
        textColor=HexColor("#333333"),
        spaceAfter=8,
    )

    story = []

    # ── Title Page ──
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("📊 Trend Analysis Report", title_style))
    story.append(Paragraph(
        f"Generated on {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}",
        subtitle_style,
    ))
    story.append(Spacer(1, 0.5 * inch))

    # Summary stats
    summary = results.get("summary", {})
    summary_data = [
        ["Metric", "Value"],
        ["Total Engagement (30d)", str(summary.get("total_engagement", 0))],
        ["Avg Daily Engagement", str(summary.get("avg_daily_engagement", 0))],
        ["Growth Trend", summary.get("trend", "N/A").title()],
        ["Communities Analyzed", str(summary.get("num_communities", 0))],
        ["R² Confidence", str(results.get("forecast", {}).get("r_squared", "N/A"))],
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(COLORS["primary"])),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor(COLORS["grid"])),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#F8FAFC"), HexColor("#FFFFFF")]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(PageBreak())

    # ── Engagement Trends ──
    story.append(Paragraph("📈 Engagement Trends", heading_style))
    story.append(Paragraph(
        "Daily engagement metrics over the past 30 days with 7-day moving average.",
        body_style,
    ))
    daily_data = results.get("daily_engagement", [])
    story.append(create_engagement_chart(daily_data))
    story.append(Spacer(1, 0.3 * inch))

    # ── Growth Forecast ──
    story.append(Paragraph("🔮 Growth Forecast", heading_style))
    forecast = results.get("forecast", {})
    trend = forecast.get("trend", "unknown")
    story.append(Paragraph(
        f"Based on polynomial regression analysis, the platform's engagement trend is "
        f"<b>{trend}</b> with an R² confidence of {forecast.get('r_squared', 'N/A')}.",
        body_style,
    ))
    story.append(create_forecast_chart(daily_data, forecast))
    story.append(PageBreak())

    # ── Peak Activity ──
    story.append(Paragraph("⏰ Peak Activity Hours", heading_style))
    story.append(Paragraph(
        "Heatmap showing when users are most active across days and hours.",
        body_style,
    ))
    story.append(create_peak_hours_heatmap(results.get("peak_hours", {})))
    story.append(Spacer(1, 0.3 * inch))

    # ── Community Health ──
    story.append(Paragraph("🏥 Community Health Scores", heading_style))
    story.append(Paragraph(
        "Health scores are computed from engagement ratios, post frequency, and member counts. "
        "Green (70+) = healthy, Yellow (40-69) = moderate, Red (&lt;40) = needs attention.",
        body_style,
    ))
    story.append(create_health_bar_chart(results.get("community_health", [])))

    # Build
    doc.build(story)
    print(f"✅ PDF report generated: {output_path}")


def main():
    """Run analysis and generate PDF report."""
    print("🚀 Starting report generation...\n")

    # Run analysis
    results = run_analysis()

    # Generate PDF
    os.makedirs(analysis_config.output_dir, exist_ok=True)
    output_path = os.path.join(analysis_config.output_dir, analysis_config.report_filename)
    build_pdf(results, output_path)

    print(f"\n🎉 Done! Report saved to: {output_path}")


if __name__ == "__main__":
    main()
