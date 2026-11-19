# =============================================================================
# S.H.I.E.L.D. — Hackathon Presentation Deck -> outputs/SHIELD_Presentation.pptx
#
# Honest deck: every "proven" number here is pulled from this project's own
# validated outputs (outputs/scan_all_summary.json, training_results.json,
# build_prd.py PRD v4 content). Forecasting is framed accurately — SoLEXS/
# HEL1OS give fast CONFIRMED detection (nowcasting), not advance warning,
# because real flares are impulsive (flux+temperature rise in 0-36s).
# The only path to genuine hours-ahead forecasting is SUIT (roadmap, in
# progress). VELC is future work for CME / geomagnetic impact.
# =============================================================================
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

OUT = Path(__file__).resolve().parent / "outputs" / "SHIELD_Presentation.pptx"

# ---------------------------------------------------------------------------
# Design-system colours (matches dashboard + PDF design reference)
# ---------------------------------------------------------------------------
BG_DARK   = RGBColor(0x0a, 0x0b, 0x14)
BG_CARD   = RGBColor(0x0f, 0x17, 0x29)
BORDER    = RGBColor(0x1e, 0x29, 0x3b)
WHITE     = RGBColor(0xf1, 0xf5, 0xf9)
MUTED     = RGBColor(0x94, 0xa3, 0xb8)
BLUE      = RGBColor(0x3b, 0x82, 0xf6)
ORANGE    = RGBColor(0xf9, 0x73, 0x16)
RED       = RGBColor(0xef, 0x44, 0x44)
GREEN     = RGBColor(0x10, 0xb9, 0x81)
YELLOW    = RGBColor(0xea, 0xb3, 0x08)
PURPLE    = RGBColor(0xa8, 0x55, 0xf7)
ROSE      = RGBColor(0xf4, 0x3f, 0x5e)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def new_slide():
    return prs.slides.add_slide(BLANK)


def set_bg(slide, color=BG_DARK):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    bg.line.fill.background()
    bg.shadow.inherit = False
    # send to back
    sp = bg._element
    sp.getparent().remove(sp)
    slide.shapes._spTree.insert(2, sp)
    return bg


def box(slide, x, y, w, h, fill=None, line=None, line_w=0.75, radius=0.08):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    try:
        shape.adjustments[0] = radius
    except Exception:
        pass
    if fill is not None:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if line is not None:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_w)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def text(slide, x, y, w, h, s, size=14, color=WHITE, bold=False, italic=False,
          align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font="Calibri", line_spacing=1.0):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    lines = s.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
        r.font.name = font
    return tb


def bullets(slide, x, y, w, h, items, size=13, color=WHITE, accent=ORANGE, gap=6, font="Calibri"):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        r1 = p.add_run()
        r1.text = "▸  "
        r1.font.size = Pt(size)
        r1.font.bold = True
        r1.font.color.rgb = accent
        r1.font.name = font
        r2 = p.add_run()
        r2.text = item
        r2.font.size = Pt(size)
        r2.font.color.rgb = color
        r2.font.name = font
    return tb


def kicker_title(slide, kicker, title, sub=None, color=ORANGE):
    text(slide, Inches(0.7), Inches(0.35), Inches(11.9), Inches(0.35),
         kicker.upper(), size=12, color=color, bold=True, font="Calibri")
    text(slide, Inches(0.7), Inches(0.68), Inches(11.9), Inches(0.7),
         title, size=30, color=WHITE, bold=True, font="Calibri")
    if sub:
        text(slide, Inches(0.7), Inches(1.32), Inches(11.9), Inches(0.45),
             sub, size=13, color=MUTED, font="Calibri")
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.72),
                                    Inches(11.9), Pt(1.4))
    rule.fill.solid()
    rule.fill.fore_color.rgb = BORDER
    rule.line.fill.background()
    rule.shadow.inherit = False


def footer(slide, n):
    text(slide, Inches(0.7), Inches(7.12), Inches(8), Inches(0.3),
         "S.H.I.E.L.D. · Team Suryastra · Bharatiya Antariksh Hackathon 2026 · Challenge #15",
         size=9, color=MUTED, font="Calibri")
    text(slide, Inches(12.3), Inches(7.12), Inches(0.4), Inches(0.3),
         str(n), size=9, color=MUTED, align=PP_ALIGN.RIGHT, font="Calibri")


def stat_card(slide, x, y, w, h, value, label, color=ORANGE, sub=None):
    box(slide, x, y, w, h, fill=BG_CARD, line=color, line_w=1.0, radius=0.10)
    text(slide, x, y + Inches(0.12), w, Inches(0.55), value, size=24, color=color,
         bold=True, align=PP_ALIGN.CENTER, font="Calibri")
    text(slide, x + Inches(0.08), y + h - Inches(0.5), w - Inches(0.16), Inches(0.35),
         label, size=10.5, color=WHITE, align=PP_ALIGN.CENTER, font="Calibri")
    if sub:
        text(slide, x + Inches(0.08), y + h - Inches(0.22), w - Inches(0.16), Inches(0.25),
             sub, size=8, color=MUTED, align=PP_ALIGN.CENTER, font="Calibri")


def mini_table(slide, x, y, headers, rows, col_w, row_h=0.36, header_color=ORANGE, font_size=10.5):
    # header row
    hx = x
    for i, htext in enumerate(headers):
        cw = Inches(col_w[i])
        box(slide, hx, y, cw, Inches(row_h), fill=BG_CARD, line=header_color, line_w=0.75, radius=0.04)
        text(slide, hx + Inches(0.08), y, cw - Inches(0.16), Inches(row_h), htext,
             size=font_size, color=header_color, bold=True, anchor=MSO_ANCHOR.MIDDLE, font="Calibri")
        hx += cw
    # data rows
    ry = y + Inches(row_h) + Pt(2)
    for row in rows:
        rx = x
        for i, cell in enumerate(row):
            cw = Inches(col_w[i])
            box(slide, rx, ry, cw, Inches(row_h), fill=None, line=BORDER, line_w=0.5, radius=0.0)
            text(slide, rx + Inches(0.08), ry, cw - Inches(0.16), Inches(row_h), str(cell),
                 size=font_size, color=WHITE, anchor=MSO_ANCHOR.MIDDLE, font="Calibri")
            rx += cw
        ry += Inches(row_h) + Pt(2)
    return ry


def badge(slide, x, y, w, h, txt, color):
    box(slide, x, y, w, h, fill=None, line=color, line_w=1.0, radius=0.5)
    text(slide, x, y, w, h, txt, size=10, color=color, bold=True,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, font="Calibri")


# =============================================================================
# SLIDE 1 — Title
# =============================================================================
s = new_slide()
set_bg(s)
text(s, Inches(0), Inches(2.55), SLIDE_W, Inches(1.1), "S.H.I.E.L.D.",
     size=64, color=ORANGE, bold=True, align=PP_ALIGN.CENTER, font="Calibri")
text(s, Inches(0), Inches(3.65), SLIDE_W, Inches(0.5),
     "Solar Hazard Interception & Extra-orbital Logistics Dashboard",
     size=18, color=WHITE, align=PP_ALIGN.CENTER, font="Calibri")
text(s, Inches(0), Inches(4.15), SLIDE_W, Inches(0.4),
     "A real-data early-warning system built on Aditya-L1 SoLEXS + HEL1OS",
     size=13, color=MUTED, align=PP_ALIGN.CENTER, font="Calibri")
rule = box(s, Inches(5.17), Inches(4.75), Inches(3.0), Pt(1.5), fill=BORDER)
text(s, Inches(0), Inches(5.0), SLIDE_W, Inches(0.4),
     "Team Suryastra", size=14, color=ORANGE, bold=True, align=PP_ALIGN.CENTER, font="Calibri")
text(s, Inches(0), Inches(5.4), SLIDE_W, Inches(0.4),
     "Bharatiya Antariksh Hackathon 2026 · Challenge #15", size=11, color=MUTED,
     align=PP_ALIGN.CENTER, font="Calibri")
text(s, Inches(0), Inches(6.6), SLIDE_W, Inches(0.4),
     "Built for the Sun. Built for India.", size=11, italic=True, color=MUTED,
     align=PP_ALIGN.CENTER, font="Calibri")


# =============================================================================
# SLIDE 2 — Problem Statement
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Challenge #15", "Solar Flares Threaten Earth & Space Infrastructure",
             "Aditya-L1 watches the Sun in real time — SHIELD turns that data into actionable warning")

domains = [
    ("Radio Blackouts", "HF radio loss during flares", BLUE),
    ("GPS / Navigation", "Positioning errors, signal loss", GREEN),
    ("Aviation", "Polar route HF comms disrupted", YELLOW),
    ("Satellites", "Single-event upsets, drag", PURPLE),
    ("Astronaut Radiation", "Radiation exposure risk", RED),
    ("Power Grids", "Geomagnetically induced currents", ROSE),
]
cx, cy = Inches(0.7), Inches(2.05)
cw, ch, gap = Inches(3.85), Inches(1.55), Inches(0.18)
for i, (title, desc, color) in enumerate(domains):
    col = i % 3
    row = i // 3
    x = cx + col * (cw + gap)
    y = cy + row * (ch + gap)
    box(s, x, y, cw, ch, fill=BG_CARD, line=color, line_w=1.0)
    text(s, x + Inches(0.2), y + Inches(0.18), cw - Inches(0.4), Inches(0.4), title,
         size=15, color=color, bold=True, font="Calibri")
    text(s, x + Inches(0.2), y + Inches(0.65), cw - Inches(0.4), Inches(0.8), desc,
         size=11.5, color=MUTED, font="Calibri")

text(s, Inches(0.7), Inches(5.55), Inches(11.9), Inches(1.2),
     "India needs an indigenous, real-data early-warning system using its own Aditya-L1 mission — "
     "not a dependency on foreign GOES/SWPC feeds alone.",
     size=14, color=WHITE, italic=True, font="Calibri")
footer(s, 2)


# =============================================================================
# SLIDE 3 — Data Sources
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Data", "Real Aditya-L1 Data — Not Simulated",
             "Sourced from ISRO PRADAN · processed directly from FITS/zip archives, no manual extraction")

instruments = [
    ("SoLEXS", "Soft X-ray (1-30 keV)", "Thermal flare emission, GOES-equivalent class/onset", BLUE, "BUILT"),
    ("HEL1OS", "Hard X-ray (10-150 keV)", "Impulsive burst, Neupert cross-validation", RED, "BUILT"),
    ("SUIT", "UV imaging", "Active-region build-up before a flare", ORANGE, "TESTING"),
    ("VELC", "Coronagraph", "CME detection, geomagnetic impact", PURPLE, "ROADMAP"),
]
cx, cy = Inches(0.7), Inches(2.05)
cw, ch, gap = Inches(2.84), Inches(3.1), Inches(0.22)
for i, (name, band, desc, color, status) in enumerate(instruments):
    x = cx + i * (cw + gap)
    box(s, x, cy, cw, ch, fill=BG_CARD, line=color, line_w=1.2)
    box(s, x, cy, cw, Inches(0.55), fill=color)
    text(s, x, cy, cw, Inches(0.55), name, size=17, color=RGBColor(0xff, 0xff, 0xff), bold=True,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, font="Calibri")
    text(s, x + Inches(0.18), cy + Inches(0.72), cw - Inches(0.36), Inches(0.4), band,
         size=11.5, color=MUTED, bold=True, font="Calibri")
    text(s, x + Inches(0.18), cy + Inches(1.15), cw - Inches(0.36), Inches(1.3), desc,
         size=11, color=WHITE, font="Calibri")
    badge(s, x + Inches(0.18), cy + ch - Inches(0.55), Inches(1.6), Inches(0.36), status, color)

text(s, Inches(0.7), Inches(5.55), Inches(11.9), Inches(1.0),
     "877 days indexed: Feb 2024 -> Jun 2026 (both-instrument coverage). Manifest-based reads — zips and FITS "
     "parsed directly, no pre-extraction needed.",
     size=13, color=MUTED, font="Calibri")
footer(s, 3)


# =============================================================================
# SLIDE 4 — System Architecture (4-stage pipeline)
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Architecture", "4-Stage Detection Pipeline",
             "Physics-first engine — zero training needed for core detection")

stages = [
    ("S1", "QUIET SUN", "Baseline monitoring,\nall sensors nominal", GREEN),
    ("S2", "PRE-FLARE HEATING", "SoLEXS derivative\nrising", YELLOW),
    ("S3", "FORECAST ALERT", "Sustained slope\nsteepening flagged", ORANGE),
    ("S4", "NOWCAST CONFIRMED", "HEL1OS 3-sigma spike\nconfirms (Neupert)", RED),
]
cx, cy = Inches(0.7), Inches(2.2)
cw, ch, gap = Inches(2.84), Inches(2.6), Inches(0.22)
for i, (tag, name, desc, color) in enumerate(stages):
    x = cx + i * (cw + gap)
    box(s, x, cy, cw, ch, fill=BG_CARD, line=color, line_w=1.2)
    text(s, x, cy + Inches(0.18), cw, Inches(0.8), tag, size=34, color=color, bold=True,
         align=PP_ALIGN.CENTER, font="Calibri")
    text(s, x + Inches(0.15), cy + Inches(1.05), cw - Inches(0.3), Inches(0.5), name,
         size=13, color=WHITE, bold=True, align=PP_ALIGN.CENTER, font="Calibri")
    text(s, x + Inches(0.15), cy + Inches(1.55), cw - Inches(0.3), Inches(0.9), desc,
         size=10.5, color=MUTED, align=PP_ALIGN.CENTER, font="Calibri")
    if i < 3:
        arrow = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW,
                                     x + cw + Inches(0.02), cy + ch/2 - Inches(0.1),
                                     Inches(0.18), Inches(0.2))
        arrow.fill.solid(); arrow.fill.fore_color.rgb = MUTED; arrow.line.fill.background()
        arrow.shadow.inherit = False

text(s, Inches(0.7), Inches(5.2), Inches(11.9), Inches(0.9),
     "Two independent instruments must agree (Neupert Effect) before a NOWCAST fires — this is what keeps "
     "false alarms low without needing AI for the core detection.",
     size=13, color=WHITE, italic=True, font="Calibri")
footer(s, 4)


# =============================================================================
# SLIDE 5 — PROVEN: Physics Detector vs GOES catalog
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Proven Results · 1 / 3", "Physics Detector — Benchmarked vs 8,149 Real GOES Flares",
             "877-day full-archive scan (Feb 2024 -> Jun 2026), 6-worker parallel processing")

stats = [
    ("877", "Days Scanned", GREEN),
    ("175", "Flares Detected", BLUE),
    ("0.328", "False Alarms / 24h", ORANGE),
    ("95.9%", "Precision", GREEN),
    ("51%", "X-class Recall", YELLOW),
]
cx, cy = Inches(0.7), Inches(2.05)
cw, ch, gap = Inches(2.18), Inches(1.3), Inches(0.18)
for i, (val, lab, color) in enumerate(stats):
    x = cx + i * (cw + gap)
    stat_card(s, x, cy, cw, ch, val, lab, color)

text(s, Inches(0.7), Inches(3.7), Inches(11.9), Inches(0.4),
     "What this means", size=15, color=WHITE, bold=True, font="Calibri")
bullets(s, Inches(0.7), Inches(4.15), Inches(11.9), Inches(2.0), [
    "Target was under 1 false alarm per 24h — achieved 0.328, well within budget.",
    "Detector is deliberately conservative: high precision (95.9%) over raw recall.",
    "Strongest on the flares that matter operationally most — large, high-impact events.",
], size=14, color=WHITE)
footer(s, 5)


# =============================================================================
# SLIDE 6 — PROVEN: ML Models
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Proven Results · 2 / 3", "Three Trained ML Models (XGBoost)",
             "Chronological train/test split — no data leakage")

models = [
    ("MODEL 1", "SoLEXS Flare Detector", BLUE, [
        ("AUC", "0.935"), ("Recall X", "85.7%"), ("Recall C", "88.3%"), ("Top feature", "peak_over_base"),
    ], "Catches small C/M flares the hard-X-ray\nphysics engine misses."),
    ("MODEL 2", "Dual-Instrument (SoLEXS+HEL1OS)", RED, [
        ("AUC", "0.854"), ("Precision", "98.6%"), ("Recall", "83.3%"), ("FA rate", "~1.4%"),
    ], "Physics features + Neupert flag.\nNear-zero false alarms."),
    ("MODEL 3", "24h Flare Forecaster", YELLOW, [
        ("AUC", "0.754"), ("vs Poisson", "+67.0%"), ("vs Climatology", "+31.9%"), ("Top feature", "nM_48h"),
    ], "Catalog activity rate -> P(M+ in 24h).\nStatistical, not physics-based."),
]
cx, cy = Inches(0.7), Inches(2.0)
cw, ch, gap = Inches(3.84), Inches(4.4), Inches(0.22)
for i, (tag, name, color, metrics, note) in enumerate(models):
    x = cx + i * (cw + gap)
    box(s, x, cy, cw, ch, fill=BG_CARD, line=color, line_w=1.2)
    box(s, x, cy, cw, Inches(0.65), fill=color)
    text(s, x + Inches(0.15), cy + Inches(0.05), cw - Inches(0.3), Inches(0.3), tag,
         size=11, color=RGBColor(0xff,0xff,0xff), bold=True, font="Calibri")
    text(s, x + Inches(0.15), cy + Inches(0.32), cw - Inches(0.3), Inches(0.3), name,
         size=11.5, color=RGBColor(0xff,0xff,0xff), bold=True, font="Calibri")
    my = cy + Inches(0.85)
    for label, val in metrics:
        text(s, x + Inches(0.2), my, cw - Inches(2.0), Inches(0.35), label, size=11.5, color=MUTED, font="Calibri")
        text(s, x + cw - Inches(1.7), my, Inches(1.5), Inches(0.35), val, size=12.5, color=color,
             bold=True, align=PP_ALIGN.RIGHT, font="Calibri")
        my += Inches(0.42)
    box(s, x + Inches(0.15), cy + ch - Inches(1.15), cw - Inches(0.3), Inches(0.95), fill=BG_DARK, line=BORDER, line_w=0.5)
    text(s, x + Inches(0.27), cy + ch - Inches(1.05), cw - Inches(0.54), Inches(0.85), note,
         size=10, color=MUTED, font="Calibri")
footer(s, 6)


# =============================================================================
# SLIDE 7 — HONEST LIMITATIONS
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Stated Honestly", "What SHIELD Does NOT Do (Yet)",
             "Transparency over hype — this is what separates a real system from a demo", color=RED)

box(s, Inches(0.7), Inches(2.0), Inches(11.9), Inches(1.15), fill=BG_CARD, line=RED, line_w=1.2)
text(s, Inches(1.0), Inches(2.18), Inches(11.3), Inches(0.4),
     "Flares are impulsive — X-rays cannot forecast minutes ahead", size=15, color=RED, bold=True, font="Calibri")
text(s, Inches(1.0), Inches(2.6), Inches(11.3), Inches(0.45),
     "Proven this session: SoLEXS flux AND derived temperature rise within 0-36 seconds of flare onset across "
     "all tested events. The X-ray rise IS the flare, not a precursor to it.",
     size=12, color=WHITE, font="Calibri")

bullets(s, Inches(0.7), Inches(3.35), Inches(11.9), Inches(3.2), [
    "Current \"forecast\" (Model 3) is climatological — recent flare-rate statistics, not a physics prediction of a specific flare.",
    "Counts -> GOES-flux calibration is still approximate (R-squared ~ 0.31); flare class carries this caveat.",
    "Severity and forecaster accuracy are near the current data ceiling — gains need more flare events, not more training epochs.",
    "Geomagnetic storm / radiation-belt impacts need particle (ASPEX) and CME (VELC) data — not available from SoLEXS/HEL1OS.",
    "SUIT tested on one sparse 2-day campaign batch — pipeline works, but data too sparse yet to prove a pre-flare UV trend.",
], size=13.5, color=WHITE, accent=RED)
footer(s, 7)


# =============================================================================
# SLIDE 8 — Impact Assessment
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Output", "Impact Assessment & Safety Advisories",
             "Every confirmed flare maps to NOAA-scale advisories across 6 domains")

mini_table(s, Inches(0.7), Inches(2.05),
           ["Scale", "Trigger", "Status in SHIELD"],
           [
               ["R1-R5  Radio Blackout", "X-ray flux > M1.0", "ACTIVE — direct from soft X-ray"],
               ["S1-S5  Radiation Storm", "Proton flux > 10 pfu", "ROADMAP — needs ASPEX particle data"],
               ["G1-G5  Geomagnetic Storm", "Kp index > 5", "ROADMAP — needs VELC CME tracking"],
           ],
           col_w=[3.6, 3.6, 4.7], row_h=0.5, font_size=12)

text(s, Inches(0.7), Inches(4.4), Inches(11.9), Inches(0.4),
     "Six live impact domains today:", size=14, color=WHITE, bold=True, font="Calibri")
domains2 = ["Radio Blackout", "GPS / Navigation", "Aviation", "Satellites", "Astronaut Radiation", "Power Grid"]
dx = Inches(0.7)
for i, d in enumerate(domains2):
    w = Inches(1.85)
    badge(s, dx, Inches(4.9), w, Inches(0.45), d, GREEN)
    dx += w + Inches(0.16)

text(s, Inches(0.7), Inches(5.7), Inches(11.9), Inches(0.8),
     "Radio / GPS / aviation effects follow directly from soft X-ray flux — operational today. Radiation and "
     "geomagnetic effects are estimates pending ASPEX + VELC data (roadmap).",
     size=12, color=MUTED, italic=True, font="Calibri")
footer(s, 8)


# =============================================================================
# SLIDE 9 — ROADMAP: SUIT (Phase 1)
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Roadmap · Phase 1", "SUIT — The Path to True Advance Forecasting",
             "Active-region UV build-up is the only Aditya-L1 signal that precedes a flare", color=ORANGE)

box(s, Inches(0.7), Inches(2.0), Inches(11.9), Inches(1.3), fill=BG_CARD, line=ORANGE, line_w=1.2)
text(s, Inches(1.0), Inches(2.18), Inches(11.3), Inches(0.4),
     "Why SUIT matters", size=15, color=ORANGE, bold=True, font="Calibri")
text(s, Inches(1.0), Inches(2.6), Inches(11.3), Inches(0.65),
     "X-rays only flash at flare onset — they carry no precursor signal. UV images of an active region can "
     "show it building up beforehand. SUIT is the only Aditya-L1 instrument that can give genuine hours-ahead "
     "warning instead of seconds-ahead confirmation.",
     size=12, color=WHITE, font="Calibri")

text(s, Inches(0.7), Inches(3.55), Inches(11.9), Inches(0.4),
     "Status", size=14, color=WHITE, bold=True, font="Calibri")
bullets(s, Inches(0.7), Inches(4.0), Inches(11.9), Inches(1.3), [
    "Pipeline built (core/suit.py) — reads FITS/zip, extracts active-region brightness + area features.",
    "Tested on 1 batch (2 sparse campaign days, ~10,000 files) — SUIT shoots in short ~2h windows, not continuously.",
    "Result: pipeline works end-to-end, but coverage too sparse yet to prove a pre-flare brightening trend.",
], size=13, color=WHITE, accent=ORANGE)

text(s, Inches(0.7), Inches(5.35), Inches(11.9), Inches(0.4),
     "Next: download dense SUIT coverage around known major flares", size=14, color=WHITE, bold=True, font="Calibri")
mini_table(s, Inches(0.7), Inches(5.8),
           ["Priority Window", "Target Event", "Why"],
           [
               ["2024-05-06 to 2024-05-15", "X9.0, X8.7 storm", "Biggest cluster — 9 active days, 1 AR"],
               ["2026-02-01 to 2026-02-05", "X8.1, X4.2 cluster", "Most recent dense X-class sequence"],
               ["2024-10-01 to 2024-10-09", "Twin X9.0 events", "Same AR, 8 days apart"],
           ],
           col_w=[3.4, 3.0, 5.5], row_h=0.42, font_size=11)
footer(s, 9)


# =============================================================================
# SLIDE 10 — ROADMAP: VELC + Production (Phase 2 & 3)
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Roadmap · Phase 2 & 3", "VELC Impact Layer + Production Hardening",
             "Completing the hazard chain and shipping what's already built", color=PURPLE)

# Phase 2 card
box(s, Inches(0.7), Inches(2.0), Inches(5.75), Inches(4.5), fill=BG_CARD, line=PURPLE, line_w=1.2)
text(s, Inches(1.0), Inches(2.2), Inches(5.2), Inches(0.4), "PHASE 2 — VELC (Coronagraph)",
     size=15, color=PURPLE, bold=True, font="Calibri")
bullets(s, Inches(1.0), Inches(2.75), Inches(5.2), Inches(3.5), [
    "Detect CMEs leaving the Sun via coronagraph imaging.",
    "Feed CME speed/direction into geomagnetic (G-scale) storm prediction.",
    "Unlocks power-grid GIC alerting — currently roadmap-only.",
    "Unlocks 1-3 day Earth-arrival impact window for CME-driven storms.",
    "Combined with ASPEX particle data -> radiation storm (S-scale) alerts.",
], size=12.5, color=WHITE, accent=PURPLE, gap=10)

# Phase 3 card
box(s, Inches(6.85), Inches(2.0), Inches(5.75), Inches(4.5), fill=BG_CARD, line=GREEN, line_w=1.2)
text(s, Inches(7.15), Inches(2.2), Inches(5.2), Inches(0.4), "PHASE 3 — Production Hardening",
     size=15, color=GREEN, bold=True, font="Calibri")
bullets(s, Inches(7.15), Inches(2.75), Inches(5.2), Inches(3.5), [
    "Wire trained ML models into the live alert pipeline (currently trained, not yet connected).",
    "Improve counts -> GOES-flux calibration (current R-squared ~ 0.31).",
    "Live dashboard already built: Next.js, real pipeline JSON, live UTC/IST clock, live chart playback.",
    "Expand training data — more flare events, not more training epochs (proven lesson from this project).",
], size=12.5, color=WHITE, accent=GREEN, gap=10)
footer(s, 10)


# =============================================================================
# SLIDE 11 — Multi-Instrument Vision
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Vision", "The Full Hazard Chain — All Four Instruments",
             "From \"a region is building\" to \"a storm reaches Earth\"")

mini_table(s, Inches(0.7), Inches(2.1),
           ["Instrument", "Sees", "Answers", "Status"],
           [
               ["SUIT (UV)", "Active region building", "Is a flare coming? (forecast)", "TESTING"],
               ["SoLEXS (soft X-ray)", "Thermal flare emission", "Flare now + what class?", "BUILT"],
               ["HEL1OS (hard X-ray)", "Impulsive burst", "Confirm it (Neupert), energy?", "BUILT"],
               ["VELC (coronagraph)", "CME leaving the Sun", "Storm heading to Earth?", "ROADMAP"],
           ],
           col_w=[2.7, 3.0, 4.0, 2.2], row_h=0.55, font_size=12)

text(s, Inches(0.7), Inches(4.85), Inches(11.9), Inches(1.5),
     "The working core (SoLEXS + HEL1OS) owns the middle of this chain — detection, classification, and the "
     "minutes-scale radio/GPS impact, proven on real data today. SUIT extends the front (forecast); VELC "
     "extends the back (CME + 1-3 day geomagnetic impact). The two-instrument core is the complete, honest "
     "answer to Challenge #15 today — the four-instrument system is the roadmap.",
     size=13, color=WHITE, font="Calibri")
footer(s, 11)


# =============================================================================
# SLIDE 12 — Tech Stack
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Implementation", "Technology Stack",
             "Real pipeline end to end — ingestion to live dashboard")

stacks = [
    ("Ingestion", ["pandas", "astropy", "zipfile/io — FITS/ZIP read without extraction", "merge_asof time alignment"], BLUE),
    ("Features & Physics", ["numpy.gradient (derivatives)", "scipy (rolling stats, sigma scoring)", "Neupert cross-validation"], GREEN),
    ("Machine Learning", ["XGBoost (production)", "PyTorch LSTM (compared, lost)", "scikit-learn (metrics only)"], ORANGE),
    ("Dashboard", ["Next.js 16 + React 19 + TypeScript", "Plotly.js — live light curves", "Live UTC/IST clock + playback"], PURPLE),
]
cx, cy = Inches(0.7), Inches(2.05)
cw, ch, gap = Inches(2.84), Inches(4.4), Inches(0.22)
for i, (title, items, color) in enumerate(stacks):
    x = cx + i * (cw + gap)
    box(s, x, cy, cw, ch, fill=BG_CARD, line=color, line_w=1.2)
    box(s, x, cy, cw, Inches(0.55), fill=color)
    text(s, x, cy, cw, Inches(0.55), title, size=12.5, color=RGBColor(0xff,0xff,0xff), bold=True,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, font="Calibri")
    bullets(s, x + Inches(0.18), cy + Inches(0.75), cw - Inches(0.36), ch - Inches(0.95), items,
            size=10.5, color=WHITE, accent=color, gap=10)
text(s, Inches(0.7), Inches(6.65), Inches(11.9), Inches(0.4),
     "Data source: ISRO PRADAN — SoLEXS, HEL1OS (+ ASPEX, MAG on roadmap)", size=11, color=MUTED, font="Calibri")
footer(s, 12)


# =============================================================================
# SLIDE 13 — Conclusion
# =============================================================================
s = new_slide()
set_bg(s)
kicker_title(s, "Summary", "SHIELD Today — and What's Next",
             "A validated core, with a clearly-scoped, honest roadmap")

box(s, Inches(0.7), Inches(2.0), Inches(5.75), Inches(4.3), fill=BG_CARD, line=GREEN, line_w=1.4)
text(s, Inches(1.0), Inches(2.2), Inches(5.2), Inches(0.4), "WORKING TODAY", size=15, color=GREEN, bold=True, font="Calibri")
bullets(s, Inches(1.0), Inches(2.75), Inches(5.2), Inches(3.4), [
    "Real-time flare detection + classification (95.9% precision, 0.33 FA/24h).",
    "3 trained ML models — detector AUC 0.935, dual-instrument AUC 0.854, forecaster AUC 0.754.",
    "877-day full archive validated against 8,149 real GOES flares.",
    "Live dashboard with real-time clock + live chart playback.",
    "6-domain impact assessment with safety advisories.",
], size=12.5, color=WHITE, accent=GREEN, gap=10)

box(s, Inches(6.85), Inches(2.0), Inches(5.75), Inches(4.3), fill=BG_CARD, line=ORANGE, line_w=1.4)
text(s, Inches(7.15), Inches(2.2), Inches(5.2), Inches(0.4), "ROADMAP", size=15, color=ORANGE, bold=True, font="Calibri")
bullets(s, Inches(7.15), Inches(2.75), Inches(5.2), Inches(3.4), [
    "SUIT: dense pre-flare UV coverage -> true hours-ahead forecasting (target AUC 0.90+).",
    "VELC: CME detection -> geomagnetic + radiation storm prediction.",
    "Wire ML models into the live alert pipeline.",
    "Improve counts-to-flux calibration (R-squared 0.31 -> higher).",
    "Satellite digital-twin protection + Earth-impact module (grid, GPS, aviation).",
], size=12.5, color=WHITE, accent=ORANGE, gap=10)
footer(s, 13)


# =============================================================================
# SLIDE 14 — Thank you
# =============================================================================
s = new_slide()
set_bg(s)
text(s, Inches(0), Inches(2.7), SLIDE_W, Inches(0.9), "Thank You",
     size=48, color=ORANGE, bold=True, align=PP_ALIGN.CENTER, font="Calibri")
text(s, Inches(0), Inches(3.6), SLIDE_W, Inches(0.4),
     "S.H.I.E.L.D. — Team Suryastra", size=16, color=WHITE, align=PP_ALIGN.CENTER, font="Calibri")
text(s, Inches(0), Inches(4.05), SLIDE_W, Inches(0.4),
     "Bharatiya Antariksh Hackathon 2026 · Challenge #15", size=12, color=MUTED,
     align=PP_ALIGN.CENTER, font="Calibri")
text(s, Inches(0), Inches(5.4), SLIDE_W, Inches(0.4),
     "Built for the Sun. Built for India.", size=12, italic=True, color=MUTED,
     align=PP_ALIGN.CENTER, font="Calibri")


# ---------------------------------------------------------------------------
OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(OUT)
print(f"PPTX generated: {OUT}")
print(f"Slides: {len(prs.slides._sldIdLst)}")
