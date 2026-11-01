"""Decision-support service: builds analysis payloads from the snapshot."""
from __future__ import annotations

import logging
from datetime import date, datetime, time as dtime, timedelta, timezone

import pandas as pd

from app.core.config import (
    DEFAULT_CUTOFF_LONDON,
    HORIZON_BUCKETS,
    NORMALISATION_FLOOR_MW,
    LONDON_TZ,
    get_settings,
)
from app.core.decision import (
    cutoff_utc_for_delivery,
    horizon_bucket,
    london_date_to_utc,
    select_latest_forecast,
)
from app.core.metrics import (
    MetricSummary,
    error_distribution,
    error_percentiles,
    percentile,
    summary_metrics,
)
from app.services import data_store

log = logging.getLogger(__name__)

# Static histogram bin edges in MW (signed error: forecast - actual).
ERROR_BINS = [-8000, -6000, -4000, -3000, -2000, -1000, -500, 0, 500, 1000, 2000, 3000, 4000, 6000, 8000]


def parse_cutoff(cutoff: str | None) -> dtime:
    """Parse a 'HH:MM' London-local clock cutoff; default 09:00."""
    if not cutoff:
        return dtime.fromisoformat(DEFAULT_CUTOFF_LONDON)
    try:
        return dtime.fromisoformat(cutoff)
    except ValueError as exc:
        raise ValueError(f"cutoff must be HH:MM (Europe/London), got {cutoff!r}") from exc


def month_days(year: int = 2026, month: int = 1) -> list[date]:
    """Delivery days covered by the snapshot for the given month."""
    first = date(year, month, 1)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    return [(first + timedelta(days=i)) for i in range((nxt - first).days)]


def eval_pairs_df(cutoff: dtime, days: list[date]) -> pd.DataFrame:
    """Aligned forecast-at-cutoff vs actual pairs for every hour of given days.

    Columns: day, startTime, actual (MW), halfHours, forecast (MW),
    publishTime, horizonHours, error (forecast-actual), errorBucket (MW),
    horizonBucket.
    """
    fc = data_store.load_forecasts()
    ah = data_store.load_actuals_hourly()
    rows: list[dict] = []
    for day in days:
        cutoff_utc = pd.Timestamp(cutoff_utc_for_delivery(day, cutoff, LONDON_TZ))
        day_start = pd.Timestamp(day, tz="UTC")
        day_end = day_start + pd.Timedelta(hours=24)
        fday = fc[
            (fc["startTime"] >= day_start)
            & (fc["startTime"] < day_end)
            & (fc["publishTime"] <= cutoff_utc)
        ]
        if fday.empty:
            continue
        latest = fday.sort_values("publishTime").groupby("startTime", as_index=False).tail(1)
        aday = ah[(ah["startTime"] >= day_start) & (ah["startTime"] < day_end)]
        merged = latest.merge(aday, on="startTime", how="inner")
        for r in merged.itertuples(index=False):
            publish_tz = r.publishTime.to_pydatetime() if hasattr(r.publishTime, "to_pydatetime") else r.publishTime
            h = (r.startTime.to_pydatetime() - publish_tz).total_seconds() / 3600.0
            rows.append(
                {
                    "day": day.isoformat(),
                    "startTime": r.startTime,
                    "actual": float(r.generation_y),
                    "halfHours": float(r.half_hours),
                    "forecast": float(r.generation_x),
                    "publishTime": r.publishTime,
                    "horizonHours": h,
                    "error": float(r.generation_x) - float(r.generation_y),
                    "horizonBucket": horizon_bucket(h),
                }
            )
    df = pd.DataFrame(rows)
    return df


def _bucket_label(h: float) -> str:
    return horizon_bucket(h)


def forecast_view(day: date, cutoff: dtime) -> dict:
    """Latest-at-cutoff forecast vs actual for one delivery day, with uncertainty band."""
    day_start = pd.Timestamp(day, tz="UTC")
    cutoff_utc = pd.Timestamp(cutoff_utc_for_delivery(day, cutoff, LONDON_TZ))

    hourly = data_store.actual_hour_vector(day_start)
    fcvec = data_store.forecast_hour_vector(day_start, cutoff_utc)

    # Empirical error percentiles per horizon bucket, over ALL decision-eval pairs
    # (cutoff applied per day just like the buyer would).
    evals = eval_pairs_df(cutoff, month_days())
    bucket_pct: dict[str, dict] = {}
    for bucket in evals["horizonBucket"].unique():
        e = evals.loc[evals["horizonBucket"] == bucket, "error"].tolist()
        bucket_pct[bucket] = error_percentiles(e)

    points = []
    for ts in pd.date_range(day_start, periods=24, freq="1h", tz="UTC"):
        actual = hourly.loc[hourly["startTime"] == ts, "generation"]
        a_val = float(actual.iloc[0]) if len(actual) else None
        half = hourly.loc[hourly["startTime"] == ts, "half_hours"]
        a_half = int(half.iloc[0]) if len(half) else 0
        frow = fcvec[fcvec["startTime"] == ts]
        fc_val: float | None = None
        pt = None
        horizon = None
        bucket = None
        p10 = p90 = None
        if len(frow):
            fc_val = float(frow["generation"].iloc[0])
            pt = frow["publishTime"].iloc[0]
            horizon = float(frow["horizonHours"].iloc[0])
            bucket = _bucket_label(horizon)
            b = bucket_pct.get(bucket)
            if b:
                # actual = forecast - error, so band edges invert the percentiles:
                # P10 of actual = forecast - P90(error); P90 of actual = forecast - P10(error).
                p10 = fc_val - b["p90"]
                p90 = fc_val - b["p10"]
        points.append(
            {
                "startTime": ts.isoformat(),
                "actual": a_val,
                "halfHours": a_half,
                "forecast": fc_val,
                "publishTime": None if pt is None else pt.isoformat(),
                "horizonHours": horizon,
                "horizonBucket": bucket,
                "bandLow": p10,
                "bandHigh": p90,
            }
        )

    valid_pairs = evals[evals["day"] == day.isoformat()]
    risk = None
    if len(valid_pairs):
        errs = valid_pairs["error"].tolist()
        pct = error_percentiles(errs)
        risk = {
            "method": "empirical-decision-time",
            # Deltas to add to the latest forecast to obtain percentile outcomes of ACTUAL wind:
            "lowWindP10Delta": -pct["p90"],  # 90% of historical actuals were above forecast+lowWindP10Delta
            "medianDelta": -pct["p50"],
            "highWindP90Delta": -pct["p10"],
            "nDays": int(valid_pairs["day"].nunique()),
        }
    return {
        "day": day.isoformat(),
        "cutoff": {
            "london": f"{day - timedelta(days=1)}T{cutoff.strftime('%H:%M')}",
            "utc": cutoff_utc.isoformat(),
        },
        "points": points,
        "risk": risk,
    }


def accuracy_summary(cutoff: dtime) -> dict:
    days = month_days()
    evals = eval_pairs_df(cutoff, days)
    if evals.empty:
        raise ValueError("no evaluable pairs in snapshot for the summary window")
    ms: MetricSummary = summary_metrics(evals["error"].tolist(), evals["actual"].tolist())

    # Republished bias direction statement
    if ms.bias >= 0:
        bias_dir = "over" if ms.bias > 0 else "(unchanged)"
        insight_bias = (
            f"Decision-time forecasts {bias_dir}forecast wind by {ms.bias:,.0f} MW on average "
            f"(mean error {ms.bias:+,.0f} MW)."
        )
    else:
        insight_bias = (
            f"Decision-time forecasts underforecast wind by {abs(ms.bias):,.0f} MW on average "
            f"(mean error {ms.bias:+,.0f} MW)."
        )
    return {
        "cutoff": cutoff.strftime("%H:%M"),
        "cutoffLondon": DEFAULT_CUTOFF_LONDON if cutoff == dtime.fromisoformat(DEFAULT_CUTOFF_LONDON) else cutoff.strftime("%H:%M"),
        "metrics": ms.to_dict(),
        "nHours": int(len(evals)),
        "nDaysWithPairs": int(evals["day"].nunique()),
        "totalHoursJan": 31 * 24,
        "insights": [
            insight_bias,
            f"P95 absolute error is {ms.p95_abs:,.0f} MW; in the worst 5% of hours the "
            f"forecast misses by more than that.",
            f"Wind buffer: hold at least {ms.p90_abs:,.0f} MW of extra thermal/spin reserve relative to the "
            f"forecast (P90 absolute error) — historical wind came in below forecast by more than that in "
            f"~10% of decision-time hours; {ms.p95_abs:,.0f} MW covers the worst 5%.",
        ],
        "coverage": data_store.load_ingest_report(),
    }


def accuracy_by_hour(cutoff: dtime) -> list[dict]:
    evals = eval_pairs_df(cutoff, month_days())
    return [
        {
            "hourLondon": h,
            "bias": round(g["error"].mean(), 1),
            "mae": round(g["error"].abs().mean(), 1),
            "rmse": round(float((g["error"] ** 2).mean() ** 0.5), 1),
            "meanActual": round(g["actual"].mean(), 1),
            "meanForecast": round(g["forecast"].mean(), 1),
            "n": int(len(g)),
        }
        for h, g in evals.assign(
            hourLondon=evals["startTime"].dt.tz_convert(LONDON_TZ).dt.hour
        ).groupby("hourLondon", sort=True)
    ]


def accuracy_by_horizon(cutoff: dtime) -> list[dict]:
    evals = eval_pairs_df(cutoff, month_days())
    out = []
    for label, lo, hi in HORIZON_BUCKETS:
        g = evals[evals["horizonBucket"] == label]
        if g.empty:
            out.append({"horizonBucket": label, "loHours": lo, "hiHours": hi, "n": 0, "bias": None, "mae": None, "rmse": None})
            continue
        out.append(
            {
                "horizonBucket": label,
                "loHours": lo,
                "hiHours": hi,
                "n": int(len(g)),
                "bias": round(g["error"].mean(), 1),
                "mae": round(g["error"].abs().mean(), 1),
                "rmse": round(float((g["error"] ** 2).mean() ** 0.5), 1),
            }
        )
    return out


def accuracy_distribution(cutoff: dtime) -> dict:
    evals = eval_pairs_df(cutoff, month_days())
    return {
        "binsMw": ERROR_BINS,
        "histogram": error_distribution(evals["error"].tolist(), ERROR_BINS),
        "percentiles": {k: round(v, 1) for k, v in error_percentiles(evals["error"].tolist()).items()},
        "n": int(len(evals)),
    }


def accuracy_scatter(cutoff: dtime, max_points: int = 4000) -> list[dict]:
    evals = eval_pairs_df(cutoff, month_days())
    if len(evals) > max_points:
        evals = evals.sample(max_points, random_state=42)
    return [
        {
            "startTime": r.startTime.isoformat(),
            "forecast": round(r.forecast, 1),
            "actual": round(r.actual, 1),
            "horizonHours": round(r.horizonHours, 2),
        }
        for r in evals.itertuples(index=False)
    ]


def revisions_view(day: date, cutoff: dtime) -> dict:
    """Show successive forecast revisions for each hour of delivery day D."""
    day_start = pd.Timestamp(day, tz="UTC")
    day_end = day_start + pd.Timedelta(hours=24)
    cutoff_utc = pd.Timestamp(cutoff_utc_for_delivery(day, cutoff, LONDON_TZ))
    fc = data_store.load_forecasts()
    window_start = cutoff_utc - pd.Timedelta(hours=96)
    fday = fc[
        (fc["startTime"] >= day_start)
        & (fc["startTime"] < day_end)
        & (fc["publishTime"] > window_start)
        & (fc["publishTime"] <= cutoff_utc)
    ]
    aday = data_store.actual_hour_vector(day_start)

    by_publish: dict[str, list] = {}
    for pt, g in fday.groupby("publishTime"):
        rows = []
        for r in g.sort_values("startTime").itertuples(index=False):
            rows.append(
                {
                    "startTime": r.startTime.isoformat(),
                    "forecast": float(r.generation),
                    "horizonHours": round(float((r.startTime - pt).total_seconds() / 3600.0), 2),
                }
            )
        by_publish[pt.isoformat()] = rows

    actuals = {
        r.startTime.isoformat(): float(r.generation)
        for r in aday.itertuples(index=False)
    }
    return {
        "day": day.isoformat(),
        "cutoffUtc": cutoff_utc.isoformat(),
        "actuals": actuals,
        "publishes": [{"publishTime": pt, "targets": rows} for pt, rows in sorted(by_publish.items())],
    }


def meta() -> dict:
    ah = data_store.load_actuals_hourly()
    fc = data_store.load_forecasts()
    return {
        "actuals": {
            "first": ah["startTime"].min().isoformat(),
            "last": ah["startTime"].max().isoformat(),
            "resolutionMinutes": 30,
            "hoursNormalized": int(len(ah)),
        },
        "forecasts": {
            "firstPublish": fc["publishTime"].min().isoformat(),
            "lastPublish": fc["publishTime"].max().isoformat(),
            "nPublishes": int(fc["publishTime"].nunique()),
            "nRows": int(len(fc)),
            "resolutionMinutes": 60,
        },
        "generatedUtc": data_store.load_ingest_report().get("generated_utc"),
        "source": "Elexon BMRS (BMRS Insight API v1)",
        "defaultCutoffLondon": DEFAULT_CUTOFF_LONDON,
    }
