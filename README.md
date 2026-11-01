# UK Wind — Day-Ahead Decision Support (January 2026)

A web tool for a UK energy utility's day-ahead power purchasing desk. For each January 2026
delivery day **D**, the buyer must purchase tomorrow's residual demand (= demand − wind) on **D-1**.
The product shows:

- the **latest wind forecast available at decision time** (cutoff default **09:00 Europe/London on D-1**),
  where "latest" means the forecast revision with the greatest `publishTime ≤ cutoff`;
- **how accurate those decision-time forecasts historically are** (bias, MAE, RMSE, MAPE with a
  near-zero guard, P50/P90/P95 errors, error by hour-of-day / horizon / generation level);
- a **transparent uncertainty band** (empirical P10–P90 of wind given the forecast) and a
  **risk-adjusted wind figure** (forecast − P90 of error ≈ 90% historical coverage).

Scope: national-level UK **wind only**, data from **Elexon BMRS** only (datasets FUELHH and WINDFOR),
delivery days in **January 2026**. Real data — 744/744 January hours covered, no fixtures.

**Deployed app:** _<paste your Vercel URL here after `vercel deploy`>_

## Quick start

### With Docker (recommended, one command)

```bash
docker compose up --build
# frontend: http://localhost:5174   backend API docs: http://localhost:8000/docs
```

> Note: on the machine this repo was authored on, Docker was not available, so the compose stack
> was written to standard patterns but not executed there — if anything differs, see
> "Run without Docker" below, which is verified.

### Without Docker (verified)

```bash
# Backend ---------------------------------------------------------------
python -m pip install -r backend/requirements.txt pytest httpx
cd backend && uvicorn app.main:app --port 8000         # needs data/ snapshot (committed)

# Frontend (second terminal) ---------------------------------------------
cd frontend
npm install
npm run dev                                            # http://localhost:5173, /api proxied to :8000
```

UI pages: **Overview** (KPIs + insights + coverage), **Forecast Explorer** (day/cutoff picker,
chart with band, table + CSV download), **Accuracy Analysis** (by-hour, by-horizon, histogram,
scatter), **Revisions** (how successive forecast publishes evolved), **Methodology**.

## Tests

```bash
python -m pytest backend/tests -q        # 21 tests: decision-time selection, DST, horizon, metrics, API
cd frontend && npm run typecheck && npm run lint && npm run build
```

GitHub Actions (`.github/workflows/ci.yml`) runs backend tests and frontend lint/typecheck/build on
push/PR.

## Refreshing data

```bash
python scripts/fetch_data.py                     # full refresh (actuals + forecasts)
python scripts/fetch_data.py --actuals-only      # refresh actuals only
# --forecasts-only, and --actuals-from/--actuals-to/--forecasts-from/--forecasts-to to override windows
```

The script streams from `https://data.elexon.co.uk/bmrs/api/v1/datasets/{FUELHH,WINDFOR}/stream`
with `publishDateTimeFrom/To` chunking, retries and backoff, validates UTC timestamps/dedupes,
and rewrites `data/*.parquet` + `data/ingest_report.json`. The committed snapshot is what the app
serves; re-run and commit to refresh. An optional guarded live-refresh endpoint exists behind
`ENABLE_LIVE_REFRESH=1`.

## Deployment (Vercel)

The repo deploys as one Vercel project with separate `frontend` (Vite) and `backend` (FastAPI)
services. The frontend is public on all non-API paths, and `/api/*` is routed to the public backend.
The backend build copies the committed snapshot into its service root and bundles it with the
FastAPI function. The browser calls the API through the same-origin `/api` path, so no service
binding is needed: bindings are for server-side service-to-service calls.

```bash
npm i -g vercel
vercel link                # create/attach the project
vercel deploy --prod       # builds both services and applies the public rewrites in vercel.json
```

`vercel.json` declares both services and routes `/api/*` to `backend` before routing other paths to
`frontend`. The backend uses `DATA_DIR` if configured; otherwise it reads the copied service-local
`data/` snapshot on Vercel and the repository-level `data/` snapshot during local development. The
Vite client uses same-origin `/api` requests; no API URL environment variable is needed for this
deployment.

Dev notes: `VITE_API_BASE` empty ⇒ same-origin/proxy; set it to the absolute API URL when served
separately. `.env.example` documents all env vars.

## Directory guide

```
backend/app/core       decision.py (cutoff/DST/horizon/latest-forecast), metrics.py, config.py, logging.py
backend/app/services   data_store.py (parquet loading/cache), analysis.py (endpoint payloads)
backend/app/api        routes.py (REST endpoints), backend/app/models/schemas.py (Pydantic)
backend/tests          pytest suite
frontend/src/pages     Overview.tsx, Explorer.tsx, Accuracy.tsx, Revisions.tsx, Methodology.tsx
frontend/src/{api,hooks,components,utils}
scripts/fetch_data.py  offline ingestion CLI
data/                  committed snapshot: actuals.parquet, actuals_60min.parquet,
                       forecasts.parquet, ingest_report.json
docs/                  ARCHITECTURE.md, ANALYSIS.md (real January-2026 findings), DEMO_SCRIPT.md
Dockerfile, frontend/Dockerfile, docker-compose.yml, .dockerignore
api/index.py (legacy single-service entrypoint), vercel.json (Vercel services and routing)
Makefile, .github/workflows/ci.yml, .env.example
```

## API summary

`/api/health`, `/api/meta`, `/api/forecast?day=&cutoff=`, `/api/accuracy/summary?cutoff=`,
`/api/accuracy/by-hour`, `/api/accuracy/by-horizon`, `/api/accuracy/distribution`,
`/api/accuracy/scatter`, `/api/revisions?day=&cutoff=`. Interactive docs at `/docs`. `cutoff` is
`HH:MM` Europe/London (D-1), default `09:00`; days are restricted to 2026-01-XX with 422
validation errors otherwise.

## Assumptions

- **Window:** delivery days January 2026 (per deliverable); actuals pulled 2026-01-01→2026-02-03
  (+2 days to catch late corrections), forecasts from publishes 2025-12-01→2026-02-02.
- **Cutoff semantics:** one cutoff clock time applies to every D-1 (default 09:00 London). Cutoffs
  posted in UI land on D-1 "yesterday" relative to the delivery day, in Europe/London; DST handled
  via `zoneinfo` (fold=0 for ambiguous autumn times; spring-gap times normalise per IANA rules).
  January itself is all-GMT so London and UTC coincide — the labelling is made explicit in the UI.
- **Alignment:** WINDFOR forecasts are hourly (startTime on the hour); FUELHH actuals are 30-min.
  Hourly actual = mean of the two half-hours (`halfHours` count kept to expose hours averaged from
  one half-hour). Error is compared at hourly granularity.
- **Revisions:** forecasts keep every (publishTime, startTime) revision; actuals dedupe by keeping
  the **latest** publishTime per startTime (BMRS late corrections win).
- **Data quality:** generation coerced, NaNs dropped (0 found), sanity range 0–30,000 MW enforced
  by the ingestion script (observed January max 17,756 MW, min 1,695 MW).
- **Metrics:** MAPE/normalised error computed only where actual ≥ 1,000 MW (≈5% of typical winter
  wind) to avoid divide-by-small blow-up; percentiles use linear interpolation.
- **Uncertainty band:** empirical percentile-of-error per horizon bucket, assuming error
  stationarity; not a probabilistic forecast model. Risk-adjusted wind = forecast + lowWindP10Delta
  (= forecast − P90 error) giving ≈90% historical coverage.
- **No invented data:** the app reads only the committed snapshot produced by the verified
  ingestion script against the live BMRS v1 API.

## Limitations & future work

- **Snapshot freshness:** data is frozen at ingest time; a scheduled re-run + commit (or enabling
  `ENABLE_LIVE_REFRESH`) is manual today. Natural follow-up: CI cron job that reuploads the
  snapshot weekly.
- **Wind-flow confound:** at a fixed cutoff, horizon and hour-of-day are correlated; per-bucket
  bands partly control for this, but a regime-aware calibration (rolling window) would help.
- Scope is national wind only; distribution-level or per-week granularity is out of scope.
- Inline forecast "no-fixtures" rule: if BMRS data were unreachable, the script fails loudly
  rather than fabricating; the UI shows loading/error/empty states accordingly.
- MAPE is quoted alongside normalised MAE; single-number "accuracy" is intentionally avoided.

## AI tools used

This project was built with the assistance of AI coding tools — **Freebuff/Codebuff** (end-to-end
scaffold, implementation, testing, docs) and **Claude** — under senior-engineer direction and
review. All domain logic is deterministic, unit-tested, and reproducible from the committed data.
