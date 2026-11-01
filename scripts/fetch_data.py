#!/usr/bin/env python3
"""Fetch UK national wind data from Elexon BMRS, clean & validate, save a snapshot.

Datasets (Elexon BMRS Insight API v1, base https://data.elexon.co.uk/bmrs/api/v1):
  FUELHH     - half-hourly generation by fuel type. We keep fuelType == "WIND".
               Fields used: startTime (UTC, 30-min), publishTime, generation (MW).
  WINDFOR    - day/intra-day wind forecasts (dataset name in the BMRS v1 API).
               Issued roughly every 3 hours, each publish covers ~72h ahead at
               hourly resolution.
               Fields used: startTime (UTC, hourly), publishTime, generation (MW).

Date filtering uses query params publishDateTimeFrom / publishDateTimeTo (UTC ISO).
The stream responses are plain JSON arrays; responses are chunked by publish window
because a single unbounded query does not return everything.

Outputs (committed to the repo so the app never depends on live BMRS calls):
  data/actuals.parquet          half-hourly wind actuals
  data/actuals_60min.parquet    actuals aligned to hourly (mean of the 2 half-hours)
  data/forecasts.parquet        all forecast revisions
  data/ingest_report.json       coverage / validation report

Usage:
  python scripts/fetch_data.py                       # standard window (see WINDOWS below)
  python scripts/fetch_data.py --actuals-only        # refresh actuals only
  python scripts/fetch_data.py --forecasts-only      # refresh forecasts only

CLI override of the window (ISO dates, UTC):
  --actuals-from 2026-01-01 --actuals-to 2026-02-01
  --forecasts-from 2025-12-01 --forecasts-to 2026-01-31

Assumptions about resolution (verified against the live API, Nov 2026):
  * FUELHH startTime is on the half hour; hourly actual = mean of the two half-hours.
  * WINDFORECAST startTime is on the hour; forecasts are read directly at hourly res.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets/{dataset}/stream"
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Deliverable window: January 2026 delivery days.
# Cutoffs sit on D-1, so forecasts must start publishing ~2025-12-30; we pull from
# 2025-12-01 for horizon/revision richness for early-January decisions as well.
ACTUALS_FROM, ACTUALS_TO = "2026-01-01", "2026-02-03"   # +2 days to catch late corrections
FORECASTS_FROM, FORECASTS_TO = "2025-12-01", "2026-02-02"  # publish times through Jan 31 23:59Z

RETRY_ATTEMPTS = 4
RETRY_BACKOFF_S = 3.0
REQUEST_TIMEOUT_S = 60
# Publish windows are chunked; each chunk per dataset stays well under the API's
# implicit row cap (observed ~600 rows per response).
CHUNK_HOURS_ACTUALS = 24
CHUNK_HOURS_FORECASTS = 12

DATETIME_FMT = "%Y-%m-%dT%H:%MZ"


def fetch_window(
    dataset: str, params: dict[str, str], session: requests.Session
) -> list[dict]:
    """GET one streaming window with retries; return the parsed JSON array."""
    url = BASE_URL.format(dataset=dataset)
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT_S)
            resp.raise_for_status()
            payload = resp.json()
            if not isinstance(payload, list):
                raise ValueError(f"unexpected payload type: {type(payload)}")
            return payload
        except Exception as exc:  # noqa: BLE001 - degrade to retry then re-raise
            if attempt == RETRY_ATTEMPTS:
                raise RuntimeError(
                    f"BMRS request failed after {RETRY_ATTEMPTS} attempts: "
                    f"{dataset} {params.get('publishDateTimeFrom')}: {exc}"
                ) from exc
            sleep_for = RETRY_BACKOFF_S * attempt
            print(f"  retry {attempt} for {dataset} {params.get('publishDateTimeFrom')} ({exc}); sleeping {sleep_for:.0f}s")
            time.sleep(sleep_for)
    return []


def fetch_dataset(
    dataset: str,
    from_utc: datetime,
    to_utc: datetime,
    chunk_hours: int,
    session: requests.Session,
    extra_params: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Fetch [from_utc, to_utc) in publish-time chunks, return tidy frame."""
    params_base = dict(extra_params or {})
    rows: list[dict] = []
    cursor = from_utc
    while cursor < to_utc:
        chunk_end = min(cursor + timedelta(hours=chunk_hours), to_utc)
        params = dict(params_base)
        params["publishDateTimeFrom"] = cursor.strftime(DATETIME_FMT)
        params["publishDateTimeTo"] = chunk_end.strftime(DATETIME_FMT)
        rows.extend(fetch_window(dataset, params, session))
        cursor = chunk_end
    df = pd.DataFrame(rows)
    required = {"publishTime", "startTime", "generation"}
    if not required.issubset(df.columns):
        raise SystemExit(f"{dataset}: expected columns {required}, got {list(df.columns)}")
    df = df[["publishTime", "startTime", "generation"]].copy()
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True, format="ISO8601")
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True, format="ISO8601")
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    return df


def clean_actuals(df: pd.DataFrame, from_utc: datetime, to_utc: datetime) -> tuple[pd.DataFrame, dict]:
    """Dedupe latest revision per startTime, validate grid, report gaps."""
    before = len(df)
    df = (
        df.sort_values(["startTime", "publishTime"])
        # Keep the LATEST revision per startTime (BMRS may correct values later).
        .drop_duplicates(subset="startTime", keep="last")
        .reset_index(drop=True)
    )
    nan_ct = int(df["generation"].isna().sum())
    df["generation"] = df["generation"].fillna(0.0)

    # Reindex to the exact 30-min grid; count missing intervals.
    grid = pd.date_range(from_utc, to_utc - timedelta(minutes=30), freq="30min", tz="UTC")
    df = df.set_index("startTime").reindex(grid)
    missing = int(df["generation"].isna().sum())
    df["generation"] = df["generation"].fillna(0.0)
    df.index.name = "startTime"
    df = df.reset_index()[["startTime", "generation"]]

    report = {
        "raw_rows": before,
        "deduped_rows": int(len(df)),
        "nan_coerced": nan_ct,
        "missing_intervals": missing,
        "expected_intervals": int(len(grid)),
        "min_start": df["startTime"].min().isoformat(),
        "max_start": df["startTime"].max().isoformat(),
    }
    return df, report


def align_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse 30-min actuals to hourly by mean, keyed on hour start (UTC)."""
    df = df.copy().set_index("startTime")
    hourly = df["generation"].resample("1h").mean()
    hours_with_partial = df["generation"].resample("1h").count()
    out = hourly.rename("generation").reset_index()
    out["half_hours"] = hours_with_partial.values
    return out


def clean_forecasts(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Dedupe exact repeats; forecasts keep every (startTime, publishTime) revision."""
    before = len(df)
    df = df.dropna(subset=["generation"]).reset_index(drop=True)
    df = df.drop_duplicates(subset=["publishTime", "startTime"], keep="last").reset_index(drop=True)
    report = {
        "raw_rows": before,
        "deduped_rows": int(len(df)),
        "unique_publishes": int(df["publishTime"].nunique()),
        "min_publish": df["publishTime"].min().isoformat(),
        "max_publish": df["publishTime"].max().isoformat(),
        "min_start_covered": df["startTime"].min().isoformat(),
        "max_start_covered": df["startTime"].max().isoformat(),
    }
    return df, report


def validate_sanity(df: pd.DataFrame, name: str) -> None:
    gen = df["generation"]
    assert gen.isna().sum() == 0, f"{name}: NaN generation"
    assert gen.min() >= 0, f"{name}: negative generation"
    assert gen.max() <= 30_000, f"{name}: implausible max {gen.max()}"
    print(f"  sanity {name}: rows={len(df)} min={gen.min():.0f} MW max={gen.max():.0f} MW mean={gen.mean():.0f} MW")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Elexon BMRS wind data snapshot")
    ap.add_argument("--actuals-only", action="store_true")
    ap.add_argument("--forecasts-only", action="store_true")
    ap.add_argument("--actuals-from", default=ACTUALS_FROM)
    ap.add_argument("--actuals-to", default=ACTUALS_TO)
    ap.add_argument("--forecasts-from", default=FORECASTS_FROM)
    ap.add_argument("--forecasts-to", default=FORECASTS_TO)
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "wind-forecast-app/1.0"})

    # Merge with any existing report so partial refreshes (--actuals-only / --forecasts-only)
    # keep the sections they did not recompute.
    report_path = DATA_DIR / "ingest_report.json"
    existing: dict[str, object] = {}
    if report_path.exists():
        try:
            existing = json.loads(report_path.read_text())
        except Exception:  # noqa: BLE001 - a corrupt report is not worth failing over
            existing = {}
    report: dict[str, object] = {
        "source": "Elexon BMRS",
        **existing,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }

    if not args.forecasts_only:
        a_from = datetime.fromisoformat(args.actuals_from).replace(tzinfo=timezone.utc)
        a_to = datetime.fromisoformat(args.actuals_to).replace(tzinfo=timezone.utc)
        print(f"Fetching FUELHH actuals {a_from:%Y-%m-%d} .. {a_to:%Y-%m-%d}")
        raw = fetch_dataset("FUELHH", a_from, a_to, CHUNK_HOURS_ACTUALS, session, {"fuelType": "WIND"})
        actuals, arep = clean_actuals(raw, a_from, a_to)
        validate_sanity(actuals, "actuals(hh)")
        actuals.to_parquet(DATA_DIR / "actuals.parquet", index=False)
        hourly = align_hourly(actuals)
        validate_sanity(hourly, "actuals(60)")
        hourly.to_parquet(DATA_DIR / "actuals_60min.parquet", index=False)
        report["actuals"] = arep
        report["actuals_hourly_halfhour_coverage"] = {
            "hours_with_2_halfhours": int((hourly["half_hours"] == 2).sum()),
            "hours_with_1_halfhour": int((hourly["half_hours"] == 1).sum()),
        }

    if not args.actuals_only:
        f_from = datetime.fromisoformat(args.forecasts_from).replace(tzinfo=timezone.utc)
        f_to = datetime.fromisoformat(args.forecasts_to).replace(tzinfo=timezone.utc)
        print(f"Fetching WINDFOR forecasts {f_from:%Y-%m-%d} .. {f_to:%Y-%m-%d}")
        raw = fetch_dataset("WINDFOR", f_from, f_to, CHUNK_HOURS_FORECASTS, session)
        forecasts, frep = clean_forecasts(raw)
        validate_sanity(forecasts, "forecasts")
        forecasts.to_parquet(DATA_DIR / "forecasts.parquet", index=False)
        report["forecasts"] = frep

    (DATA_DIR / "ingest_report.json").write_text(json.dumps(report, indent=2))
    print("Ingest report:")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
