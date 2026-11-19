"""
S.H.I.E.L.D. Dashboard — Design Reference PDF Generator
Generates a multi-page PDF with the dashboard design mockup, layout grid,
component specifications, and color palette for development reference.
"""

import os
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PDF = SCRIPT_DIR.parent / "outputs" / "SHIELD_Dashboard_Design.pdf"
MOCKUP_IMG = Path(
    r"C:\Users\lalit\.gemini\antigravity-ide\brain"
    r"\c62e3ae7-1261-4831-9769-4212572e9ecc"
    r"\dashboard_design_mockup_1782735519149.png"
)

# ---------------------------------------------------------------------------
# Design-system colours
# ---------------------------------------------------------------------------
BG_DARK    = HexColor("#0a0b14")
BG_CARD    = HexColor("#0f1729")
BORDER     = HexColor("#1e293b")
TEXT_WHITE  = HexColor("#f1f5f9")
TEXT_MUTED  = HexColor("#94a3b8")
ACCENT_BLUE   = HexColor("#3b82f6")
ACCENT_ORANGE = HexColor("#f97316")
ACCENT_RED    = HexColor("#ef4444")
ACCENT_GREEN  = HexColor("#10b981")
ACCENT_YELLOW = HexColor("#eab308")
ACCENT_PURPLE = HexColor("#a855f7")
ACCENT_ROSE   = HexColor("#f43f5e")

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 20 * mm


# ---------------------------------------------------------------------------
# Helper drawing functions
# ---------------------------------------------------------------------------
def draw_dark_bg(c, w=PAGE_W, h=PAGE_H):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, w, h, fill=1, stroke=0)


def draw_rounded_card(c, x, y, w, h, fill=BG_CARD, border_col=BORDER, r=4*mm):
    c.saveState()
    c.setStrokeColor(border_col)
    c.setLineWidth(0.5)
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1)
    c.restoreState()


def draw_text(c, x, y, text, size=10, color=TEXT_WHITE, font="Helvetica"):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawString(x, y, text)


def draw_text_centered(c, x, y, text, size=10, color=TEXT_WHITE, font="Helvetica"):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(x, y, text)


def draw_color_swatch(c, x, y, color, label, hex_val):
    c.setFillColor(color)
    c.roundRect(x, y, 18*mm, 10*mm, 2*mm, fill=1, stroke=0)
    draw_text(c, x, y - 5*mm, label, size=7, color=TEXT_WHITE, font="Helvetica-Bold")
    draw_text(c, x, y - 9*mm, hex_val, size=6, color=TEXT_MUTED)


# ===========================================================================
# PAGE 1 — Cover + Mockup
# ===========================================================================
def page_cover(c):
    draw_dark_bg(c)

    # Title block
    draw_text_centered(c, PAGE_W/2, PAGE_H - 30*mm,
                       "S.H.I.E.L.D.", size=36, color=ACCENT_ORANGE,
                       font="Helvetica-Bold")
    draw_text_centered(c, PAGE_W/2, PAGE_H - 40*mm,
                       "Solar Hazard Interception & Extra-orbital Logistics Dashboard",
                       size=12, color=TEXT_MUTED)
    draw_text_centered(c, PAGE_W/2, PAGE_H - 50*mm,
                       "Dashboard Design Reference  —  Team Suryastra",
                       size=10, color=TEXT_MUTED)

    # Separator line
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.line(MARGIN, PAGE_H - 55*mm, PAGE_W - MARGIN, PAGE_H - 55*mm)

    # Mockup image
    if MOCKUP_IMG.exists():
        img = Image.open(MOCKUP_IMG)
        iw, ih = img.size
        avail_w = PAGE_W - 2 * MARGIN
        avail_h = PAGE_H - 75*mm
        scale = min(avail_w / iw, avail_h / ih)
        draw_w = iw * scale
        draw_h = ih * scale
        x = (PAGE_W - draw_w) / 2
        y = 15*mm
        # Card behind image
        draw_rounded_card(c, x - 3*mm, y - 3*mm, draw_w + 6*mm, draw_h + 6*mm,
                          fill=HexColor("#0d1117"), border_col=ACCENT_BLUE, r=3*mm)
        c.drawImage(ImageReader(MOCKUP_IMG), x, y, draw_w, draw_h,
                    preserveAspectRatio=True, mask='auto')
    else:
        draw_text_centered(c, PAGE_W/2, PAGE_H/2,
                           "(Mockup image not found)", size=14, color=ACCENT_RED)

    # Footer
    draw_text_centered(c, PAGE_W/2, 8*mm,
                       "Bharatiya Antariksh Hackathon 2026  ·  Challenge #15",
                       size=7, color=TEXT_MUTED)


# ===========================================================================
# PAGE 2 — Layout Grid Wireframe
# ===========================================================================
def page_layout_grid(c):
    draw_dark_bg(c)

    draw_text(c, MARGIN, PAGE_H - 20*mm, "DASHBOARD LAYOUT GRID",
              size=18, color=ACCENT_ORANGE, font="Helvetica-Bold")
    draw_text(c, MARGIN, PAGE_H - 28*mm,
              "Responsive CSS Grid layout — maps directly to the wireframe sketch",
              size=9, color=TEXT_MUTED)

    base_y = PAGE_H - 38*mm
    lx = MARGIN
    full_w = PAGE_W - 2*MARGIN
    half_w = (full_w - 5*mm) / 2
    row_gap = 4*mm

    # Row 1: Header
    rh = 12*mm
    draw_rounded_card(c, lx, base_y - rh, full_w, rh, border_col=ACCENT_GREEN)
    draw_text_centered(c, PAGE_W/2, base_y - rh + 4*mm,
                       "HEADER  —  S.H.I.E.L.D. Logo  |  Event Selector  |  System Status",
                       size=8, color=ACCENT_GREEN, font="Helvetica-Bold")
    base_y -= rh + row_gap

    # Row 2: KPI Cards
    rh = 14*mm
    kpi_w = (full_w - 3*5*mm) / 4
    kpi_colors = [ACCENT_BLUE, ACCENT_ORANGE, ACCENT_YELLOW, ACCENT_PURPLE]
    kpi_labels = ["Algorithm\nStage", "Detection\nSpeed", "Flare\nProbability", "Observed\nClass"]
    for i in range(4):
        x = lx + i * (kpi_w + 5*mm)
        draw_rounded_card(c, x, base_y - rh, kpi_w, rh, border_col=kpi_colors[i])
        draw_text_centered(c, x + kpi_w/2, base_y - rh + 5*mm,
                           kpi_labels[i].split('\n')[0], size=7,
                           color=kpi_colors[i], font="Helvetica-Bold")
    base_y -= rh + row_gap

    # Row 3: Mixed Graph (full width)
    rh = 35*mm
    draw_rounded_card(c, lx, base_y - rh, full_w, rh, border_col=ACCENT_BLUE)
    draw_text_centered(c, PAGE_W/2, base_y - rh/2 + 3*mm,
                       "SoLEXS + HEL1OS MIXED GRAPH", size=11,
                       color=ACCENT_BLUE, font="Helvetica-Bold")
    draw_text_centered(c, PAGE_W/2, base_y - rh/2 - 5*mm,
                       "Full-width hero chart  ·  Dual-axis  ·  Forecast / Nowcast markers",
                       size=7, color=TEXT_MUTED)
    base_y -= rh + row_gap

    # Row 4: SoLEXS + HEL1OS standalone
    rh = 28*mm
    draw_rounded_card(c, lx, base_y - rh, half_w, rh, border_col=ACCENT_BLUE)
    draw_text_centered(c, lx + half_w/2, base_y - rh/2,
                       "SoLEXS GRAPH", size=9, color=ACCENT_BLUE, font="Helvetica-Bold")

    draw_rounded_card(c, lx + half_w + 5*mm, base_y - rh, half_w, rh, border_col=ACCENT_RED)
    draw_text_centered(c, lx + half_w + 5*mm + half_w/2, base_y - rh/2,
                       "HEL1OS GRAPH", size=9, color=ACCENT_RED, font="Helvetica-Bold")
    base_y -= rh + row_gap

    # Row 5: Flux sidebar + SUIT images + VELC + Forecast
    rh = 40*mm
    sidebar_w = 28*mm
    draw_rounded_card(c, lx, base_y - rh, sidebar_w, rh, border_col=ACCENT_GREEN)
    draw_text_centered(c, lx + sidebar_w/2, base_y - 8*mm,
                       "FLUX &", size=7, color=ACCENT_GREEN, font="Helvetica-Bold")
    draw_text_centered(c, lx + sidebar_w/2, base_y - 13*mm,
                       "TIME", size=7, color=ACCENT_GREEN, font="Helvetica-Bold")
    draw_text_centered(c, lx + sidebar_w/2, base_y - 20*mm,
                       "UTC / IST", size=6, color=TEXT_MUTED)

    # 3 SUIT images
    suit_area_x = lx + sidebar_w + 4*mm
    remaining_w = full_w - sidebar_w - 4*mm
    suit_w = (remaining_w * 0.6 - 2*4*mm) / 3
    for i in range(3):
        sx = suit_area_x + i * (suit_w + 4*mm)
        draw_rounded_card(c, sx, base_y - rh, suit_w, rh, border_col=ACCENT_ORANGE)
        draw_text_centered(c, sx + suit_w/2, base_y - rh/2 + 3*mm,
                           f"SUIT", size=8, color=ACCENT_ORANGE, font="Helvetica-Bold")
        draw_text_centered(c, sx + suit_w/2, base_y - rh/2 - 4*mm,
                           f"Sun Image {i+1}", size=6, color=TEXT_MUTED)

    # VELC + Forecast
    right_x = suit_area_x + 3 * (suit_w + 4*mm)
    right_w = remaining_w * 0.4
    rh_half = (rh - 4*mm) / 2

    draw_rounded_card(c, right_x, base_y - rh_half, right_w, rh_half,
                      border_col=ACCENT_ROSE)
    draw_text_centered(c, right_x + right_w/2, base_y - rh_half/2,
                       "VELC DATA", size=8, color=ACCENT_ROSE, font="Helvetica-Bold")

    draw_rounded_card(c, right_x, base_y - rh, right_w, rh_half,
                      border_col=ACCENT_YELLOW)
    draw_text_centered(c, right_x + right_w/2, base_y - rh + rh_half/2,
                       "FORECAST & IMPACT", size=7, color=ACCENT_YELLOW, font="Helvetica-Bold")

    # Footer annotation
    draw_text(c, MARGIN, 10*mm,
              "Grid: CSS Grid with named areas  ·  Responsive breakpoints at 768px / 1280px  ·  Glassmorphism cards",
              size=7, color=TEXT_MUTED)


# ===========================================================================
# PAGE 3 — Component Specs
# ===========================================================================
def page_components(c):
    draw_dark_bg(c)

    draw_text(c, MARGIN, PAGE_H - 20*mm, "COMPONENT SPECIFICATIONS",
              size=18, color=ACCENT_ORANGE, font="Helvetica-Bold")

    components = [
        ("FlareChart.tsx", "Combined SoLEXS + HEL1OS", ACCENT_BLUE,
         "Dual-axis Plotly chart • Blue SoLEXS + Red HEL1OS • Forecast/Nowcast vertical markers • Log scale Y-axes"),
        ("SolexsChart.tsx  [NEW]", "Standalone SoLEXS", ACCENT_BLUE,
         "SoLEXS flux + derivative overlay • Slope-steepening signal • Stage 3 forecast marker • Fill-to-zero area"),
        ("Hel1osChart.tsx  [NEW]", "Standalone HEL1OS", ACCENT_RED,
         "HEL1OS flux + rolling baseline band • 3σ threshold shading • Stage 4 nowcast spike highlight"),
        ("FluxSidebar.tsx  [NEW]", "Flux & Time Panel", ACCENT_GREEN,
         "Current flux values • UTC/IST time toggle • 4-stage pipeline indicator • Vertical animated state bar"),
        ("SuitImageCard.tsx  [NEW]", "SUIT Sun Images ×3", ACCENT_ORANGE,
         "Full-disk UV image cards • Active-region overlay • Timestamp + filter metadata • Animated glow border"),
        ("VelcDataCard.tsx  [NEW]", "VELC / Spectral Data", ACCENT_ROSE,
         "Plasma temperature gauge • Spectral index • Hardness ratio • Peak flare timestamp"),
        ("ForecastPanel.tsx  [NEW]", "Forecast & Impact", ACCENT_YELLOW,
         "6h/24h Poisson probability bars • Activity level badge • Impact domains grid • Safety advisories"),
    ]

    y = PAGE_H - 38*mm
    card_h = 20*mm
    for name, subtitle, color, desc in components:
        draw_rounded_card(c, MARGIN, y - card_h, PAGE_W - 2*MARGIN, card_h, border_col=color)
        # Color accent bar on left
        c.setFillColor(color)
        c.roundRect(MARGIN, y - card_h, 3*mm, card_h, 1*mm, fill=1, stroke=0)

        draw_text(c, MARGIN + 8*mm, y - 6*mm, name, size=10, color=color,
                  font="Helvetica-Bold")
        draw_text(c, MARGIN + 8*mm, y - 12*mm, subtitle, size=8, color=TEXT_WHITE)
        draw_text(c, MARGIN + 8*mm, y - 17*mm, desc, size=7, color=TEXT_MUTED)

        y -= card_h + 3*mm


# ===========================================================================
# PAGE 4 — Color Palette & Typography
# ===========================================================================
def page_design_system(c):
    draw_dark_bg(c)

    draw_text(c, MARGIN, PAGE_H - 20*mm, "DESIGN SYSTEM",
              size=18, color=ACCENT_ORANGE, font="Helvetica-Bold")

    # --- Color Palette ---
    draw_text(c, MARGIN, PAGE_H - 35*mm, "COLOR PALETTE",
              size=12, color=TEXT_WHITE, font="Helvetica-Bold")

    colors = [
        (BG_DARK, "Background", "#0A0B14"),
        (BG_CARD, "Card BG", "#0F1729"),
        (BORDER, "Borders", "#1E293B"),
        (ACCENT_BLUE, "SoLEXS Blue", "#3B82F6"),
        (ACCENT_RED, "HEL1OS Red", "#EF4444"),
        (ACCENT_ORANGE, "Warning", "#F97316"),
        (ACCENT_GREEN, "Success", "#10B981"),
        (ACCENT_YELLOW, "Caution", "#EAB308"),
        (ACCENT_PURPLE, "Severity", "#A855F7"),
        (ACCENT_ROSE, "Spectral", "#F43F5E"),
    ]

    x = MARGIN
    y = PAGE_H - 50*mm
    for i, (col, label, hex_val) in enumerate(colors):
        draw_color_swatch(c, x, y, col, label, hex_val)
        x += 25*mm
        if (i + 1) % 5 == 0:
            x = MARGIN
            y -= 20*mm

    # --- Typography ---
    ty = y - 15*mm
    draw_text(c, MARGIN, ty, "TYPOGRAPHY",
              size=12, color=TEXT_WHITE, font="Helvetica-Bold")
    ty -= 12*mm

    fonts = [
        ("Inter / Geist Sans", "Primary UI", "Headers, labels, body text"),
        ("Geist Mono", "Data / Code", "Flux values, timestamps, alert logs"),
    ]
    for fname, role, usage in fonts:
        draw_text(c, MARGIN + 5*mm, ty, fname, size=11, color=ACCENT_BLUE, font="Helvetica-Bold")
        draw_text(c, MARGIN + 60*mm, ty, role, size=9, color=TEXT_WHITE)
        draw_text(c, MARGIN + 100*mm, ty, usage, size=8, color=TEXT_MUTED)
        ty -= 8*mm

    # --- Effects ---
    ey = ty - 12*mm
    draw_text(c, MARGIN, ey, "VISUAL EFFECTS",
              size=12, color=TEXT_WHITE, font="Helvetica-Bold")
    ey -= 12*mm

    effects = [
        ("Glassmorphism", "Semi-transparent cards with backdrop-blur-md, subtle 1px borders"),
        ("Gradient Glow", "KPI cards use bg-gradient-to-br with accent color → transparent"),
        ("Pulse Animation", "System status dot + alert indicators use animate-ping"),
        ("Sun Glow", "SUIT image cards have a pulsing radial orange glow behind the sun disk"),
        ("Hover Lift", "Cards translate-y -1px on hover with 300ms transition"),
        ("Stage Colors", "S1=Emerald  S2=Yellow  S3=Orange  S4=Red (pipeline progression)"),
    ]
    for name, desc in effects:
        draw_text(c, MARGIN + 5*mm, ey, f"▸ {name}", size=9, color=ACCENT_ORANGE, font="Helvetica-Bold")
        draw_text(c, MARGIN + 45*mm, ey, desc, size=8, color=TEXT_MUTED)
        ey -= 8*mm

    # --- Data Source ---
    dy = ey - 12*mm
    draw_text(c, MARGIN, dy, "DATA SOURCE",
              size=12, color=TEXT_WHITE, font="Helvetica-Bold")
    dy -= 10*mm
    data_lines = [
        "All data from ISRO PRADAN portal — pradan.issdc.gov.in/al1",
        "Dashboard reads:  dashboard/public/shield_data.json  (generated by python dashboard_export.py)",
        "Contains: 6 validated flare events, real SoLEXS/HEL1OS light curves, stage transitions, alert logs",
        "Instruments: SoLEXS (Soft X-ray) + HEL1OS (Hard X-ray) + SUIT (UV) + VELC (Coronagraph)",
    ]
    for line in data_lines:
        draw_text(c, MARGIN + 5*mm, dy, f"•  {line}", size=8, color=TEXT_MUTED)
        dy -= 7*mm


# ===========================================================================
# PAGE 5 — Tech Stack & Build
# ===========================================================================
def page_tech_stack(c):
    draw_dark_bg(c)

    draw_text(c, MARGIN, PAGE_H - 20*mm, "TECHNOLOGY STACK & BUILD",
              size=18, color=ACCENT_ORANGE, font="Helvetica-Bold")

    y = PAGE_H - 40*mm
    sections = [
        ("FRAMEWORK", [
            ("Next.js 16", "React 19 SSR framework with App Router"),
            ("TypeScript 5", "Type-safe component development"),
            ("Tailwind CSS 4", "Utility-first styling with @theme inline"),
        ]),
        ("CHARTING", [
            ("Plotly.js 3", "Scientific-grade interactive charts"),
            ("react-plotly.js 4", "React wrapper with SSR-disabled dynamic import"),
        ]),
        ("ICONS & UI", [
            ("Lucide React", "Clean, consistent icon set (Activity, ShieldAlert, Zap, Sun, Server)"),
            ("Google Fonts", "Inter for UI, Geist Mono for data"),
        ]),
        ("BACKEND PIPELINE", [
            ("Python 3.14", "Core S.H.I.E.L.D. engine"),
            ("dashboard_export.py", "Runs real pipeline → outputs shield_data.json"),
            ("6 Flare Events", "MAY2024_X87, FEB2024_X63, JAN2025_X18, and more"),
            ("XGBoost 3.3", "3 trained ML models saved in outputs/models/"),
        ]),
        ("BUILD & RUN", [
            ("npm run dev", "Start dev server at localhost:3000"),
            ("npm run build", "Production build"),
            ("python main.py --dashboard", "Regenerate data from pipeline"),
        ]),
    ]

    for section_title, items in sections:
        draw_text(c, MARGIN, y, section_title, size=11, color=ACCENT_BLUE, font="Helvetica-Bold")
        y -= 3*mm
        c.setStrokeColor(ACCENT_BLUE)
        c.setLineWidth(0.3)
        c.line(MARGIN, y, MARGIN + 60*mm, y)
        y -= 6*mm
        for name, desc in items:
            draw_text(c, MARGIN + 8*mm, y, name, size=9, color=TEXT_WHITE, font="Helvetica-Bold")
            draw_text(c, MARGIN + 55*mm, y, desc, size=8, color=TEXT_MUTED)
            y -= 7*mm
        y -= 5*mm

    # Footer
    draw_rounded_card(c, MARGIN, 12*mm, PAGE_W - 2*MARGIN, 16*mm, border_col=ACCENT_ORANGE)
    draw_text_centered(c, PAGE_W/2, 22*mm,
                       "S.H.I.E.L.D.  ·  Built for the Sun. Built for India.",
                       size=10, color=ACCENT_ORANGE, font="Helvetica-Bold")
    draw_text_centered(c, PAGE_W/2, 15*mm,
                       "Team Suryastra  ·  Bharatiya Antariksh Hackathon 2026  ·  Challenge #15",
                       size=8, color=TEXT_MUTED)


# ===========================================================================
# PAGE 6 — Click-to-Detail Interaction Map
# ===========================================================================
def page_interactions(c):
    draw_dark_bg(c)

    draw_text(c, MARGIN, PAGE_H - 20*mm, "CLICK-TO-DETAIL INTERACTIONS",
              size=18, color=ACCENT_ORANGE, font="Helvetica-Bold")
    draw_text(c, MARGIN, PAGE_H - 28*mm,
              "Every section on the dashboard is clickable — opening a slide-in detail panel with deeper data",
              size=9, color=TEXT_MUTED)

    y = PAGE_H - 42*mm
    full_w = PAGE_W - 2*MARGIN

    interactions = [
        ("KPI: Algorithm State", "→  Stage Detail Panel", ACCENT_BLUE,
         "4-stage pipeline progression with timestamps, S1–S4 visual timeline, detection summary (forecast/nowcast fired, provisional vs true class)"),
        ("KPI: Detection Speed", "→  Detection Speed Analysis", ACCENT_ORANGE,
         "Stage 3→4 gap measurement (onset to confirmed), stage timestamps, cross-event comparison, Neupert Effect explained honestly (concurrent rise, not advance warning)"),
        ("KPI: Flare Probability", "→  Forecast Deep Dive", ACCENT_YELLOW,
         "6h/24h probability gauges, activity level badge, Poisson model formula (λ, P equations), model transparency notes"),
        ("KPI: Observed Class", "→  Classification Detail", ACCENT_PURPLE,
         "GOES X-ray classification scale table (A/B/C/M/X), active region info, full event catalog comparison"),
        ("Flux Chart", "→  Full Analysis View", ACCENT_BLUE,
         "Enlarged 500px chart, time series statistics (data points, window duration, SoLEXS/HEL1OS peaks), stage markers table, instrument descriptions"),
        ("Alert Log", "→  Complete Alert Timeline", HexColor("#94a3b8"),
         "Expanded alert cards with confidence bars, provisional class, trigger source, plus summary table with all alert fields"),
        ("Spectral Diagnostics", "→  Spectral Deep Dive", ACCENT_ROSE,
         "Key measurements with explanations: plasma temperature, spectral index (γ), hardness ratio — what each means physically"),
        ("Impact Domain Cards", "→  Individual Threat Detail", ACCENT_ORANGE,
         "Per-domain view: threat level badge, expected impact, recommended action, assessment basis, cross-domain comparison table"),
    ]

    card_h = 16*mm
    for source, target, color, desc in interactions:
        draw_rounded_card(c, MARGIN, y - card_h, full_w, card_h, border_col=color)

        # Color accent dot
        c.setFillColor(color)
        c.circle(MARGIN + 5*mm, y - card_h/2, 2.5*mm, fill=1, stroke=0)

        draw_text(c, MARGIN + 12*mm, y - 5*mm, source, size=9,
                  color=TEXT_WHITE, font="Helvetica-Bold")
        draw_text(c, MARGIN + 65*mm, y - 5*mm, target, size=9,
                  color=color, font="Helvetica-Bold")
        draw_text(c, MARGIN + 12*mm, y - 11*mm, desc, size=6.5, color=TEXT_MUTED)

        y -= card_h + 2.5*mm

    # UX notes
    y -= 4*mm
    draw_rounded_card(c, MARGIN, y - 18*mm, full_w, 18*mm,
                      fill=HexColor("#0d1117"), border_col=ACCENT_GREEN)
    draw_text(c, MARGIN + 6*mm, y - 5*mm, "UX INTERACTIONS",
              size=8, color=ACCENT_GREEN, font="Helvetica-Bold")
    notes = [
        "▸ Slide-in panel from right edge with glassmorphism backdrop (backdrop-blur-sm + 60% black overlay)",
        "▸ Close via × button, Escape key, or backdrop click  ·  Body scroll-locked while panel is open",
        "▸ Hover lift on all cards (translateY -2px, 250ms ease)  ·  Chevron icon hints at interactivity",
    ]
    for i, note in enumerate(notes):
        draw_text(c, MARGIN + 6*mm, y - 10*mm - i*4*mm, note,
                  size=6.5, color=TEXT_MUTED)


# ===========================================================================
# PAGE 7 — Detail Panel Content Breakdown
# ===========================================================================
def page_detail_panels(c):
    draw_dark_bg(c)

    draw_text(c, MARGIN, PAGE_H - 20*mm, "DETAIL PANEL CONTENT",
              size=18, color=ACCENT_ORANGE, font="Helvetica-Bold")
    draw_text(c, MARGIN, PAGE_H - 28*mm,
              "What each slide-in panel displays when a user clicks on a dashboard section",
              size=9, color=TEXT_MUTED)

    half_w = (PAGE_W - 2*MARGIN - 8*mm) / 2
    col1_x = MARGIN
    col2_x = MARGIN + half_w + 8*mm

    panels = [
        # Column 1
        [
            ("Stage Detail", ACCENT_BLUE, [
                "Current state: large S1–S4 badge + description",
                "4-stage timeline: each stage with status, time, description",
                "Color-coded: reached stages highlighted, unreached dimmed",
                "Detection summary: forecast/nowcast status, provisional class",
            ]),
            ("Detection Speed Analysis", ACCENT_ORANGE, [
                "Onset-to-confirmed gap, in minutes and seconds",
                "Honest note: flares are impulsive, not a warning window",
                "Cross-event comparison table (all 6 events)",
                "Mean detection speed across all events",
                "Neupert Effect explained as cross-validation, not lead time",
            ]),
            ("Forecast Deep Dive", ACCENT_YELLOW, [
                "6h and 24h probability as large gauge cards",
                "Activity level badge (LOW/WATCH/ELEVATED/HIGH)",
                "Peak forecast timestamp",
                "Poisson model formula (λ, P equations)",
                "Transparency note: 'situational awareness, not skillful'",
            ]),
            ("Classification Detail", ACCENT_PURPLE, [
                "Flare parameters grid (class, tier, AR, provisional)",
                "GOES X-ray classification scale reference table",
                "Full event catalog table for comparison",
            ]),
        ],
        # Column 2
        [
            ("Full Chart Analysis", ACCENT_BLUE, [
                "Enlarged Plotly chart (500px height)",
                "Time series stats: data points, window duration",
                "SoLEXS/HEL1OS peak values in scientific notation",
                "Stage markers table with trigger sources",
                "Instrument descriptions (SoLEXS + HEL1OS)",
            ]),
            ("Alert Timeline", HexColor("#94a3b8"), [
                "Expanded alert cards with stage-colored borders",
                "Confidence progress bars (visual percentage)",
                "Provisional class + trigger source per alert",
                "Summary table with all alert fields",
            ]),
            ("Spectral Deep Dive", ACCENT_ROSE, [
                "Key measurements grid (temp, γ, hardness, time)",
                "Per-measurement explanation cards:",
                "  - Plasma Temperature: reconnection significance",
                "  - Spectral Index: particle acceleration efficiency",
                "  - Hardness Ratio: SEP event correlation",
                "Flare statistics and selection methodology",
            ]),
            ("Impact Domain Detail", ACCENT_ORANGE, [
                "Threat level badge (large, color-coded)",
                "Expected impact in highlighted card",
                "Recommended action in green card",
                "Assessment basis and data source notes",
                "Cross-domain comparison table (all 6 domains)",
            ]),
        ],
    ]

    for col_idx, col_panels in enumerate(panels):
        x = col1_x if col_idx == 0 else col2_x
        y = PAGE_H - 40*mm

        for panel_name, color, items in col_panels:
            panel_h = 8*mm + len(items) * 4.5*mm
            draw_rounded_card(c, x, y - panel_h, half_w, panel_h, border_col=color)

            # Title
            draw_text(c, x + 5*mm, y - 6*mm, panel_name, size=8,
                      color=color, font="Helvetica-Bold")

            # Items
            for i, item in enumerate(items):
                draw_text(c, x + 5*mm, y - 10*mm - i*4.5*mm,
                          f"• {item}", size=6, color=TEXT_MUTED)

            y -= panel_h + 3*mm

    # Footer
    draw_text_centered(c, PAGE_W/2, 8*mm,
                       "DetailModal.tsx  ·  Reusable sub-components: DetailSection, DetailStat, DetailTable",
                       size=7, color=TEXT_MUTED)


# ===========================================================================
# PAGE 8 — ML Model Results & Validation
# ===========================================================================
def page_ml_results(c):
    draw_dark_bg(c)

    draw_text(c, MARGIN, PAGE_H - 20*mm, "ML MODEL RESULTS & VALIDATION",
              size=18, color=ACCENT_ORANGE, font="Helvetica-Bold")
    draw_text(c, MARGIN, PAGE_H - 28*mm,
              "Trained on 877 days of real Aditya-L1 SoLEXS + HEL1OS data  |  Chronological train/test split (no leakage)",
              size=9, color=TEXT_MUTED)

    # Scan summary banner
    draw_rounded_card(c, MARGIN, PAGE_H - 50*mm, PAGE_W - 2*MARGIN, 16*mm,
                      fill=HexColor("#0d1117"), border_col=ACCENT_GREEN)
    stats = [
        ("877", "Days Scanned"),
        ("175", "Flares Detected"),
        ("0.328", "False Alarms/Day"),
        ("Feb 2024", "Archive Start"),
        ("Jun 2026", "Archive End"),
        ("6 Workers", "Parallel Scan"),
    ]
    sw = (PAGE_W - 2*MARGIN) / len(stats)
    for i, (val, label) in enumerate(stats):
        sx = MARGIN + i * sw + sw/2
        draw_text_centered(c, sx, PAGE_H - 39*mm, val, size=11,
                           color=ACCENT_GREEN, font="Helvetica-Bold")
        draw_text_centered(c, sx, PAGE_H - 45*mm, label, size=6, color=TEXT_MUTED)

    y = PAGE_H - 58*mm
    full_w = PAGE_W - 2*MARGIN
    third_w = (full_w - 2*6*mm) / 3

    models = [
        ("MODEL 1 — SoLEXS Flare Detector", ACCENT_BLUE, [
            ("AUC",        "0.935"),
            ("Recall C",   "88.3%"),
            ("Recall M",   "81.4%"),
            ("Recall X",   "85.7%"),
            ("Precision",  "26.5%"),
            ("Train wins", "232,724"),
            ("Top feature","peak_over_base"),
        ], "6-min sliding windows over SoLEXS flux. Labels from GOES catalog.\nXGBoost 300 trees. Catches 85%+ of X-class flares."),
        ("MODEL 2 — Dual Instrument (SoLEXS+HEL1OS)", ACCENT_RED, [
            ("AUC",        "0.854"),
            ("Precision",  "98.6%"),
            ("Recall",     "83.3%"),
            ("Train",      "214 events"),
            ("Test",       "93 events"),
            ("Top feature","n_hls_detect"),
            ("FA rate",    "~1.4%"),
        ], "Physics features: HEL1OS sigma, hardness ratio, Neupert flag.\nNearly zero false alarms — precision 98.6%."),
        ("MODEL 3 — 24h Flare Forecaster", ACCENT_YELLOW, [
            ("AUC",          "0.754"),
            ("vs Climatology","+31.9%"),
            ("vs Poisson",   "+67.0%"),
            ("Brier ML",     "0.196"),
            ("Train",        "4,908 pts"),
            ("Top feature",  "nM_48h"),
            ("Horizon",      "24h"),
        ], "Catalog activity features: M+ count in 6/12/24/48h windows.\nML beats Poisson baseline by +67% skill score."),
    ]

    for col, (title, color, metrics, note) in enumerate(models):
        x = MARGIN + col * (third_w + 6*mm)
        card_h = 95*mm
        draw_rounded_card(c, x, y - card_h, third_w, card_h, border_col=color)

        # Title
        c.setFillColor(color)
        c.roundRect(x, y - 10*mm, third_w, 10*mm, 2*mm, fill=1, stroke=0)
        draw_text_centered(c, x + third_w/2, y - 7*mm, title, size=7,
                           color=white, font="Helvetica-Bold")

        # Metrics table
        my = y - 14*mm
        for label, val in metrics:
            draw_text(c, x + 4*mm, my, label, size=7, color=TEXT_MUTED)
            draw_text(c, x + third_w - 4*mm - len(val)*4, my, val,
                      size=8, color=color, font="Helvetica-Bold")
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.3)
            c.line(x + 4*mm, my - 2*mm, x + third_w - 4*mm, my - 2*mm)
            my -= 8*mm

        # Note
        note_y = y - card_h + 18*mm
        draw_rounded_card(c, x + 3*mm, note_y - 12*mm, third_w - 6*mm, 14*mm,
                          fill=HexColor("#0d1117"), border_col=BORDER)
        for i, line in enumerate(note.split('\n')):
            draw_text(c, x + 5*mm, note_y - 4*mm - i*5*mm, line, size=5.5, color=TEXT_MUTED)

    # Footer
    fy = y - 105*mm
    draw_rounded_card(c, MARGIN, fy - 14*mm, full_w, 14*mm,
                      fill=HexColor("#0d1117"), border_col=ACCENT_PURPLE)
    draw_text(c, MARGIN + 6*mm, fy - 5*mm,
              "Next phase: SUIT UV imaging features (pre-flare active region signatures) → expected AUC 0.90+",
              size=8, color=ACCENT_PURPLE, font="Helvetica-Bold")
    draw_text(c, MARGIN + 6*mm, fy - 10*mm,
              "Models saved: outputs/models/detector_xgb.pkl  |  dual_instrument_xgb.pkl  |  forecaster_xgb.pkl",
              size=7, color=TEXT_MUTED)


# ===========================================================================
# Main — Build PDF
# ===========================================================================
def main():
    c = canvas.Canvas(str(OUTPUT_PDF), pagesize=landscape(A4))
    c.setTitle("S.H.I.E.L.D. Dashboard Design")
    c.setAuthor("Team Suryastra")
    c.setSubject("Dashboard Design Reference — Bharatiya Antariksh Hackathon 2026")

    page_cover(c)
    c.showPage()
    page_layout_grid(c)
    c.showPage()
    page_components(c)
    c.showPage()
    page_design_system(c)
    c.showPage()
    page_tech_stack(c)
    c.showPage()
    page_interactions(c)
    c.showPage()
    page_detail_panels(c)
    c.showPage()
    page_ml_results(c)
    c.showPage()

    c.save()
    n_pages = 8
    print(f"  PDF generated: {OUTPUT_PDF}")
    print(f"  Pages: {n_pages}")
    print(f"  Size: {OUTPUT_PDF.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
