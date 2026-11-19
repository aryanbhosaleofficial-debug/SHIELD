# =============================================================================
# S.H.I.E.L.D. Core Engine — Data Preprocessing
# Aligns SoLEXS and HEL1OS time-series on a common time axis, cleans gaps,
# interpolates missing values, and produces a unified DataFrame.
#
# Output: clean DataFrame with columns:
#   [timestamp, solexs_flux, hel1os_flux]
# at 1-second cadence, ready for the physics engine.
# =============================================================================

import logging
from typing import Optional, Union
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import (
    RESAMPLE_CADENCE_S,
    MAX_GAP_INTERPOLATE_S,
    PROCESSED_DATA_DIR,
)

logger = logging.getLogger(__name__)


# =============================================================================
# TIME-AXIS ALIGNMENT
# =============================================================================

def align_timeseries(
    solexs_df: pd.DataFrame,
    hel1os_df: pd.DataFrame,
    cadence_s: int = RESAMPLE_CADENCE_S,
) -> pd.DataFrame:
    """
    Align SoLEXS and HEL1OS data onto a common time axis using
    pandas merge_asof (nearest-timestamp matching).

    Both instruments have ~1s cadence but their timestamps won't match
    exactly. merge_asof handles this by matching each timestamp to the
    nearest one in the other series within a tolerance.

    Parameters
    ----------
    solexs_df : pd.DataFrame
        SoLEXS data with ['timestamp', 'flux'] columns.
    hel1os_df : pd.DataFrame
        HEL1OS data with ['timestamp', 'flux'] columns.
    cadence_s : int
        Target cadence in seconds for the output (default: 1s).

    Returns
    -------
    pd.DataFrame
        Aligned DataFrame with columns:
        ['timestamp', 'solexs_flux', 'hel1os_flux']
    """
    logger.info("Aligning SoLEXS and HEL1OS time-series...")

    # Prepare SoLEXS
    solexs = solexs_df[['timestamp', 'flux']].copy()
    solexs = solexs.rename(columns={'flux': 'solexs_flux'})
    solexs = solexs.sort_values('timestamp').reset_index(drop=True)
    solexs['timestamp'] = pd.to_datetime(solexs['timestamp'])

    # Prepare HEL1OS
    hel1os = hel1os_df[['timestamp', 'flux']].copy()
    hel1os = hel1os.rename(columns={'flux': 'hel1os_flux'})
    hel1os = hel1os.sort_values('timestamp').reset_index(drop=True)
    hel1os['timestamp'] = pd.to_datetime(hel1os['timestamp'])

    # Determine the common time range
    start = max(solexs['timestamp'].min(), hel1os['timestamp'].min())
    end = min(solexs['timestamp'].max(), hel1os['timestamp'].max())

    if start >= end:
        logger.warning("No overlapping time range between SoLEXS and HEL1OS!")
        return pd.DataFrame(columns=['timestamp', 'solexs_flux', 'hel1os_flux'])

    logger.info(f"  Common time range: {start} -> {end}")
    duration = (end - start).total_seconds()
    logger.info(f"  Duration: {duration:.0f} seconds ({duration/3600:.1f} hours)")

    # Create a uniform time grid at the target cadence
    time_grid = pd.date_range(start=start, end=end, freq=f'{cadence_s}s')
    aligned = pd.DataFrame({'timestamp': time_grid})

    # Merge SoLEXS onto the grid (nearest match within tolerance)
    tolerance = pd.Timedelta(seconds=cadence_s * 2)

    aligned = pd.merge_asof(
        aligned,
        solexs,
        on='timestamp',
        tolerance=tolerance,
        direction='nearest',
    )

    # Merge HEL1OS onto the grid
    aligned = pd.merge_asof(
        aligned,
        hel1os,
        on='timestamp',
        tolerance=tolerance,
        direction='nearest',
    )

    logger.info(f"  Aligned grid: {len(aligned)} points at {cadence_s}s cadence")
    logger.info(f"  SoLEXS NaN: {aligned['solexs_flux'].isna().sum()} "
                f"({aligned['solexs_flux'].isna().mean()*100:.1f}%)")
    logger.info(f"  HEL1OS NaN: {aligned['hel1os_flux'].isna().sum()} "
                f"({aligned['hel1os_flux'].isna().mean()*100:.1f}%)")

    return aligned


# =============================================================================
# DATA CLEANING
# =============================================================================

def clean_flux_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the aligned flux data:
      1. Remove negative flux values (unphysical)
      2. Remove extreme outliers (likely telemetry errors)
      3. Interpolate small gaps
      4. Flag remaining gaps

    Parameters
    ----------
    df : pd.DataFrame
        Aligned DataFrame with ['timestamp', 'solexs_flux', 'hel1os_flux'].

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with additional columns:
        ['solexs_valid', 'hel1os_valid'] — boolean flags for data quality.
    """
    logger.info("Cleaning flux data...")
    result = df.copy()

    for col in ['solexs_flux', 'hel1os_flux']:
        if col not in result.columns:
            continue

        original_nans = result[col].isna().sum()
        valid_col = col.replace('_flux', '_valid')

        # Step 1: Replace negative values with NaN (unphysical)
        neg_count = (result[col] < 0).sum()
        if neg_count > 0:
            result.loc[result[col] < 0, col] = np.nan
            logger.info(f"  {col}: removed {neg_count} negative values")

        # Step 2: Remove extreme outliers (> 10-sigma from rolling median)
        rolling_median = result[col].rolling(
            window=61, center=True, min_periods=10
        ).median()
        rolling_std = result[col].rolling(
            window=61, center=True, min_periods=10
        ).std()

        outlier_mask = np.abs(result[col] - rolling_median) > (10 * rolling_std)
        outlier_count = outlier_mask.sum()
        if outlier_count > 0:
            result.loc[outlier_mask, col] = np.nan
            logger.info(f"  {col}: removed {outlier_count} outliers (>10-sigma)")

        # Step 3: Interpolate small gaps (up to MAX_GAP_INTERPOLATE_S)
        # Identify gap sizes
        is_nan = result[col].isna()
        gap_groups = (is_nan != is_nan.shift()).cumsum()
        gap_sizes = is_nan.groupby(gap_groups).transform('sum')

        # Only interpolate gaps smaller than the threshold
        small_gap_mask = is_nan & (gap_sizes <= MAX_GAP_INTERPOLATE_S)
        if small_gap_mask.any():
            result[col] = result[col].interpolate(
                method='linear', limit=MAX_GAP_INTERPOLATE_S
            )
            interpolated = original_nans - result[col].isna().sum()
            logger.info(f"  {col}: interpolated {interpolated} small gap values")

        # Step 4: Mark valid data points
        result[valid_col] = ~result[col].isna()

        total_valid = result[valid_col].sum()
        total = len(result)
        logger.info(f"  {col}: {total_valid}/{total} valid "
                    f"({total_valid/total*100:.1f}%)")

    return result


# =============================================================================
# NORMALIZATION
# =============================================================================

def normalize_flux(df: pd.DataFrame, method: str = 'none') -> pd.DataFrame:
    """
    Optionally normalize flux values for ML processing.
    The physics engine (Layer 1) uses raw flux, but ML layers may
    benefit from normalization.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame with flux columns.
    method : str
        'none' — no normalization (for physics engine)
        'minmax' — scale to [0, 1]
        'zscore' — standardize to mean=0, std=1
        'log' — log10 transform (common for flux spanning decades)

    Returns
    -------
    pd.DataFrame
        DataFrame with normalized flux columns added.
    """
    result = df.copy()

    for col in ['solexs_flux', 'hel1os_flux']:
        if col not in result.columns:
            continue

        norm_col = col.replace('_flux', '_flux_norm')
        valid_data = result[col].dropna()

        if method == 'none':
            result[norm_col] = result[col]
        elif method == 'minmax':
            vmin, vmax = valid_data.min(), valid_data.max()
            result[norm_col] = (result[col] - vmin) / (vmax - vmin + 1e-15)
        elif method == 'zscore':
            mean, std = valid_data.mean(), valid_data.std()
            result[norm_col] = (result[col] - mean) / (std + 1e-15)
        elif method == 'log':
            # Log10 with floor for zeros
            result[norm_col] = np.log10(np.maximum(result[col], 1e-15))
        else:
            raise ValueError(f"Unknown normalization method: {method}")

    return result


# =============================================================================
# FULL PREPROCESSING PIPELINE
# =============================================================================

def preprocess_event(
    solexs_df: pd.DataFrame,
    hel1os_df: pd.DataFrame,
    event_id: str = "unknown",
    save: bool = True,
) -> pd.DataFrame:
    """
    Run the full preprocessing pipeline on a pair of instrument DataFrames:
      1. Align on common time axis
      2. Clean (remove negatives, outliers, interpolate gaps)
      3. Save to processed directory

    Parameters
    ----------
    solexs_df : pd.DataFrame
        Raw SoLEXS data with ['timestamp', 'flux'].
    hel1os_df : pd.DataFrame
        Raw HEL1OS data with ['timestamp', 'flux'].
    event_id : str
        Event identifier for file naming.
    save : bool
        Whether to save the processed data to disk.

    Returns
    -------
    pd.DataFrame
        Clean, aligned DataFrame ready for the physics engine.
    """
    logger.info(f"{'='*60}")
    logger.info(f"Preprocessing event: {event_id}")
    logger.info(f"{'='*60}")

    # Step 1: Align
    aligned = align_timeseries(solexs_df, hel1os_df)

    if aligned.empty:
        logger.error(f"  Alignment produced no data for {event_id}")
        return aligned

    # Step 2: Clean
    cleaned = clean_flux_data(aligned)

    # Step 3: Save
    if save:
        save_path = PROCESSED_DATA_DIR / f"{event_id}_processed.csv"
        cleaned.to_csv(save_path, index=False)
        logger.info(f"  Saved processed data to: {save_path}")

    logger.info(f"  Preprocessing complete: {len(cleaned)} rows")
    logger.info(f"  Time range: {cleaned['timestamp'].min()} -> "
                f"{cleaned['timestamp'].max()}")

    return cleaned


def load_processed_event(event_id: str) -> Optional[pd.DataFrame]:
    """
    Load a previously processed event from disk.

    Parameters
    ----------
    event_id : str
        Event identifier.

    Returns
    -------
    pd.DataFrame or None
        Processed DataFrame, or None if not found.
    """
    filepath = PROCESSED_DATA_DIR / f"{event_id}_processed.csv"
    if not filepath.exists():
        logger.warning(f"No processed data found for {event_id}")
        return None

    df = pd.read_csv(filepath, parse_dates=['timestamp'])
    logger.info(f"Loaded processed data for {event_id}: {len(df)} rows")
    return df
