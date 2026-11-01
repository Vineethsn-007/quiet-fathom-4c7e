"""Loads the committed BMRS snapshot (parquet) into cached pandas frames."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.core.config import get_settings

log = logging.getLogger(__name__)


class SnapshotError(RuntimeError):
    """Raised when the data snapshot is missing or unreadable."""


def _path(name: str) -> Path:
    data_dir = get_settings().data_dir
    p = data_dir / name
    if not p.exists():
        raise SnapshotError(
            f"Snapshot file {name} not found in {data_dir}. "
            "Run scripts/fetch_data.py to generate the data snapshot."
        )
    return p


@lru_cache(maxsize=1)
def load_actuals() -> pd.DataFrame:
    """Half-hourly actuals: columns startTime (tz-aware UTC), generation (MW)."""
    df = pd.read_parquet(_path("actuals.parquet"))
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df


@lru_cache(maxsize=1)
def load_actuals_hourly() -> pd.DataFrame:
    """Hourly actuals (mean of the two half-hours) + coverage counts."""
    df = pd.read_parquet(_path("actuals_60min.parquet"))
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df


@lru_cache(maxsize=1)
def load_forecasts() -> pd.DataFrame:
    """All forecast revisions: publishTime, startTime, generation (MW)."""
    df = pd.read_parquet(_path("forecasts.parquet"))
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df


@lru_cache(maxsize=1)
def load_ingest_report() -> dict:
    path = _path("ingest_report.json")
    return json.loads(path.read_text())


def forecast_hour_vector(day_start_utc: pd.Timestamp, cutoff_utc: pd.Timestamp) -> pd.DataFrame:
    """Vectorised latest-at-cutoff forecast for the 24 hourly starts of a day.

    Returns columns: startTime, publishTime, generation, horizonHours.
    """
    fc = load_forecasts()
    day_end = day_start_utc + pd.Timedelta(hours=24)
    in_day = fc[(fc["startTime"] >= day_start_utc) & (fc["startTime"] < day_end) & (fc["publishTime"] <= cutoff_utc)]
    if in_day.empty:
        return pd.DataFrame(columns=["startTime", "publishTime", "generation", "horizonHours"])
    latest = in_day.sort_values("publishTime").groupby("startTime", as_index=False).tail(1)
    latest["horizonHours"] = (latest["startTime"] - latest["publishTime"]).dt.total_seconds() / 3600.0
    return latest.sort_values("startTime").reset_index(drop=True)


def actual_hour_vector(day_start_utc: pd.Timestamp) -> pd.DataFrame:
    """Aligned hourly actuals for a delivery day (UTC hours 0-23)."""
    ah = load_actuals_hourly()
    day_end = day_start_utc + pd.Timedelta(hours=24)
    sel = ah[(ah["startTime"] >= day_start_utc) & (ah["startTime"] < day_end)]
    return sel.reset_index(drop=True)


def clear_caches() -> None:
    load_actuals.cache_clear()
    load_actuals_hourly.cache_clear()
    load_forecasts.cache_clear()
    load_ingest_report.cache_clear()
