"""Core decision-time domain logic.

Key concept: for a delivery day D and a decision cutoff on day D-1, the buyer
sees the LATEST forecast per target startTime with publishTime <= cutoff.
All timestamps are UTC internally; cutoff is expressed in Europe/London local
time and converted with proper DST handling.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")

# Europe/London DST transition dates are the last Sunday in March / October.
# Cutoffs landing on the ambiguous (01:00-01:59 GMT repeat in autumn) hour are
# resolved with the FIRST occurrence (fold=0), i.e. the earlier UTC instant.


def london_date_to_utc(local_date: date, local_time: time, tz: ZoneInfo = LONDON) -> datetime:
    """Convert a wall-clock instant in the given tz to UTC, DST-aware.

    For non-existent times (spring-forward gap) the clock is normalised by the
    zone rules (UTC + gap). For ambiguous times (autumn repeat) the first
    occurrence (fold=0) is used.
    """
    local_dt = datetime.combine(local_date, local_time, tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


def cutoff_utc_for_delivery(day: date, cutoff: time, tz: ZoneInfo = LONDON) -> datetime:
    """Decision cutoff UTC instant: cutoff clock time on day D-1 (London tz)."""
    return london_date_to_utc(day - timedelta(days=1), cutoff, tz)


def horizon_hours(start_time: datetime, publish_time: datetime) -> float:
    """Forecast horizon = startTime - publishTime, in hours."""
    return (start_time - publish_time).total_seconds() / 3600.0


def select_latest_forecast(
    forecasts: list[dict], cutoff_utc: datetime, start_from: datetime | None, start_to: datetime | None
) -> list[dict]:
    """For each target startTime pick the forecast row with the greatest
    publishTime <= cutoff_utc.

    Args:
        forecasts: rows with keys startTime (UTC datetime), publishTime
            (UTC datetime), generation (float MW).
        cutoff_utc: decisions may only use rows published at/before this instant.
        start_from/start_to: restrict to target startTimes in [from, to).

    Returns:
        One row per startTime, each carrying the original keys plus horizon
        hours. Sorted by startTime.
    """
    by_start: dict[datetime, dict] = {}
    for row in forecasts:
        st = row["startTime"]
        pt = row["publishTime"]
        if row["generation"] is None or (
            isinstance(row["generation"], float) and row["generation"] != row["generation"]
        ):
            continue
        if pt > cutoff_utc:
            continue
        if start_from is not None and st < start_from:
            continue
        if start_to is not None and st >= start_to:
            continue
        best = by_start.get(st)
        if best is None or pt > best["publishTime"]:
            by_start[st] = row
    out = []
    for st in sorted(by_start):
        row = dict(by_start[st])
        row["horizonHours"] = horizon_hours(st, row["publishTime"])
        out.append(row)
    return out


def horizon_bucket(h: float) -> str:
    """Map horizon hours to a readable bucket label."""
    from app.core.config import HORIZON_BUCKETS

    for label, lo, hi in HORIZON_BUCKETS:
        if lo <= h < hi:
            return label
    return "48-72h" if h >= 48 else "0-6h"
