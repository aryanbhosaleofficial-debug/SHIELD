"""
Build stunning ISRO BAH 2026 PDF submission for S.H.I.E.L.D.
Pages 1, 2, 10: Preserved from original PPTX (rendered with ISRO template backgrounds + text)
Pages 3-9: Custom designed with AI-generated images and rich content
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import io

# =============================================================================
# Configuration
# =============================================================================

OUTPUT_PDF = Path("SHIELD_ISRO_Final.pdf")

# Page size — 16:9 widescreen (standard presentation)
PAGE_W = 13.333 * inch  # ~960pt
PAGE_H = 7.5 * inch     # ~540pt
PAGE_SIZE = (PAGE_W, PAGE_H)

# Colors
DARK_BG = HexColor("#0a0e1a")
DARK_CARD = HexColor("#111827")
CARD_BORDER = HexColor("#1e293b")
ORANGE = HexColor("#F97316")
AMBER = HexColor("#F59E0B")
SOLAR_GOLD = HexColor("#FBBF24")
GREEN = HexColor("#22c55e")
RED = HexColor("#ef4444")
BLUE = HexColor("#3B82F6")
CYAN = HexColor("#06b6d4")
WHITE = HexColor("#FFFFFF")
BLACK = HexColor("#000000")
BODY_TEXT = HexColor("#FFFFFF")       # White for dark background
DESC_TEXT = HexColor("#e2e8f0")       # Light gray for dark background
LIGHT_GRAY = HexColor("#94a3b8")
MEDIUM_GRAY = HexColor("#555555")     # Darker gray for better contrast
VERY_LIGHT = HexColor("#e2e8f0")
GRADIENT_START = HexColor("#F97316")
GRADIENT_END = HexColor("#3B82F6")

# Asset paths — use optimized JPEGs where available
OPT_DIR = Path("_optimized_assets")

TEMPLATE_BG = OPT_DIR / "template_bg.jpg"            # ISRO template bg (slides 2-9)
TITLE_BG = OPT_DIR / "title_bg.jpg"                   # Title slide bg
LAST_BG = Path("_shield_assets/image4.jpg")           # Last slide bg (already small)
DASHBOARD_IMG = OPT_DIR / "dashboard.jpg"             # Dashboard screenshot
SUIT_IMG = OPT_DIR / "suit.jpg"                        # SUIT solar image
VELC_IMG = Path("dashboard/public/velc_real.png")     # VELC spectrogram

# AI-generated images (optimized)
HERO_IMG = OPT_DIR / "solar_flare_hero.jpg"
ARCH_IMG = OPT_DIR / "architecture_diagram.jpg"
NEUPERT_IMG = OPT_DIR / "neupert_effect.jpg"
PIPELINE_IMG = OPT_DIR / "pipeline_flow.jpg"
TECHSTACK_IMG = OPT_DIR / "tech_stack_visual.jpg"

# Try to register fonts
FONT_BOLD = "Helvetica-Bold"
FONT_REG = "Helvetica"
FONT_ITALIC = "Helvetica-Oblique"

# Attempt to register better fonts
try:
    # Try common Windows font paths
    font_paths = [
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
        Path("C:/Windows/Fonts/calibrii.ttf"),
    ]
    if font_paths[0].exists():
        pdfmetrics.registerFont(TTFont("Calibri", str(font_paths[0])))
        pdfmetrics.registerFont(TTFont("Calibri-Bold", str(font_paths[1])))
        FONT_REG = "Calibri"
        FONT_BOLD = "Calibri-Bold"
except:
    pass


# =============================================================================
# Helper Functions
# =============================================================================

def draw_bg_image(c, img_path, opacity=1.0):
    """Draw a background image covering the full page."""
    if img_path and img_path.exists():
        c.saveState()
        if opacity < 1.0:
            # Draw with transparency
            c.setFillColor(DARK_BG)
            c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        c.drawImage(str(img_path), 0, 0, width=PAGE_W, height=PAGE_H,
                    preserveAspectRatio=False, mask='auto')
        c.restoreState()


def draw_dark_bg(c):
    """Fill page with dark background."""
    c.setFillColor(DARK_BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def draw_gradient_bar(c, x, y, w, h):
    """Draw a horizontal gradient bar (orange to blue)."""
    steps = 60
    step_w = w / steps
    for i in range(steps):
        r = GRADIENT_START.red + (GRADIENT_END.red - GRADIENT_START.red) * i / steps
        g = GRADIENT_START.green + (GRADIENT_END.green - GRADIENT_START.green) * i / steps
        b = GRADIENT_START.blue + (GRADIENT_END.blue - GRADIENT_START.blue) * i / steps
        c.setFillColor(Color(r, g, b))
        c.rect(x + i * step_w, y, step_w + 1, h, fill=1, stroke=0)


def draw_card(c, x, y, w, h, fill_color=DARK_CARD, border_color=CARD_BORDER, radius=8):
    """Draw a rounded card with border."""
    c.saveState()
    c.setFillColor(fill_color)
    c.setStrokeColor(border_color)
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)
    c.restoreState()


def draw_text(c, text, x, y, font=None, size=12, color=WHITE, align="left", max_width=None):
    """Draw text with specified properties."""
    if font is None:
        font = FONT_REG
    c.saveState()
    c.setFont(font, size)
    c.setFillColor(color)
    if align == "center" and max_width:
        text_w = c.stringWidth(text, font, size)
        x = x + (max_width - text_w) / 2
    elif align == "right" and max_width:
        text_w = c.stringWidth(text, font, size)
        x = x + max_width - text_w
    c.drawString(x, y, text)
    c.restoreState()


def draw_wrapped_text(c, text, x, y, max_width, font=None, size=11, color=WHITE, leading=15):
    """Draw text with word wrapping."""
    if font is None:
        font = FONT_REG
    style = ParagraphStyle(
        'custom',
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=color,
    )
    p = Paragraph(text, style)
    pw, ph = p.wrap(max_width, 500)
    p.drawOn(c, x, y - ph)
    return ph


def draw_bullet_list(c, items, x, y, max_width, font=None, size=10, color=WHITE, leading=14, bullet_color=None):
    """Draw a bulleted list."""
    if font is None:
        font = FONT_REG
    if bullet_color is None:
        bullet_color = ORANGE
    
    current_y = y
    for item in items:
        # Bullet
        c.saveState()
        c.setFillColor(bullet_color)
        c.circle(x + 4, current_y + 3, 3, fill=1, stroke=0)
        c.restoreState()
        
        # Text
        h = draw_wrapped_text(c, item, x + 14, current_y + size/2, max_width - 14, font, size, color, leading)
        current_y -= h + 4
    
    return y - current_y


def draw_isro_header(c):
    """Draw the ISRO template header bar (dark band with logos)."""
    # Top dark band
    c.setFillColor(HexColor("#0a0a0a"))
    c.rect(0, PAGE_H - 0.65*inch, PAGE_W, 0.65*inch, fill=1, stroke=0)
    
    # ISRO logo area (left) — draw text as placeholder
    draw_text(c, "ISRO", 0.5*inch, PAGE_H - 0.45*inch, FONT_BOLD, 14, ORANGE)
    
    # H2S logo area (right)
    draw_text(c, "H2S", PAGE_W - 1*inch, PAGE_H - 0.45*inch, FONT_BOLD, 14, WHITE)
    
    # Bottom gradient bar
    draw_gradient_bar(c, 0, 0.08*inch, PAGE_W, 0.08*inch)


def draw_isro_template_bg(c):
    """Draw the ISRO template background for content slides."""
    if TEMPLATE_BG.exists():
        c.drawImage(str(TEMPLATE_BG), 0, 0, width=PAGE_W, height=PAGE_H,
                    preserveAspectRatio=False, mask='auto')
    else:
        # Fallback: white bg with header
        c.setFillColor(WHITE)
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        draw_isro_header(c)


def draw_page_number(c, num, total=10):
    """Draw page number in bottom right."""
    draw_text(c, f"{num}/{total}", PAGE_W - 0.8*inch, 0.25*inch, FONT_REG, 9, MEDIUM_GRAY)


def draw_section_title(c, title, y=None, color=None):
    """Draw a section title on a content page."""
    if y is None:
        y = PAGE_H - 1.3*inch
    if color is None:
        color = WHITE
    draw_text(c, title, 0.8*inch, y, FONT_BOLD, 22, color)
    # Underline accent
    c.setStrokeColor(ORANGE)
    c.setLineWidth(2.5)
    title_w = c.stringWidth(title, FONT_BOLD, 22)
    c.line(0.8*inch, y - 5, 0.8*inch + title_w, y - 5)


def fit_image(c, img_path, x, y, max_w, max_h, mask='auto'):
    """Draw image fitted within bounds, maintaining aspect ratio."""
    if img_path and img_path.exists():
        c.drawImage(str(img_path), x, y, width=max_w, height=max_h,
                    preserveAspectRatio=True, anchor='c', mask=mask)


# =============================================================================
# Page Builders
# =============================================================================

def build_page1(c):
    """Page 1: Title slide — preserved from PPTX."""
    # Full background from SHIELD submission
    draw_bg_image(c, TITLE_BG)
    
    # Team & problem info (positioned to match PPTX layout)
    # Bottom section (white area in template)
    draw_text(c, "Team Name : Team Suryastra", 
              0.8*inch, PAGE_H * 0.28, FONT_BOLD, 16, BLACK)
    
    draw_wrapped_text(c, 
        "Problem Statement : Solar Hazard Interception & Extra-orbital Logistics Dashboard "
        "(S.H.I.E.L.D.) - A real-data early-warning system built on Aditya-L1 SoLEXS & HEL1OS",
        0.8*inch, PAGE_H * 0.24, PAGE_W - 1.6*inch,
        FONT_REG, 12, BODY_TEXT, leading=16)
    
    draw_text(c, "Team Leader Name : Aryan Bhosale",
              0.8*inch, PAGE_H * 0.1, FONT_BOLD, 14, BLACK)
    
    draw_page_number(c, 1)


def build_page2(c):
    """Page 2: Team Members — preserved from PPTX."""
    draw_isro_template_bg(c)
    
    draw_section_title(c, "Team Members")
    
    draw_page_number(c, 2)


def build_page3(c):
    """Page 3: Opportunity / USP — ENHANCED."""
    draw_isro_template_bg(c)
    
    draw_section_title(c, "Opportunity: What Makes S.H.I.E.L.D. Different")
    
    content_y = PAGE_H - 1.8*inch
    left_x = 0.8*inch
    content_w = PAGE_W * 0.55
    
    # USP points with styled cards
    usps = [
        ("<b>100% Indian Data:</b> Unlike most teams using NOAA's American GOES data, S.H.I.E.L.D. is built "
         "entirely on India's own Aditya-L1 mission. We use real SoLEXS (soft X-ray) + HEL1OS (hard X-ray) "
         "FITS files from ISRO's PRADAN portal."),
        ("<b>Physics-First, Not Blackbox AI:</b> Our Layer 1 engine uses zero-training deterministic "
         "algorithms based on the Neupert Effect -- a proven astrophysical relationship. No training data "
         "needed, no overfitting risk, fully transparent."),
        ("<b>Dual-Instrument Fusion:</b> S.H.I.E.L.D. is the first system to algorithmically fuse SoLEXS "
         "and HEL1OS data streams in real-time: SoLEXS derivative FORECASTS the flare, HEL1OS spike CONFIRMS it."),
        ("<b>Validated on Real Events:</b> Tested against 6 actual solar flares (X1.8 to X8.7) from "
         "Aditya-L1 data spanning Jan 2024 - Nov 2025. 93.5% ROC-AUC, 95.9% precision."),
        ("<b>Working Dashboard:</b> Live Next.js application showing real-time light curves, 4-stage "
         "detection status, impact advisories, and alert logs."),
    ]
    
    style = ParagraphStyle(
        'usp',
        fontName=FONT_REG,
        fontSize=10,
        leading=13,
        textColor=BODY_TEXT,
    )
    
    current_y = content_y
    for i, usp in enumerate(usps):
        # Bullet number
        c.saveState()
        c.setFillColor(ORANGE)
        c.circle(left_x + 6, current_y + 3, 8, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 9)
        c.drawCentredString(left_x + 6, current_y, str(i+1))
        c.restoreState()
        
        p = Paragraph(usp, style)
        pw, ph = p.wrap(content_w - 25, 200)
        p.drawOn(c, left_x + 20, current_y - ph + 8)
        current_y -= ph + 8
    
    # Right side: Neupert Effect image
    img_x = PAGE_W * 0.58
    img_y = PAGE_H * 0.15
    img_w = PAGE_W * 0.38
    img_h = PAGE_H * 0.65
    
    if NEUPERT_IMG and NEUPERT_IMG.exists():
        # Dark card behind image
        c.saveState()
        c.setFillColor(HexColor("#0a0e1a"))
        c.roundRect(img_x - 5, img_y - 5, img_w + 10, img_h + 10, 10, fill=1, stroke=0)
        c.restoreState()
        fit_image(c, NEUPERT_IMG, img_x, img_y, img_w, img_h)
        draw_text(c, "The Neupert Effect", img_x + img_w/2 - 60, img_y - 18, FONT_BOLD, 9, MEDIUM_GRAY)
    
    draw_page_number(c, 3)


def build_page4(c):
    """Page 4: Key Features — ENHANCED with icons and cards."""
    draw_isro_template_bg(c)
    
    draw_section_title(c, "Key Features of S.H.I.E.L.D.")
    
    features = [
        ("DATA", "Real Aditya-L1 Data Ingestion",
         "Reads SoLEXS & HEL1OS FITS files directly from ISRO PRADAN. "
         "Time-aligns multi-instrument data using merge_asof with 1-second cadence.",
         BLUE),
        ("4-STAGE", "4-Stage Detection Pipeline",
         "State machine: Quiet Sun > Pre-Flare Heating > Forecast Alert > Nowcast Confirmed. "
         "Physics-driven transitions with configurable thresholds.",
         GREEN),
        ("PHYSICS", "Neupert Effect Engine",
         "Watches SoLEXS soft X-ray derivative to ANTICIPATE flares, waits for HEL1OS "
         "hard X-ray spike to CONFIRM. Zero-training, fully deterministic.",
         ORANGE),
        ("ML", "3-Layer Algorithm Stack",
         "Layer 1: Physics Engine (primary). Layer 2: XGBoost severity classifier (C/M/X). "
         "Layer 3: LSTM 30-min probabilistic forecaster.",
         CYAN),
        ("ALERT", "Impact Advisory System",
         "Real-time alerts with satellite, GPS, radio, aviation, and power grid impact "
         "assessment. Automated severity-based advisories.",
         RED),
        ("DASH", "Live Monitoring Dashboard",
         "Next.js + React + Plotly interactive dashboard. Real-time SoLEXS/HEL1OS light "
         "curves, SUIT UV images, VELC spectrograms, alert logs.",
         AMBER),
    ]
    
    # 2 columns x 3 rows of feature cards
    card_w = (PAGE_W - 2.2*inch) / 2
    card_h = 1.15*inch
    gap = 0.15*inch
    start_x = 0.8*inch
    start_y = PAGE_H - 2*inch
    
    text_color = HexColor('#1f2937')
    
    for i, (tag, title, desc, accent) in enumerate(features):
        col = i % 2
        row = i // 2
        cx = start_x + col * (card_w + gap)
        cy = start_y - row * (card_h + gap)
        
        # Card background
        c.saveState()
        c.setFillColor(HexColor("#f8fafc"))
        c.setStrokeColor(HexColor("#e2e8f0"))
        c.setLineWidth(1)
        c.roundRect(cx, cy, card_w, card_h, 6, fill=1, stroke=1)
        
        # Left accent bar
        c.setFillColor(accent)
        c.rect(cx, cy, 4, card_h, fill=1, stroke=0)
        c.restoreState()
        
        # Tag badge
        c.saveState()
        c.setFillColor(accent)
        tag_w = c.stringWidth(tag, FONT_BOLD, 7) + 8
        c.roundRect(cx + 15, cy + card_h - 22, tag_w, 14, 3, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 7)
        c.drawString(cx + 19, cy + card_h - 19, tag)
        c.restoreState()
        
        # Title
        draw_text(c, title, cx + 15, cy + card_h - 38, FONT_BOLD, 11, text_color)
        
        # Description
        style = ParagraphStyle('fdesc', fontName=FONT_REG, fontSize=8.5, leading=11,
                              textColor=HexColor('#6b7280'))
        p = Paragraph(desc, style)
        pw, ph = p.wrap(card_w - 30, 60)
        p.drawOn(c, cx + 15, cy + 5)
    
    draw_page_number(c, 4)


def build_page5(c):
    """Page 5: Process Flow Diagram — ENHANCED."""
    draw_isro_template_bg(c)
    
    draw_section_title(c, "4-Stage Detection Pipeline Flow")
    
    # Pipeline flow image
    if PIPELINE_IMG and PIPELINE_IMG.exists():
        img_w = PAGE_W * 0.85
        img_h = PAGE_H * 0.45
        img_x = (PAGE_W - img_w) / 2
        img_y = PAGE_H * 0.28
        
        c.saveState()
        c.setFillColor(HexColor("#0a0e1a"))
        c.roundRect(img_x - 8, img_y - 8, img_w + 16, img_h + 16, 12, fill=1, stroke=0)
        c.restoreState()
        
        fit_image(c, PIPELINE_IMG, img_x, img_y, img_w, img_h)
    
    # Stage details below
    stages = [
        ("S1: QUIET SUN", "Baseline monitoring\nAll sensors nominal", GREEN),
        ("S2: PRE-FLARE", "SoLEXS derivative\nstarts rising", AMBER),
        ("S3: FORECAST", "Sustained slope\nsteepening >60s", ORANGE),
        ("S4: NOWCAST", "HEL1OS 5-sigma\nspike confirmed", RED),
    ]
    
    stage_w = (PAGE_W - 2*inch) / 4
    stage_y = 0.4*inch
    stage_h = 0.55*inch
    
    for i, (name, desc, color) in enumerate(stages):
        sx = 0.8*inch + i * stage_w
        
        # Stage card
        c.saveState()
        c.setFillColor(color)
        c.setFillAlpha(0.12)
        c.roundRect(sx + 4, stage_y, stage_w - 8, stage_h, 5, fill=1, stroke=0)
        c.restoreState()
        
        # Top colored line
        c.setStrokeColor(color)
        c.setLineWidth(2)
        c.line(sx + 4, stage_y + stage_h, sx + stage_w - 4, stage_y + stage_h)
        
        draw_text(c, name, sx + 10, stage_y + stage_h - 16, FONT_BOLD, 9, color)
        
        lines = desc.split("\n")
        for j, line in enumerate(lines):
            draw_text(c, line, sx + 10, stage_y + stage_h - 28 - j*11, FONT_REG, 8, HexColor("#e2e8f0"))
        
        # Arrow between stages
        if i < 3:
            c.saveState()
            c.setStrokeColor(MEDIUM_GRAY)
            c.setLineWidth(1.5)
            arrow_x = sx + stage_w - 2
            arrow_y = stage_y + stage_h / 2
            c.line(arrow_x - 4, arrow_y, arrow_x + 4, arrow_y)
            # Arrowhead
            c.setFillColor(MEDIUM_GRAY)
            c.drawString(arrow_x + 1, arrow_y - 4, ">")
            c.restoreState()
    
    draw_page_number(c, 5)


def build_page6(c):
    """Page 6: Dashboard / Wireframes — ENHANCED."""
    draw_isro_template_bg(c)
    
    draw_section_title(c, "Live Dashboard (Built & Running)")
    
    # Subtitle
    draw_wrapped_text(c,
        "Real Next.js application on real Aditya-L1 data. Shows live SoLEXS + HEL1OS light curves, "
        "4-stage detection pipeline status, and impact advisories.",
        0.8*inch, PAGE_H - 1.55*inch, PAGE_W - 1.6*inch,
        FONT_REG, 10, HexColor("#e2e8f0"), leading=13)
    
    # Dashboard screenshot — main feature
    dash_w = PAGE_W * 0.62
    dash_h = PAGE_H * 0.58
    dash_x = 0.6*inch
    dash_y = 0.5*inch
    
    # Shadow/frame
    c.saveState()
    c.setFillColor(HexColor("#1e293b"))
    c.roundRect(dash_x - 4, dash_y - 4, dash_w + 8, dash_h + 8, 8, fill=1, stroke=0)
    c.restoreState()
    
    if DASHBOARD_IMG.exists():
        c.drawImage(str(DASHBOARD_IMG), dash_x, dash_y, width=dash_w, height=dash_h,
                    preserveAspectRatio=True, anchor='nw', mask='auto')
    
    # Right side: Key metrics and SUIT image
    right_x = dash_x + dash_w + 0.3*inch
    right_w = PAGE_W - right_x - 0.5*inch
    
    # Metrics cards
    metrics = [
        ("877", "Days Scanned", BLUE),
        ("175", "Flares Detected", ORANGE),
        ("95.9%", "Precision", GREEN),
        ("0.33", "False Alarms/24h", CYAN),
    ]
    
    metric_h = 0.52*inch
    metric_y = PAGE_H - 1.8*inch
    
    for i, (val, label, color) in enumerate(metrics):
        my = metric_y - i * (metric_h + 0.08*inch)
        
        c.saveState()
        c.setFillColor(HexColor("#f1f5f9"))
        c.setStrokeColor(HexColor("#e2e8f0"))
        c.roundRect(right_x, my, right_w, metric_h, 5, fill=1, stroke=1)
        
        # Left accent
        c.setFillColor(color)
        c.rect(right_x, my, 3, metric_h, fill=1, stroke=0)
        c.restoreState()
        
        draw_text(c, val, right_x + 12, my + metric_h - 20, FONT_BOLD, 16, color)
        draw_text(c, label, right_x + 12, my + 8, FONT_REG, 8, HexColor("#6b7280"))
    
    # SUIT image at bottom right
    suit_size = right_w * 0.85
    suit_y = 0.5*inch
    suit_x = right_x + (right_w - suit_size) / 2
    
    if SUIT_IMG.exists():
        c.saveState()
        c.setStrokeColor(ORANGE)
        c.setLineWidth(2)
        c.roundRect(suit_x - 3, suit_y - 3, suit_size + 6, suit_size + 6, 6, fill=0, stroke=1)
        c.restoreState()
        c.drawImage(str(SUIT_IMG), suit_x, suit_y, width=suit_size, height=suit_size,
                    preserveAspectRatio=True, mask='auto')
        draw_text(c, "SUIT UV Image (May 2024)", suit_x, suit_y - 12, FONT_REG, 7, MEDIUM_GRAY)
    
    # Label
    draw_text(c, "Demonstrated: May 2024 X8.7 flare (strongest of the century)",
              dash_x, dash_y - 16, FONT_BOLD, 8, ORANGE)
    
    draw_page_number(c, 6)


def build_page7(c):
    """Page 7: Architecture Diagram — ENHANCED."""
    draw_isro_template_bg(c)
    
    draw_section_title(c, "System Architecture")
    
    # Architecture image
    if ARCH_IMG and ARCH_IMG.exists():
        img_w = PAGE_W * 0.55
        img_h = PAGE_H * 0.6
        img_x = 0.5*inch
        img_y = 0.4*inch
        
        c.saveState()
        c.setFillColor(HexColor("#0a0e1a"))
        c.roundRect(img_x - 6, img_y - 6, img_w + 12, img_h + 12, 10, fill=1, stroke=0)
        c.restoreState()
        
        fit_image(c, ARCH_IMG, img_x, img_y, img_w, img_h)
    
    # Right side: Detailed architecture text
    right_x = PAGE_W * 0.56
    right_w = PAGE_W * 0.4
    text_color = HexColor('#FFFFFF')
    
    layers = [
        ("Data Layer", [
            "Aditya-L1 Instruments: SUIT | SoLEXS | HEL1OS | VELC",
            "FITS file reader (Astropy) + ZIP extraction",
            "Time alignment via merge_asof (1-sec cadence)",
            "PyArrow Parquet for 100+ GB scaling",
        ], BLUE),
        ("Processing Layer", [
            "Layer 1: Physics Engine (Neupert Effect)",
            "Layer 2: XGBoost C/M/X Classifier",
            "Layer 3: LSTM 30-min Forecaster",
            "Adaptive rolling baseline (10-min window)",
        ], ORANGE),
        ("Presentation Layer", [
            "Next.js 16 + React 19 Dashboard",
            "Plotly.js interactive light curves",
            "4-stage status + impact advisories",
            "Real-time alert log system",
        ], GREEN),
    ]
    
    ly = PAGE_H - 1.8*inch
    
    for layer_name, items, color in layers:
        # Layer header
        c.saveState()
        c.setFillColor(color)
        header_w = c.stringWidth(layer_name, FONT_BOLD, 9) + 12
        c.roundRect(right_x, ly, header_w, 16, 3, fill=1, stroke=0)
        c.restoreState()
        draw_text(c, layer_name, right_x + 6, ly + 4, FONT_BOLD, 9, WHITE)
        
        ly -= 8
        for item in items:
            ly -= 14
            c.setFillColor(color)
            c.circle(right_x + 5, ly + 4, 2.5, fill=1, stroke=0)
            draw_text(c, item, right_x + 14, ly, FONT_REG, 8.5, text_color)
        
        ly -= 15
    
    draw_page_number(c, 7)


def build_page8(c):
    """Page 8: Technologies — ENHANCED."""
    draw_isro_template_bg(c)
    
    draw_section_title(c, "Technologies Used")
    
    # Tech categories
    categories = [
        ("Data Ingestion & Alignment", [
            ("Python 3.10+", "Core language"),
            ("Pandas & NumPy", "Time-series processing"),
            ("Astropy", "FITS file I/O for PRADAN data"),
            ("CDFlib", "CDF heliophysics products"),
            ("PyArrow", "Parquet store (100+ GB scaling)"),
        ], BLUE),
        ("Physics & Signal Processing", [
            ("SciPy", "Rolling statistics, interpolation"),
            ("SunPy", "Solar data standards"),
            ("NumPy Gradient", "Derivative computation"),
            ("Custom Engine", "Neupert Effect implementation"),
        ], ORANGE),
        ("Machine Learning", [
            ("Scikit-learn", "Feature engineering & metrics"),
            ("XGBoost", "Layer 2 severity classifier"),
            ("Keras / TensorFlow", "Layer 3 LSTM forecaster"),
        ], GREEN),
        ("Dashboard & Visualization", [
            ("Next.js 16", "React framework"),
            ("React 19", "UI components"),
            ("TypeScript", "Type-safe development"),
            ("Plotly.js", "Interactive charts"),
            ("TailwindCSS 4", "Styling"),
        ], CYAN),
    ]
    
    # Layout: 2 columns
    col_w = (PAGE_W - 2*inch) / 2
    text_color = HexColor('#FFFFFF')
    
    for i, (cat_name, techs, color) in enumerate(categories):
        col = i % 2
        row = i // 2
        
        cx = 0.8*inch + col * (col_w + 0.3*inch)
        cy = PAGE_H - 2*inch - row * 2.4*inch
        
        # Category header
        c.saveState()
        c.setFillColor(color)
        c.setFillAlpha(0.1)
        c.roundRect(cx, cy - 1.9*inch, col_w - 0.1*inch, 2.2*inch, 8, fill=1, stroke=0)
        c.restoreState()
        
        c.setStrokeColor(color)
        c.setLineWidth(2)
        c.line(cx, cy + 0.3*inch, cx + col_w - 0.1*inch, cy + 0.3*inch)
        
        draw_text(c, cat_name, cx + 8, cy + 0.35*inch, FONT_BOLD, 12, color)
        
        ty = cy
        for tech_name, tech_desc in techs:
            # Tech name (bold) + description
            c.saveState()
            c.setFillColor(color)
            c.circle(cx + 12, ty + 3, 3, fill=1, stroke=0)
            c.restoreState()
            
            draw_text(c, tech_name, cx + 22, ty, FONT_BOLD, 9.5, text_color)
            name_w = c.stringWidth(tech_name, FONT_BOLD, 9.5)
            draw_text(c, f"  --  {tech_desc}", cx + 22 + name_w, ty, FONT_REG, 9, HexColor("#e2e8f0"))
            ty -= 17
    
    # Data source callout at bottom
    c.saveState()
    c.setFillColor(ORANGE)
    c.setFillAlpha(0.08)
    c.roundRect(0.8*inch, 0.35*inch, PAGE_W - 1.6*inch, 0.5*inch, 6, fill=1, stroke=0)
    c.restoreState()
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.5)
    c.roundRect(0.8*inch, 0.35*inch, PAGE_W - 1.6*inch, 0.5*inch, 6, fill=0, stroke=1)
    
    draw_text(c, "Data Source: ISRO PRADAN Portal (pradan.issdc.gov.in/al1) -- "
              "100% real Aditya-L1 SoLEXS & HEL1OS telemetry (Jan 2024 - Nov 2025)",
              1.0*inch, 0.5*inch, FONT_BOLD, 10, ORANGE)
    
    draw_page_number(c, 8)


def build_page9(c):
    """Page 9: Implementation Cost & Roadmap — ENHANCED."""
    draw_isro_template_bg(c)
    
    draw_section_title(c, "Implementation Cost & Roadmap")
    
    text_color = HexColor('#1f2937')
    
    # Left: Current (Zero Cost)
    left_x = 0.8*inch
    left_w = (PAGE_W - 2*inch) * 0.48
    
    # Cost card
    card_y = PAGE_H - 2*inch
    card_h = 3.8*inch
    
    c.saveState()
    c.setFillColor(HexColor("#f0fdf4"))
    c.setStrokeColor(GREEN)
    c.setLineWidth(1.5)
    c.roundRect(left_x, card_y - card_h + 0.7*inch, left_w, card_h, 8, fill=1, stroke=1)
    c.restoreState()
    
    # Header
    c.saveState()
    c.setFillColor(GREEN)
    c.roundRect(left_x, card_y + 0.4*inch, left_w, 0.3*inch, 8, fill=1, stroke=0)
    c.rect(left_x, card_y + 0.4*inch, left_w, 0.15*inch, fill=1, stroke=0)
    c.restoreState()
    draw_text(c, "CURRENT IMPLEMENTATION", left_x + 10, card_y + 0.5*inch, FONT_BOLD, 12, WHITE)
    draw_text(c, "ZERO COST", left_x + left_w - 1.1*inch, card_y + 0.5*inch, FONT_BOLD, 12, WHITE)
    
    items = [
        "Built entirely on open-source tools",
        "Publicly available Aditya-L1 PRADAN data",
        "No paid APIs, cloud services, or licenses",
        "Runs on a single laptop (Python + Node.js)",
        "All 6 validation events processed locally",
        "93.5% ROC-AUC achieved at zero cost",
        "877 days of data scanned end-to-end",
    ]
    
    iy = card_y + 0.15*inch
    for item in items:
        c.setFillColor(GREEN)
        c.circle(left_x + 15, iy + 3, 3, fill=1, stroke=0)
        draw_text(c, item, left_x + 25, iy, FONT_REG, 9.5, text_color)
        iy -= 18
    
    # Total
    c.saveState()
    c.setFillColor(HexColor("#dcfce7"))
    c.roundRect(left_x + 8, iy - 8, left_w - 16, 22, 4, fill=1, stroke=0)
    c.restoreState()
    draw_text(c, "Total Cost: Rs. 0  (Zero)", left_x + 20, iy - 2, FONT_BOLD, 11, GREEN)
    
    # Right: Future Roadmap
    right_x = left_x + left_w + 0.25*inch
    right_w = (PAGE_W - 2*inch) * 0.48
    
    c.saveState()
    c.setFillColor(HexColor("#eff6ff"))
    c.setStrokeColor(BLUE)
    c.setLineWidth(1.5)
    c.roundRect(right_x, card_y - card_h + 0.7*inch, right_w, card_h, 8, fill=1, stroke=1)
    c.restoreState()
    
    # Header
    c.saveState()
    c.setFillColor(BLUE)
    c.roundRect(right_x, card_y + 0.4*inch, right_w, 0.3*inch, 8, fill=1, stroke=0)
    c.rect(right_x, card_y + 0.4*inch, right_w, 0.15*inch, fill=1, stroke=0)
    c.restoreState()
    draw_text(c, "FUTURE ROADMAP", right_x + 10, card_y + 0.5*inch, FONT_BOLD, 12, WHITE)
    
    roadmap = [
        ("Phase 1", "ISRO Integration", "Direct PRADAN API feed for\nreal-time streaming", ORANGE),
        ("Phase 2", "Multi-Instrument", "Add SUIT UV + VELC coronagraph\nfor CME tracking", CYAN),
        ("Phase 3", "Edge Deployment", "Onboard satellite processing\nfor zero-latency alerts", GREEN),
        ("Phase 4", "National Service", "Space weather service for\nINSAT, NavIC, Gaganyaan", AMBER),
    ]
    
    ry = card_y + 0.1*inch
    for phase, title, desc, color in roadmap:
        # Phase badge
        c.saveState()
        c.setFillColor(color)
        badge_w = c.stringWidth(phase, FONT_BOLD, 8) + 10
        c.roundRect(right_x + 12, ry + 1, badge_w, 14, 3, fill=1, stroke=0)
        c.restoreState()
        draw_text(c, phase, right_x + 17, ry + 4, FONT_BOLD, 8, WHITE)
        
        draw_text(c, title, right_x + 12 + badge_w + 6, ry + 4, FONT_BOLD, 10, text_color)
        
        lines = desc.split("\n")
        for j, line in enumerate(lines):
            draw_text(c, line, right_x + 22, ry - 12 - j*12, FONT_REG, 8.5, HexColor("#6b7280"))
        
        ry -= 45
    
    draw_page_number(c, 9)


def build_page10(c):
    """Page 10: Thank You — preserved from PPTX."""
    # Full background
    draw_bg_image(c, LAST_BG)
    
    draw_page_number(c, 10)


# =============================================================================
# Main
# =============================================================================

def main():
    print("Building S.H.I.E.L.D. ISRO Submission PDF...")
    print(f"Page size: {PAGE_W/inch:.1f}\" x {PAGE_H/inch:.1f}\" (16:9)")
    
    # Verify assets
    print("\nAssets:")
    for label, path in [
        ("Template BG", TEMPLATE_BG), ("Title BG", TITLE_BG), ("Last BG", LAST_BG),
        ("Dashboard", DASHBOARD_IMG), ("SUIT", SUIT_IMG), ("VELC", VELC_IMG),
        ("Hero", HERO_IMG), ("Architecture", ARCH_IMG), ("Neupert", NEUPERT_IMG),
        ("Pipeline", PIPELINE_IMG), ("TechStack", TECHSTACK_IMG),
    ]:
        status = "OK" if path and path.exists() else "MISSING"
        print(f"  [{status}] {label}: {path}")
    
    c = canvas.Canvas(str(OUTPUT_PDF), pagesize=PAGE_SIZE)
    c.setTitle("S.H.I.E.L.D. - Team Suryastra - ISRO BAH 2026")
    c.setAuthor("Team Suryastra")
    c.setSubject("Solar Hazard Interception & Extra-orbital Logistics Dashboard")
    
    pages = [
        ("Page 1: Title", build_page1),
        ("Page 2: Team Members", build_page2),
        ("Page 3: Opportunity/USP", build_page3),
        ("Page 4: Key Features", build_page4),
        ("Page 5: Pipeline Flow", build_page5),
        ("Page 6: Dashboard", build_page6),
        ("Page 7: Architecture", build_page7),
        ("Page 8: Technologies", build_page8),
        ("Page 9: Cost & Roadmap", build_page9),
        ("Page 10: Thank You", build_page10),
    ]
    
    for i, (name, builder) in enumerate(pages):
        print(f"  Building {name}...")
        builder(c)
        if i < len(pages) - 1:
            c.showPage()
    
    c.save()
    
    size_mb = OUTPUT_PDF.stat().st_size / (1024 * 1024)
    print(f"\nOutput: {OUTPUT_PDF}")
    print(f"Size: {size_mb:.2f} MB")
    if size_mb <= 5.0:
        print("[OK] Under 5 MB target")
    else:
        print("[WARN] Over 5 MB target - may need image optimization")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
