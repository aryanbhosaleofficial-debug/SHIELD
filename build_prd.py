# =============================================================================
# S.H.I.E.L.D. — Unified PRD generator (PRD v4.0) -> outputs/SHIELD_PRD_v4.pdf
#
# Combines the two earlier PRDs into ONE honest document:
#   * Core PRD v1  (SoLEXS + HEL1OS, physics-first)  -> the proven deliverable
#   * PRD v3       (grand vision, 4 AI layers)        -> roadmap, clearly labelled
# All headline numbers are the REAL validated results from this project's
# output files (benchmark_summary, detector_results, tuning_results, etc.).
#
# Honest forecasting framing: X-rays give onset DETECTION + CLASSIFICATION now;
# true hours/days-ahead forecasting needs SUIT UV imaging (roadmap, being tested).
# No fixed "8-15 minute warning gap" is claimed -- our own data showed flares
# are impulsive (soft + hard X-ray rise within seconds).
# =============================================================================
from pathlib import Path
from fpdf import FPDF

OUT = Path(__file__).resolve().parent / "outputs" / "SHIELD_PRD_v4.pdf"

NAVY = (15, 30, 70)
BLUE = (30, 80, 160)
ORANGE = (200, 80, 20)
GREY = (90, 90, 90)
LIGHT = (235, 240, 248)
GREEN = (20, 110, 60)


def clean(s: str) -> str:
    return (s.replace("→", "->").replace("–", "-").replace("—", "-")
             .replace("’", "'").replace("“", '"').replace("”", '"')
             .replace("≥", ">=").replace("≤", "<=").replace("±", "+/-")
             .replace("×", "x").replace("≈", "~").replace("µ", "u")
             .replace("°", "deg").replace("∆", "d").replace("₹", "Rs "))


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, "S.H.I.E.L.D. PRD v4.0  |  Team Suryastra  |  Bharatiya Antariksh Hackathon 2026  |  Challenge #15", align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, f"Confidential - Team Suryastra  |  Page {self.page_no()}", align="C")


def section(pdf, t):
    pdf.ln(1)
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "  " + clean(t), fill=True)
    pdf.ln(11)


def h2(pdf, t):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(*BLUE)
    pdf.multi_cell(0, 6, clean(t))
    pdf.ln(0.5)


def body(pdf, t):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 9.7)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 5, clean(t))
    pdf.ln(1.5)


def callout(pdf, label, t, color=ORANGE):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 5, clean(label))
    pdf.set_font("Helvetica", "", 9.7)
    pdf.set_text_color(40, 40, 40)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, clean(t))
    pdf.ln(1.5)


def bullets(pdf, items):
    pdf.set_font("Helvetica", "", 9.7)
    pdf.set_text_color(20, 20, 20)
    for it in items:
        pdf.set_x(pdf.l_margin)
        pdf.cell(4)
        pdf.multi_cell(0, 5, clean("- " + it))
    pdf.ln(1.5)


def table(pdf, headers, rows, widths, align="C"):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 8.6)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6.6, clean(h), border=0, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(20, 20, 20)
    for i, row in enumerate(rows):
        fill = i % 2 == 0
        pdf.set_fill_color(*LIGHT)
        pdf.set_font("Helvetica", "", 8.6)
        pdf.set_x(pdf.l_margin)
        # measure height for wrapping first cell-free simple version: single line
        for j, (c, w) in enumerate(zip(row, widths)):
            a = "L" if (align == "L" and j == len(row) - 1) else "C"
            pdf.cell(w, 6.2, clean(str(c)), border=0, align=a, fill=fill)
        pdf.ln()
    pdf.ln(2.5)


pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=16)
pdf.add_page()

# ============================ TITLE PAGE ============================
pdf.set_fill_color(*NAVY)
pdf.rect(0, 0, 210, 46, "F")
pdf.set_y(11)
pdf.set_font("Helvetica", "B", 26)
pdf.set_text_color(255, 255, 255)
pdf.cell(0, 12, "S.H.I.E.L.D.", align="C")
pdf.ln(12)
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(255, 210, 150)
pdf.cell(0, 6, "Solar Hazard Interception & Extra-orbital Logistics Dashboard", align="C")
pdf.ln(22)

pdf.set_text_color(*NAVY)
pdf.set_font("Helvetica", "B", 13)
pdf.cell(0, 8, "Product Requirements Document - v4.0 (Unified)", align="C")
pdf.ln(8)
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(*GREY)
pdf.cell(0, 6, "Real-time Solar Flare Detection, Classification, Nowcasting & Impact Assessment from Aditya-L1", align="C")
pdf.ln(12)

meta = [
    ("HACKATHON", "Bharatiya Antariksh Hackathon 2026  -  ISRO / Hack2Skill"),
    ("CHALLENGE", "#15 - Solar Flare Forecasting & Nowcasting (Aditya-L1)"),
    ("TEAM", "Team Suryastra"),
    ("CORE DATA", "SoLEXS (soft X-ray) + HEL1OS (hard X-ray) - PRADAN portal"),
    ("VALIDATION", "8,149 official NOAA/GOES flares over a 938-day archive scan"),
    ("CORE STATUS", "BUILT & VALIDATED on real telemetry (detect / classify / nowcast)"),
    ("EXTENSIONS", "SUIT forecasting, VELC CME, satellite protection, Earth impact (roadmap)"),
    ("VERSION", "PRD v4.0  -  supersedes Core PRD v1 and PRD v3.0"),
]
lblw, valw = 42, 138
for i, (k, v) in enumerate(meta):
    pdf.set_x((210 - (lblw + valw)) / 2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(lblw, 7, "  " + k, fill=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_fill_color(*LIGHT)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(valw, 7, "  " + clean(v), fill=True)
    pdf.ln(7)

pdf.ln(8)
pdf.set_font("Helvetica", "BI", 11)
pdf.set_text_color(*BLUE)
pdf.cell(0, 6, "Built for the Sun. Built for India.", align="C")

# ============================ 1. EXECUTIVE SUMMARY ============================
pdf.add_page()
section(pdf, "1.  Executive Summary")
body(pdf, "S.H.I.E.L.D. is an operational pipeline that detects, classifies and assesses the impact of solar "
          "flares using real telemetry from ISRO's Aditya-L1 mission - the SoLEXS (soft X-ray, 2-22 keV) and "
          "HEL1OS (hard X-ray, 8-150 keV) payloads from the PRADAN portal. It pairs a zero-training physics "
          "engine (the Neupert effect plus adaptive sigma-thresholding) with supervised machine-learning models "
          "trained on a year+ of mission data and validated against 8,149 official NOAA/GOES flares.")
body(pdf, "This unified PRD supersedes the earlier Core PRD v1 and PRD v3.0. It states honestly what the physics "
          "allows: Aditya-L1's X-ray instruments deliver high-quality flare DETECTION, CLASSIFICATION and "
          "real-time NOWCASTING. True hours/days-ahead FORECASTING of an individual flare is not possible from "
          "X-rays alone - it requires UV active-region imaging (SUIT), which is presented here as a tested "
          "roadmap extension rather than a finished claim.")
callout(pdf, "Headline validated results (all measured on real data):",
        "Physics detector: 95.9% precision at 0.33 false alarms / 24 h.  ML detector (XGBoost): ROC-AUC 0.935.  "
        "Severity classifier (C/M/X): 86% cross-validated accuracy.  Activity forecaster (P[M+ flare in 24 h]): "
        "ROC-AUC ~0.75 with positive skill over the climatological baseline.", color=GREEN)

# ============================ 2. PROBLEM & MANDATE ============================
section(pdf, "2.  Problem Statement & Mandate Fit")
callout(pdf, "ISRO mandate:",
        "Build an automated algorithmic pipeline that uses the combined time-series data from SoLEXS (soft "
        "X-ray) and HEL1OS (hard X-ray) to detect (nowcast) or predict (forecast) solar flares. The challenge "
        "title reads 'forecasting and/or nowcasting' - we answer both, and treat each as independently defensible.",
        color=NAVY)
body(pdf, "Solar flares release X-rays that reach Earth in ~8 minutes, disrupting HF radio, GNSS/GPS, aviation "
          "communications and satellite operations; the associated CMEs can drive geomagnetic storms that "
          "threaten power grids and astronauts. The objective is an end-to-end system that, from Aditya-L1 X-ray "
          "telemetry, detects a flare in real time, classifies its severity (GOES B/C/M/X), measures its physical "
          "properties, and issues domain-specific impact advisories - while honestly characterising its limits.")
h2(pdf, "Why it matters")
table(pdf, ["Event", "Consequence"], [
    ["1989 Quebec blackout", "G5 storm collapsed a power grid in 92 s; 6 million people lost power, zero warning."],
    ["Carrington 1859", "Strongest recorded storm; a repeat today is estimated at USD 2-3 trillion damage."],
    ["May 2024 (Gannon)", "Strongest storm of the century; X8.7 flare on 14 May, captured by Aditya-L1."],
], [40, 140], align="L")

# ============================ 3. DATA SOURCES ============================
section(pdf, "3.  Data Sources - SoLEXS & HEL1OS (PRADAN)")
body(pdf, "All flare data is sourced exclusively from ISRO PRADAN SoLEXS and HEL1OS files. External references "
          "(NOAA/GOES class labels) are used ONLY to cross-check results, never to train the physics engine. "
          "December 2023 commissioning data is excluded.")
table(pdf, ["Parameter", "SoLEXS (soft X-ray)", "HEL1OS (hard X-ray)"], [
    ["Energy range", "2-22 keV (thermal)", "8-150 keV (non-thermal)"],
    ["Cadence", "1 s during flares", "Event mode, 100% duty"],
    ["Detectors", "Pair of Si drift detectors", "CdTe (8-70 keV) + CZT (20-150 keV)"],
    ["Physics role", "Coronal plasma heating", "Accelerated-electron impulse"],
], [38, 71, 71])
h2(pdf, "Actual archive used in this project")
bullets(pdf, [
    "SoLEXS L1: ~750 daily files - light curves + time-resolved PHA spectra.",
    "HEL1OS L1: ~2,284 files - per-detector (CZT1/2, CdTe1/2) band light curves, spectra, event lists.",
    "Coverage scanned: 30 Nov 2023 - 25 Jun 2026 (938 days, processed in 1,024 chunks).",
    "Validation catalog: 8,149 GOES flares in span (C 6,321, M 1,319, X 83, B 426) via the HEK service.",
])
body(pdf, "An out-of-core ingestion layer (filename time-manifest + per-window pruning) scales the pipeline from "
          "megabytes to the full multi-year, multi-gigabyte archive without exhausting memory.")

# ============================ 4. ARCHITECTURE ============================
section(pdf, "4.  System Architecture")
body(pdf, "PRADAN data -> parsing -> time synchronisation (merge_asof) -> noise removal -> quiet-Sun baseline -> "
          "thermal & non-thermal feature extraction -> Neupert physics engine -> detection -> classification -> "
          "impact assessment -> safety advisories -> dashboard.")
table(pdf, ["Layer", "What it does", "Training"], [
    ["1 - Physics engine", "Neupert (hard ~ d/dt soft) + adaptive N-sigma", "Zero (works day one)"],
    ["Spectral analysis", "Temperature, emission measure, spectral index, dead-time", "Zero (deterministic)"],
    ["2 - Machine learning", "Detector + severity classifier + forecaster (XGBoost)", "Hours, on real data"],
    ["Impact engine", "NOAA R-S-G -> radio/GPS/aviation/sat/grid advisories", "Rule-based"],
], [40, 100, 40], align="L")
h2(pdf, "Three-scale context architecture")
table(pdf, ["Layer", "Window & job", "Update"], [
    ["Historical", "Builds activity/complexity profile, 27-day rotation", "Daily"],
    ["Situational", "Last 72 h: watches gradient trends, issues WATCH", "Hourly"],
    ["Trigger", "Last 60 min: real-time sigma + Neupert check", "Every second"],
], [38, 110, 32], align="L")

# ============================ 5. CORE ALGORITHM / PHYSICS ============================
section(pdf, "5.  Core Algorithm - Physics Engine (zero training)")
body(pdf, "The soft X-ray fractional growth rate (dF/dt)/F flags pre-flare heating; an adaptive sigma threshold "
          "on HEL1OS confirms the impulsive burst; the Neupert relation (hard X-ray flux ~ d/dt of soft X-ray "
          "flux) cross-checks the two, so a flare is confirmed only when both instruments agree - which suppresses "
          "single-instrument false alarms. This layer is deterministic calculus on real telemetry: it cannot "
          "overfit, needs no training set, and mirrors the onboard flare-trigger logic ISRO already flies.")
callout(pdf, "Honest note on lead time (measured, not asserted):",
        "The classical Neupert effect means the soft-X-ray rise and the hard-X-ray burst are essentially "
        "CONCURRENT, not separated by a fixed 8-15 minute gap. Across every flare observed in this project the "
        "two rise within seconds of each other (impulsive), and plasma temperature also rises at onset, not "
        "before. S.H.I.E.L.D. therefore does NOT claim a fixed minutes-ahead warning window for an individual "
        "flare. Its X-ray strength is automated, low-false-alarm onset DETECTION and CLASSIFICATION. Advance "
        "forecasting is addressed by the SUIT roadmap (Section 12), not over-claimed here.")

# ============================ 6. DETECTION LIFECYCLE ============================
section(pdf, "6.  Detection Lifecycle - Four Stages")
table(pdf, ["#", "Stage", "What the data shows"], [
    ["1", "QUIET SUN", "SoLEXS flat, derivative ~0; HEL1OS stable. Baseline updated. ALL CLEAR."],
    ["2", "PRE-FLARE HEATING", "SoLEXS rising, derivative steepening; HEL1OS still quiet. WATCH."],
    ["3", "ONSET / NOWCAST", "HEL1OS impulsive spike crosses N-sigma; SoLEXS near peak; Neupert confirmed."],
    ["4", "CLASSIFY + IMPACT", "GOES class + peak time issued; R-S-G impact advisories generated."],
], [8, 40, 132], align="L")
body(pdf, "Note vs earlier PRDs: we no longer frame Stage 3 as a minutes-ahead 'forecast alert' with a guaranteed "
          "gap to Stage 4. The measured reality is an impulsive onset; the system's value at this stage is "
          "instant, validated detection and classification rather than an asserted warning window.")

# ============================ 7. ML MODELS ============================
section(pdf, "7.  Machine-Learning Models (trained on real data)")
body(pdf, "All ML uses chronological or stratified splits (no time leakage). The production library is XGBoost "
          "(gradient-boosted trees); scikit-learn's tree ensembles were blocked by a local OS policy, and a "
          "PyTorch LSTM was trained for comparison but lost (see below).")
bullets(pdf, [
    "DETECTOR (soft X-ray): catches small C/M flares the hard-X-ray engine misses. Window-level ROC-AUC 0.935.",
    "SEVERITY CLASSIFIER: predicts GOES C/M/X from per-flare features. 86% cross-validated accuracy.",
    "FORECASTER: probability of an M+ flare within 24 h from recent activity features. ROC-AUC ~0.75, positive skill.",
])
callout(pdf, "Honest ML lessons (reported, not hidden):",
        "(1) Re-running training does not raise accuracy - it risks overfitting; gains need more flare events, "
        "not more epochs. (2) A fancier LSTM (ROC-AUC 0.695) LOST to XGBoost (~0.75) on the same task, because "
        "the dataset is small. (3) Spectral features did not improve severity, because GOES class is essentially "
        "soft-X-ray peak magnitude, already captured. We keep the simpler, stronger models.")

# ============================ 8. RESULTS ============================
section(pdf, "8.  Results & Validation")
h2(pdf, "8.1  Physics detector vs 8,149 GOES flares (938-day archive scan)")
table(pdf, ["Metric", "Result"], [
    ["Precision (detections that are real flares)", "95.9%  (162 / 169)"],
    ["False-alarm rate", "0.33 / 24 h"],
    ["X-class recall", "51%  (42 / 83)"],
    ["Flares detected across archive", "169 over 938 days"],
], [120, 60], align="L")
body(pdf, "The physics engine is deliberately conservative (high precision, low false alarms) and is strongest on "
          "the largest, most operationally important flares.")
h2(pdf, "8.2  Machine-learning models")
table(pdf, ["Model", "Task", "Key metric"], [
    ["Detector (XGBoost)", "Catch flares incl. small C/M", "ROC-AUC 0.935"],
    ["Detector (operating pt)", "thr 0.85 + event de-dup", "Precision 86%, 0.79 FA/24h"],
    ["Detector recall (event)", "per class C / M / X", "57% / 41% / 41%"],
    ["Severity classifier", "Classify C / M / X", "86% (5-fold CV)"],
    ["Forecaster", "P(M+ flare in 24 h)", "ROC-AUC ~0.75"],
    ["LSTM (PyTorch)", "Same forecast task", "ROC-AUC 0.695 (loses to XGBoost)"],
], [50, 70, 60], align="L")
body(pdf, "The ML detector lifts small-flare recall dramatically over the hard-X-ray physics detector (C-class "
          "from ~0.1% to up to 88% at window level), confirming soft X-ray as the correct band for GOES-style "
          "detection. The forecaster - which had negative skill on an early 37-day sample - achieves genuine "
          "positive skill once trained on the full year+, demonstrating the value of data scale.")

# ============================ 9. PHYSICAL MEASUREMENTS ============================
section(pdf, "9.  Physical Measurements (per flare)")
bullets(pdf, [
    "Plasma temperature ~2-8 keV (24-93 million K) via the soft-X-ray band-ratio method.",
    "Non-thermal power-law spectral index ~2.7-3.9 recovered from HEL1OS energy bands.",
    "Emission measure, hardness ratio, cross-correlation lag, Neupert residual and joint significance.",
    "38-column per-flare feature set exported for every detected event; Tier-0 24 h activity history computed.",
])

# ============================ 10. IMPACT ============================
section(pdf, "10.  Impact Assessment & Safety Advisories")
body(pdf, "Each confirmed flare is mapped through the NOAA radio-blackout (R) scale to concrete advisories: HF "
          "radio blackout, GPS/GNSS degradation, aviation HF loss, satellite single-event-upset risk, astronaut "
          "radiation watch and power-grid alerting.")
table(pdf, ["Scale", "Trigger", "Status in SHIELD"], [
    ["R1-R5 Radio", "X-ray flux > M1.0", "ACTIVE - direct from soft X-ray"],
    ["S1-S5 Radiation", "Proton flux > 10 pfu", "ROADMAP - needs ASPEX particles"],
    ["G1-G5 Geomagnetic", "Kp > 5", "ROADMAP - needs VELC/CME + MAG"],
], [42, 58, 80], align="L")
body(pdf, "Radio/GPS/aviation effects follow directly from soft-X-ray flux and are operational today; radiation "
          "and geomagnetic effects are flagged as estimates pending particle (ASPEX) and CME (VELC) data.")

# ============================ 11. LIMITATIONS ============================
section(pdf, "11.  Limitations (stated honestly)")
bullets(pdf, [
    "Advance forecasting of an individual flare is not possible from X-rays alone: soft and hard X-rays rise within seconds (impulsive), so there is no minutes-ahead precursor in this band.",
    "Counts-to-flux calibration for absolute GOES class is still approximate (R^2 ~ 0.31); class is reported with this caveat.",
    "Severity and forecaster accuracy are near the current data ceiling; gains require more flare events, not more training.",
    "Geomagnetic / radiation-storm impacts require particle (ASPEX) and CME (VELC) data not carried by SoLEXS/HEL1OS.",
])

# ============================ 12. ROADMAP / EXTENSIONS ============================
section(pdf, "12.  Extensions & Roadmap - SHIELD 2.0")
body(pdf, "These layers were the vision of PRD v3.0. They are retained here as a clearly-labelled roadmap on top "
          "of the validated core - ambitious, but not claimed as finished.")
table(pdf, ["Extension", "What it adds", "Status"], [
    ["SUIT (UV imaging)", "Active-region build-up -> true advance forecasting", "Being tested"],
    ["VELC (coronagraph)", "CME detection -> geomagnetic / power-grid impact", "Roadmap"],
    ["Satellite protection", "Per-satellite digital-twin attitude optimisation", "Roadmap"],
    ["Earth-impact module", "Power grid, GPS, aviation, ozone, thermosphere", "Roadmap"],
    ["Shukrayaan-1 (2028)", "Venus solar-wind feed -> two-point CME network", "Vision"],
], [44, 96, 40], align="L")
callout(pdf, "Why SUIT is the key forecasting extension:",
        "X-rays only flash at flare onset. UV images of an active region can show it building up beforehand - the "
        "precursor X-rays do not provide. SUIT is therefore the only Aditya-L1 path to genuine days-ahead "
        "forecasting. Its honest limitation: SUIT campaigns are sparse (~2 h windows, not continuous), so a fair "
        "test needs denser imaging around a known flare. Work is in progress.")

# ============================ 13. MULTI-INSTRUMENT VISION ============================
section(pdf, "13.  Multi-Instrument Vision - the Full Hazard Chain")
body(pdf, "Each Aditya-L1 instrument covers a different stage of space weather. Together they form a complete "
          "early-warning chain from 'a region is building' to 'a storm reaches Earth':")
table(pdf, ["Instrument", "Sees", "Answers", "Status"], [
    ["SUIT (UV)", "Active region building", "Is a flare coming? (forecast)", "Testing"],
    ["SoLEXS (soft X)", "Thermal flare emission", "Flare now + what class?", "BUILT"],
    ["HEL1OS (hard X)", "Impulsive burst", "Confirm it (Neupert), how energetic?", "BUILT"],
    ["VELC (coronagraph)", "CME leaving the Sun", "Storm heading to Earth?", "Roadmap"],
], [40, 44, 64, 32], align="L")
body(pdf, "The working core (SoLEXS + HEL1OS) owns the middle of this chain - detection, classification and the "
          "minutes-scale radio/GPS impact. SUIT extends the front (forecast); VELC extends the back (CME and "
          "1-3 day geomagnetic impact). The full four-instrument system is the grand vision; the two-instrument "
          "core is the complete, honest answer to Challenge #15 today.")

# ============================ 14. TECH STACK ============================
section(pdf, "14.  Technology Stack")
table(pdf, ["Layer", "Tools"], [
    ["Ingestion", "pandas, astropy, zipfile/io (FITS/ZIP without extraction; merge_asof)"],
    ["Features", "numpy.gradient, scipy (derivatives, rolling stats, sigma scoring)"],
    ["Machine learning", "XGBoost (production); PyTorch LSTM (compared); scikit-learn (metrics)"],
    ["Dashboard", "Next.js + React, Plotly (live light curves, stage indicator, alert log)"],
    ["Data source", "ISRO PRADAN - SoLEXS, HEL1OS (+ ASPEX, MAG for roadmap)"],
], [40, 140], align="L")

# ============================ 15. VALIDATION PLAN & TEAM ============================
section(pdf, "15.  Validation Plan & Team")
bullets(pdf, [
    "PRIMARY - run the full pipeline on the May 2024 X8.7 window from PRADAN and report detection + classification with measured precision and false-alarm rate.",
    "SECONDARY - cross-validate Feb 2024 X6.3 onset timing against published Aditya-L1 analysis (Roy et al. 2025).",
    "MULTI-EVENT - demonstrate robustness across the C-to-X range; target under 1 false alert per 24 h quiet period (achieved: 0.33).",
])
body(pdf, "Round 1 (1 July 2026): this PRD plus the validated results above. Round 2 (Aug 2026 finale, if "
          "shortlisted): live dashboard demo on real PRADAN data, then one high-impact extension (SUIT).")

# ============================ CONCLUSION ============================
section(pdf, "16.  Conclusion")
body(pdf, "S.H.I.E.L.D. delivers a complete, validated solar-flare detection, classification and impact-assessment "
          "system built entirely on real Aditya-L1 SoLEXS and HEL1OS data and benchmarked against 8,149 official "
          "GOES flares. It achieves high precision (86-96%) at under one false alarm per day, measures plasma "
          "physics per flare, and issues actionable advisories - with an honest, clearly-scoped roadmap (SUIT, "
          "VELC, satellite protection, Earth impact) to advance forecasting and storm-impact prediction. The "
          "result is a credible operational nowcasting core and a defensible scientific foundation for an Indian "
          "space-weather early-warning capability.")
pdf.ln(2)
pdf.set_font("Helvetica", "BI", 11)
pdf.set_text_color(*BLUE)
pdf.set_x(pdf.l_margin)
pdf.cell(0, 6, "Built for the Sun. Built for India.  -  Team Suryastra", align="C")

OUT.parent.mkdir(parents=True, exist_ok=True)
pdf.output(str(OUT))
print("wrote", OUT)
