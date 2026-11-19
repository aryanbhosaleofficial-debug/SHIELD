# =============================================================================
# S.H.I.E.L.D. — Impact Assessment & Safety Advisory Engine
# Turns a detected flare class into concrete Earth/space impacts and per-domain
# safety advisories, following NOAA's R-S-G space-weather scales (the same matrix
# described in the PRD, Section 07).
#
# HONESTY:
#   * RADIO BLACKOUT (R-scale) and GPS/aviation impacts follow DIRECTLY from the
#     soft X-ray flare class -> these are real, standard NOAA mappings.
#   * RADIATION STORM (S-scale, astronaut/satellite dose) and GEOMAGNETIC STORM
#     (G-scale, power-grid GIC) depend on PARTICLE (ASPEX) and MAGNETIC (MAG)
#     data, which the core does not yet ingest. Those are returned as
#     flare-based ESTIMATES and clearly flagged "needs ASPEX/MAG (Phase 2)".
# =============================================================================

from typing import Optional, Dict


# --- GOES flare class <-> peak soft X-ray flux (W/m^2) -----------------------

_CLASS_BASE = {'A': 1e-8, 'B': 1e-7, 'C': 1e-6, 'M': 1e-5, 'X': 1e-4}


def class_to_flux(flare_class: str) -> Optional[float]:
    """'X8.7' -> 8.7e-4 ; 'M5' -> 5e-5 ; returns None if unparseable."""
    if not flare_class:
        return None
    letter = flare_class[0].upper()
    if letter not in _CLASS_BASE:
        return None
    try:
        mult = float(flare_class[1:]) if len(flare_class) > 1 else 1.0
    except ValueError:
        mult = 1.0
    return _CLASS_BASE[letter] * mult


def r_scale(flux: float) -> int:
    """NOAA Radio-Blackout scale from peak soft X-ray flux (0 = none)."""
    if flux is None:
        return 0
    if flux >= 2e-3:   # X20+
        return 5
    if flux >= 1e-3:   # X10
        return 4
    if flux >= 1e-4:   # X1
        return 3
    if flux >= 5e-5:   # M5
        return 2
    if flux >= 1e-5:   # M1
        return 1
    return 0


# --- Per R-level descriptions (NOAA-aligned) ---------------------------------

_RADIO = {
    0: "No significant HF radio impact.",
    1: "Minor HF radio degradation on the sunlit side for ~tens of minutes.",
    2: "Limited HF radio blackout on the sunlit side; ~tens of minutes.",
    3: "Wide-area HF radio blackout on the sunlit side for ~1 hour.",
    4: "HF radio blackout across most of the sunlit side for 1-2 hours.",
    5: "Complete HF radio blackout on the entire sunlit side for several hours.",
}
_GPS = {
    0: "Nominal.",
    1: "Slight GPS/GNSS accuracy degradation on the sunlit side.",
    2: "Noticeable GPS degradation; single-frequency users affected.",
    3: "GPS accuracy degraded (metres); navigation/timing affected ~1 hour.",
    4: "Significant GPS outages and timing errors over the sunlit hemisphere.",
    5: "Severe, prolonged GPS/GNSS outages across the sunlit hemisphere.",
}
_AVIATION = {
    0: "No action.",
    1: "Polar HF comms may flutter; monitor.",
    2: "Advise crews of possible HF comms loss on polar/sunlit routes.",
    3: "Expect HF comms loss on sunlit routes; prepare SATCOM fallback.",
    4: "Reroute polar flights; HF unreliable for 1-2 hours.",
    5: "Reroute polar/high-lat flights; plan for hours of HF blackout.",
}


def assess_impact(flare_class: str, hel1os_sigma: Optional[float] = None) -> Dict:
    """
    Map a flare class to impacts + advisories across domains.

    Parameters
    ----------
    flare_class : str
        e.g. 'X8.7', 'M5.0', 'C3.2'.
    hel1os_sigma : float, optional
        Hard X-ray spike strength (proxy for how impulsive/energetic the burst
        is) — nudges the radiation-risk estimate.

    Returns
    -------
    dict with 'flare_class', 'r_scale', 'confidence', and 'domains'
    (each domain -> {level, impact, advisory, basis}).
    """
    flux = class_to_flux(flare_class)
    R = r_scale(flux)
    big = R >= 3  # X-class or stronger

    # Radiation-storm proxy: large + very impulsive bursts more likely to drive
    # solar energetic particles. Honest: real S-scale needs ASPEX proton data.
    sig = hel1os_sigma or 0.0
    rad_level = "ELEVATED" if (big and sig >= 10) else ("WATCH" if big else "LOW")

    domains = {
        'radio_blackout': {
            'level': f"R{R}" if R else "R0",
            'impact': _RADIO[R],
            'advisory': "Notify DGCA/defence; issue HF frequency-shift advisory." if R >= 3
                        else ("Monitor HF bands." if R else "No action."),
            'basis': 'soft X-ray flux (direct NOAA R-scale)',
        },
        'gps_navigation': {
            'level': f"R{R}" if R else "R0",
            'impact': _GPS[R],
            'advisory': "Warn GNSS/timing users of degraded accuracy." if R >= 3
                        else "No action.",
            'basis': 'soft X-ray flux (ionospheric response)',
        },
        'aviation': {
            'level': f"R{R}" if R else "R0",
            'impact': _AVIATION[R],
            'advisory': "Advise polar-route diversions + SATCOM fallback." if R >= 4
                        else ("Brief crews on possible HF loss." if R >= 2 else "No action."),
            'basis': 'soft X-ray flux',
        },
        'satellite': {
            'level': "HIGH" if big else ("MODERATE" if R else "LOW"),
            'impact': ("Increased single-event-upset risk; possible sensor noise; "
                       "review safe-mode posture for vulnerable LEO/GEO assets."
                       if big else "Low risk to spacecraft electronics."),
            'advisory': ("Prepare safe-mode / attitude actions for exposed satellites."
                         if big else "No action."),
            'basis': 'flare-class estimate (full risk needs ASPEX/MAG - Phase 2)',
        },
        'astronaut_radiation': {
            'level': rad_level,
            'impact': ("Possible elevated dose if a radiation storm follows; "
                       "watch for SEP onset." if big else "No significant dose expected."),
            'advisory': ("Advise shelter readiness; monitor proton flux." if rad_level == "ELEVATED"
                         else "Monitor." if big else "No action."),
            'basis': 'flare-class estimate (true S-scale needs ASPEX protons - Phase 2)',
        },
        'power_grid': {
            'level': "WATCH" if big else "LOW",
            'impact': ("A geomagnetic storm may follow if a CME is Earth-directed; "
                       "potential GIC in high-latitude grids." if big
                       else "No geomagnetic impact expected from the flare alone."),
            'advisory': ("Flag grid operators to watch for CME/G-scale follow-up."
                         if big else "No action."),
            'basis': 'flare-class estimate (GIC needs MAG/CME - Phase 2)',
        },
    }

    return {
        'flare_class': flare_class,
        'r_scale': R,
        'domains': domains,
    }


def format_impact_report(assessment: Dict) -> str:
    """Human-readable multi-domain impact + advisory report."""
    lines = [
        "IMPACT ASSESSMENT & SAFETY ADVISORIES",
        "-" * 45,
        f"Flare class      : {assessment['flare_class']}",
        f"Radio-blackout   : R{assessment['r_scale']}",
        "",
    ]
    titles = {
        'radio_blackout': 'Radio Blackout', 'gps_navigation': 'GPS / Navigation',
        'aviation': 'Aviation', 'satellite': 'Satellites',
        'astronaut_radiation': 'Astronaut Radiation', 'power_grid': 'Power Grid',
    }
    for key, title in titles.items():
        d = assessment['domains'][key]
        lines.append(f"[{title}] ({d['level']})")
        lines.append(f"   Impact  : {d['impact']}")
        lines.append(f"   Action  : {d['advisory']}")
        lines.append(f"   Basis   : {d['basis']}")
        lines.append("")
    return "\n".join(lines)
