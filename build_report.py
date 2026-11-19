# =============================================================================
# S.H.I.E.L.D. — Report generator (4-6 page PDF via fpdf2)
# Produces outputs/SHIELD_Report.pdf for the Bharatiya Antariksh Hackathon 2026
# submission. All numbers are the real validated results from this project.
# =============================================================================
from pathlib import Path
from fpdf import FPDF

OUT = Path(__file__).resolve().parent / "outputs" / "SHIELD_Report.pdf"

NAVY = (15, 30, 70)
BLUE = (30, 80, 160)
GREY = (90, 90, 90)
LIGHT = (235, 240, 248)


def clean(s: str) -> str:
    # keep PDF core-font (latin-1) safe
    return (s.replace("→", "->").replace("–", "-").replace("—", "-")
             .replace("’", "'").replace("“", '"').replace("”", '"')
             .replace("≥", ">=").replace("≤", "<=").replace("±", "+/-")
             .replace("×", "x").replace("≈", "~"))


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, "S.H.I.E.L.D. - Solar Flare Detection & Nowcasting | Team Suryastra", align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")


def h1(pdf, t):
    pdf.ln(2); pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(*NAVY)
    pdf.multi_cell(0, 7, clean(t)); pdf.ln(1)


def h2(pdf, t):
    pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(*BLUE)
    pdf.multi_cell(0, 6, clean(t)); pdf.ln(0.5)


def body(pdf, t):
    pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "", 10); pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 5, clean(t)); pdf.ln(1.5)


def bullets(pdf, items):
    pdf.set_font("Helvetica", "", 10); pdf.set_text_color(20, 20, 20)
    for it in items:
        pdf.set_x(pdf.l_margin); pdf.cell(5)
        pdf.multi_cell(0, 5, clean("- " + it))
    pdf.ln(1.5)


def table(pdf, headers, rows, widths):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 9); pdf.set_fill_color(*NAVY); pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, clean(h), border=0, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(20, 20, 20)
    for i, row in enumerate(rows):
        fill = i % 2 == 0
        pdf.set_fill_color(*LIGHT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(pdf.l_margin)
        for c, w in zip(row, widths):
            pdf.cell(w, 6.5, clean(str(c)), border=0, align="C", fill=fill)
        pdf.ln()
    pdf.ln(2.5)


pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=16)
pdf.add_page()

# ---- Title block ----
pdf.set_fill_color(*NAVY); pdf.rect(0, 0, 210, 38, "F")
pdf.set_y(8); pdf.set_font("Helvetica", "B", 22); pdf.set_text_color(255, 255, 255)
pdf.cell(0, 10, "S.H.I.E.L.D.", align="C"); pdf.ln(9)
pdf.set_font("Helvetica", "", 10.5)
pdf.cell(0, 6, "Solar Hazard Interception & Extra-orbital Logistics Dashboard", align="C")
pdf.ln(16)
pdf.set_text_color(*GREY); pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 5, "Bharatiya Antariksh Hackathon 2026  |  Challenge #15  |  Team Suryastra", align="C"); pdf.ln(5)
pdf.cell(0, 5, "Real-time Solar Flare Detection, Classification & Impact Assessment from Aditya-L1", align="C"); pdf.ln(10)

# ---- Executive summary ----
h1(pdf, "Executive Summary")
body(pdf, "SHIELD is an operational pipeline that detects, classifies, and assesses the impact of "
          "solar flares using real telemetry from ISRO's Aditya-L1 mission - the SoLEXS (soft X-ray) "
          "and HEL1OS (hard X-ray) payloads. It combines a zero-training physics engine (the Neupert "
          "effect and adaptive sigma-thresholding) with supervised machine-learning models trained on "
          "a year+ of mission data and validated against 8,215 official NOAA/GOES flares. On held-out "
          "data the system reaches 86% detection precision at under 1 false alarm per 24 hours, an ML "
          "detector ROC-AUC of 0.935, and an M+/24h flare-probability forecaster with ROC-AUC 0.75. "
          "Every result below is measured on real data, and the report is explicit about what the "
          "physics does and does not allow.")

# ---- 1 Problem ----
h1(pdf, "1. Problem Statement & Objective")
body(pdf, "Solar flares release X-rays that reach Earth in ~8 minutes, disrupting HF radio, GNSS/GPS, "
          "aviation communications and satellite operations. The objective is an end-to-end system that, "
          "from Aditya-L1 X-ray telemetry, (a) detects a flare in real time, (b) classifies its severity "
          "(GOES B/C/M/X), (c) measures its physical properties, and (d) issues domain-specific impact "
          "advisories - while honestly characterising forecasting limits.")

# ---- 2 Data ----
h1(pdf, "2. Data Sources")
bullets(pdf, [
    "SoLEXS L1 (2-22 keV): 750 daily files - soft X-ray light curves + time-resolved PHA spectra (1 s cadence).",
    "HEL1OS L1 (8-150 keV): 2,284 files - per-detector (CZT1/2, CdTe1/2) band light curves, spectra, event lists.",
    "Coverage: Nov 2023 - Jun 2026; both instruments overlap Feb 2024 onward (292 days in 2024).",
    "Validation catalog: 8,215 official NOAA/SWPC GOES flares (C 6,384, M 1,320, X 83, B 427) via the HEK service.",
])
body(pdf, "An out-of-core ingestion layer (filename time-manifest + per-window pruning) scales the pipeline "
          "from megabytes to the full multi-year, multi-gigabyte archive without exhausting memory.")

# ---- 3 Architecture ----
h1(pdf, "3. System Architecture")
body(pdf, "PRADAN data -> Parsing -> Time synchronisation -> Noise removal -> Quiet-Sun baseline -> "
          "Thermal & non-thermal feature extraction -> Neupert physics engine -> Pre-flare detection -> "
          "Forecast -> Impulsive (nowcast) detection -> Flare classification -> Impact assessment -> "
          "Safety advisories -> Dashboard.")
bullets(pdf, [
    "Layer 1 - Physics engine (zero training): Neupert effect (hard X-ray ~ d/dt soft X-ray) + adaptive N-sigma.",
    "Spectral analysis: plasma temperature (filter band-ratio), emission measure, power-law spectral index, dead-time correction.",
    "Layer 2 - Machine learning (XGBoost): flare detector, severity classifier, probability forecaster.",
    "Impact engine: NOAA R-S-G scale mapping to radio, GPS, aviation, satellite, radiation and power-grid advisories.",
])

# ---- 4 Methodology ----
h1(pdf, "4. Methodology")
h2(pdf, "4.1 Physics engine (deterministic)")
body(pdf, "The soft X-ray fractional growth rate (dF/dt)/F flags pre-flare heating; an adaptive sigma "
          "threshold on HEL1OS confirms the impulsive burst; the Neupert relation cross-checks the two so a "
          "flare is only confirmed when both instruments agree, which suppresses single-instrument false alarms.")
h2(pdf, "4.2 Machine learning (trained on real data, honest validation)")
body(pdf, "All ML uses chronological or stratified splits (no time leakage). Three models were trained: a "
          "soft-X-ray flare DETECTOR (catches small C/M flares the hard-X-ray engine misses), a severity "
          "CLASSIFIER (C/M/X), and a probability FORECASTER (M+ flare within 24 h) using recent activity features.")

# ---- 5 Results ----
pdf.add_page()
h1(pdf, "5. Results & Validation")
h2(pdf, "5.1 Physics detector vs 8,215 GOES flares (938-day scan)")
table(pdf, ["Metric", "Result"], [
    ["Precision (detections that are real flares)", "95.9%"],
    ["False-alarm rate", "0.33 / 24 h"],
    ["X-class recall", "55%"],
    ["Mean detection across archive", "169 flares, 938 days"],
], [120, 60])

h2(pdf, "5.2 Machine-learning models")
table(pdf, ["Model", "Task", "Key metric"], [
    ["Detector (XGBoost)", "Catch flares incl. C/M", "ROC-AUC 0.935"],
    ["Detector (operating point)", "thr 0.85 + event de-dup", "Precision 86%, 0.79 FA/24h"],
    ["Detector recall", "per-event (C / M / X)", "57% / 41% / 41%"],
    ["Severity classifier", "Classify C / M / X", "86% (5-fold CV)"],
    ["Forecaster", "P(M+ flare in 24 h)", "ROC-AUC 0.75"],
    ["Forecaster skill", "vs Poisson baseline", "+0.67 Brier skill"],
], [55, 70, 55])
body(pdf, "The ML detector raises small-flare recall dramatically over the hard-X-ray physics detector "
          "(C-class 0.1% -> up to 88% at window level), confirming that soft X-ray is the correct band for "
          "GOES-style flare detection. The forecaster - which had negative skill on an early 37-day sample - "
          "achieves genuine positive skill once trained on the full year+, demonstrating the value of data scale.")

h2(pdf, "5.3 Physical measurements")
bullets(pdf, [
    "Plasma temperature measured per flare: ~2-8 keV (24-93 million K) via the soft-X-ray band-ratio method.",
    "Non-thermal power-law spectral index recovered per flare (~2.7-3.9) from HEL1OS energy bands.",
    "Per-flare features (38 columns) exported for every detected event; Tier-0 24 h activity history computed.",
])

# ---- 6 Impact ----
h1(pdf, "6. Impact Assessment & Safety Advisories")
body(pdf, "Each confirmed flare is mapped through the NOAA radio-blackout (R) scale to concrete, domain-specific "
          "advisories: HF radio blackout, GPS/GNSS degradation, aviation HF loss, satellite single-event-upset "
          "risk, astronaut radiation watch and power-grid alerting. Radio/GPS/aviation follow directly from soft "
          "X-ray flux; radiation and geomagnetic effects are flagged as estimates pending particle (ASPEX) and "
          "magnetic data.")

# ---- 7 Limitations ----
h1(pdf, "7. Limitations (stated honestly)")
bullets(pdf, [
    "Advance forecasting of individual flares is not possible from X-rays alone: across all observed flares the soft X-ray and hard X-ray rise within seconds of each other (impulsive), so there is no minutes-ahead precursor.",
    "Counts-to-flux calibration for absolute GOES class is still approximate (R^2 ~ 0.31).",
    "Severity and forecaster accuracy are at the current data ceiling; gains require more flare events, not more training.",
    "Geomagnetic/radiation-storm impacts require particle and CME data not carried by SoLEXS/HEL1OS.",
])

# ---- 8 Roadmap ----
h1(pdf, "8. Roadmap - SHIELD 2.0")
bullets(pdf, [
    "SUIT (UV imaging) for active-region-based advance forecasting - the only Aditya-L1 path to true days-ahead prediction.",
    "VELC coronagraph for CME detection -> geomagnetic-storm and power-grid impact.",
    "ASPEX particle data -> calibrated radiation-storm (S-scale) advisories.",
    "Live operational deployment of the dashboard with continuous PRADAN ingestion.",
])

# ---- 9 Conclusion ----
h1(pdf, "9. Conclusion")
body(pdf, "SHIELD delivers a complete, validated solar-flare detection, classification and impact-assessment "
          "system built entirely on real Aditya-L1 SoLEXS and HEL1OS data and benchmarked against 8,215 official "
          "GOES flares. It achieves high precision (86-96%) at under one false alarm per day, measures plasma "
          "physics per flare, and issues actionable advisories - with an honest, clearly-scoped roadmap to advance "
          "forecasting via SUIT. The result is a credible operational nowcasting core and a defensible scientific "
          "foundation for an Indian space-weather early-warning capability.")

OUT.parent.mkdir(parents=True, exist_ok=True)
pdf.output(str(OUT))
print("wrote", OUT)
