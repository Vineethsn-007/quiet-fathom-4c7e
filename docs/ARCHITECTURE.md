# Architecture

## Overview

```
React (Vite+TS, Tailwind, Recharts) ──fetch──▶ FastAPI (pandas) ──reads──▶ committed snapshot (parquet in /data)
                                                    ▲
                                     Elexon BMRS v1 API (scripts/fetch_data.py only, never at runtime)
```

```mermaid
flowchart LR
    subgraph offline[Offline ingestion - run manually or in CI]
        A[Elexon BMRS<br/>FUELHH + WINDFOR] -->|scripts/fetch_data.py<br/>chunked GET, retries, dedupe| B[data/actuals.parquet<br/>data/actuals_60min.parquet<br/>data/forecasts.parquet<br/>data/ingest_report.json]
    end
    B --> C[FastAPI backend<br/>app/services/analysis.py<br/>decision-time selection,<br/>metrics, bands]
    C -->|REST JSON| D[React SPA<br/>5 pages, Recharts]
    C --> E[Docker compose / Vercel backend service]
    D --> F[Buyer at 09:00 on D-1<br/>risk-adjusted wind figure]
```

## Data flow

1. **Ingestion (offline).** `scripts/fetch_data.py` pulls FUELHH (`fuelType=WIND`, 30-min actuals)
   and WINDFOR (hourly forecasts, published every ~3h, each spanning ~72h ahead) in time-chunked
   HTTP requests with retries/backoff, then:
   - dedupes FUELHH by `startTime` keeping the **latest** `publishTime` (late corrections win);
   - dedupes forecast revisions on the `(publishTime, startTime)` key;
   - aligns actuals to hourly (mean of the two half-hours) with a coverage count per hour;
   - writes compact parquet files plus an `ingest_report.json` and runs sanity checks
     (0 ≤ MW ≤ 30,000, no NaNs).
2. **Serving.** The Docker backend and Vercel backend service read the same committed parquet
   snapshot — the deployed app never calls Elexon live. Vercel copies the snapshot into the
   backend service root before bundling it with the FastAPI function.
3. **Decision logic.** For delivery day D and cutoff on D-1 (default 09:00 Europe/London → UTC):
   per-hour selection of the forecast row with the greatest `publishTime ≤ cutoff`
   (`app/services/analysis.py#eval_pairs_df`, mirroring the unit-tested
   `app/core/decision.py#select_latest_forecast`).
4. **Analytics.** Metrics (bias/MAE/RMSE/MAPE-with-floor/percentiles), bucketing by horizon and
   hour-of-day, and empirical P10/P90 bands; all plain pandas, no ML.

## Design decisions & trade-offs

| Decision | Rationale | Trade-off |
| --- | --- | --- |
| Committed snapshot instead of live BMRS reads | Deterministic demos, no rate limits, fast Vercel cold starts | Data ages; refresh needs a manual `scripts/fetch_data.py` run (see limitations) |
| Align 30-min actuals to hourly rather than 30-min forecasts | WINDFOR is hourly; degradation to half-hourly would fabricate data | Hours cover two half-hours; a missing half-hour makes the hour an average of one — flagged via `halfHours` |
| Empirical percentile bands instead of probabilistic forecast models | Transparent, auditable, matches "no black-box ML" requirement | Assumes error stationarity; bands can be miscalibrated in regime shifts |
| horizon buckets (0-6…48-72h) | Error grows with horizon but is confounded with hour-of-day at a fixed cutoff | Coarse buckets smooth small-sample noise |
| Cutoff stored as London wall clock, computed in UTC | Matches how the client thinks and speaks; DST-correct | Spring-forward 01:30 London gaps handled with zoneinfo fold rules (tested) |
| Single `meta` + per-endpoint payloads | Fewer round-trips for the 5 UI pages | Payload recomputation per request (small data, <1s) |
| JSON responses only from REST; CSV generated client-side | Keeps API narrow | Big exports would be better server-side |

## Repository map

```
backend/app/core      decision.py (cutoff/DST/horizon), metrics.py, config.py, logging.py
backend/app/services  data_store.py (parquet cache), analysis.py (all endpoint payloads)
backend/app/api       routes.py (typed FastAPI endpoints)
backend/app/models    Pydantic schemas
backend/tests         decision, DST, horizon, metrics, API tests (pytest)
frontend/src/pages    Overview, Explorer, Accuracy, Revisions, Methodology
frontend/src/api      typed client; hooks/useFetch; utils/format+csv
scripts/fetch_data.py offline ingestion CLI
data/*.parquet        committed snapshot consumed at runtime
docs/                 ARCHITECTURE, ANALYSIS, DEMO_SCRIPT
api/index.py          legacy single-service Vercel entrypoint
vercel.json           Vercel frontend/backend services and public routing
```
