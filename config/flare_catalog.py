# =============================================================================
# S.H.I.E.L.D. Core Engine — Flare Catalog
# The 6 training/validation events from Aditya-L1 PRADAN data.
#
# Data purity rule (from PRD):
#   - All data sourced exclusively from ISRO PRADAN SoLEXS + HEL1OS files.
#   - December 2023 excluded (instruments still commissioning).
#   - External references (NOAA class labels, published papers) used ONLY
#     to cross-check results, never to train.
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class FlareEvent:
    """A single solar flare event from the validation catalog."""

    event_id: str                          # Unique short identifier
    window_start: datetime                 # Data window start
    window_end: datetime                   # Data window end
    peak_class: str                        # GOES-style class (e.g., "X8.7")
    peak_datetime: Optional[datetime]      # Known peak time (if available)
    active_region: str                     # NOAA active region designation
    description: str                       # Why this event is in the set
    tier: str                              # CRITICAL / TIER 1 / TIER 2
    notes: str = ""                        # Additional notes


# =============================================================================
# THE SIX VALIDATION EVENTS
# =============================================================================

FLARE_CATALOG = [
    FlareEvent(
        event_id="FEB2024_X63",
        window_start=datetime(2024, 2, 20),
        window_end=datetime(2024, 2, 25),
        peak_class="X6.3",
        peak_datetime=datetime(2024, 2, 22, 22, 34),  # Approximate peak
        active_region="AR13590",
        description="Landmark early Aditya-L1 event; cross-validate timing "
                    "vs published analysis (Roy et al. 2025).",
        tier="TIER 1",
    ),
    FlareEvent(
        event_id="MAR2024_X",
        window_start=datetime(2024, 3, 22),
        window_end=datetime(2024, 3, 26),
        peak_class="X-class",
        peak_datetime=None,  # Multiple events in window
        active_region="AR13614",
        description="G4 storm; tests behaviour on a strong, well-observed event.",
        tier="TIER 2",
    ),
    FlareEvent(
        event_id="MAY2024_X87",
        window_start=datetime(2024, 5, 5),
        window_end=datetime(2024, 5, 16),
        peak_class="X8.7",
        peak_datetime=datetime(2024, 5, 14, 12, 51),  # Approximate peak
        active_region="AR13663/64",
        description="Strongest event of the century; PRIMARY validation flare "
                    "(May 14 X8.7).",
        tier="CRITICAL",
        notes="The May 2024 X8.7 flare (14 May) and the 'Gannon' geomagnetic "
              "storm (G5 storm of 10-11 May, driven by earlier CMEs) are "
              "distinct events. The X8.7 flare is the flare-detection target.",
    ),
    FlareEvent(
        event_id="OCT2024_MULTI",
        window_start=datetime(2024, 10, 1),
        window_end=datetime(2024, 10, 15),
        peak_class="Multi-X",
        peak_datetime=None,  # Multiple events
        active_region="Multiple",
        description="Event cluster; tests rolling-baseline recalculation and "
                    "back-to-back flares.",
        tier="TIER 2",
    ),
    FlareEvent(
        event_id="JAN2025_X18",
        window_start=datetime(2025, 1, 1),
        window_end=datetime(2025, 1, 10),
        peak_class="X1.8",
        peak_datetime=None,
        active_region="AR13947",
        description="Smaller X-class; tests low-end sensitivity / "
                    "false-negative rate.",
        tier="TIER 2",
    ),
    FlareEvent(
        event_id="NOV2025_X51",
        window_start=datetime(2025, 11, 7),
        window_end=datetime(2025, 11, 16),
        peak_class="X5.1",
        peak_datetime=None,
        active_region="AR4274",
        description="Strong 2025 event near solar maximum; tests recent data.",
        tier="TIER 1",
    ),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_critical_events():
    """Return events marked as CRITICAL tier."""
    return [e for e in FLARE_CATALOG if e.tier == "CRITICAL"]


def get_tier1_events():
    """Return TIER 1 events."""
    return [e for e in FLARE_CATALOG if e.tier == "TIER 1"]


def get_tier2_events():
    """Return TIER 2 events."""
    return [e for e in FLARE_CATALOG if e.tier == "TIER 2"]


def get_event_by_id(event_id: str) -> Optional[FlareEvent]:
    """Look up a specific event by its ID."""
    for event in FLARE_CATALOG:
        if event.event_id == event_id:
            return event
    return None


def get_all_events():
    """Return all events in the catalog, ordered by priority."""
    priority_order = {"CRITICAL": 0, "TIER 1": 1, "TIER 2": 2}
    return sorted(FLARE_CATALOG, key=lambda e: priority_order.get(e.tier, 99))
