# Demo script (max 10 minutes — recorded video)

Timebox markers assume the app is already deployed (Vercel URL) or running via
`docker compose up` / dev servers. Pre-load the pages in tabs; the data is static
so nothing will surprise you.

## Part 1 — Customer pitch, value-first (≤ 5 min)

| Time | On screen | Say / do |
| --- | --- | --- |
| 0:00–0:30 | Overview page | "Every day your day-ahead wind purchase rests on one number: how much wind will actually blow tomorrow. This app shows what that forecast was worth at the moment you bought — and what it cost you when it was wrong." Point at the four KPI cards: **MAE 2,142 MW, RMSE 2,612 MW, bias +1,852 MW, P95 5,307 MW**. |
| 0:30–1:15 | Overview insights | Read insight 1 out loud: *"Forecasts over-forecast wind by ~1.9 GW on average; in the worst 5% of hours they miss by more than 5.3 GW."* Translation for the trading desk: "Trust the BMRS number relative to wind, and you were short thermal on most January mornings — that risk lands on your balancing exposure." |
| 1:15–2:15 | Forecast Explorer | Pick **15 Jan, cutoff 09:00**. Walk the chart: blue = forecast published at/before 09:00 the day before; green = what actually blew; grey band = the ±P10/P90 envelope from history. Hover 01:00: forecast 15.5 GW vs actual 14.4 GW — spot the overnight overprediction pattern. |
| 2:15–3:15 | Forecast Explorer band + risk note | Scroll to the amber "risk-adjusted wind" note: **forecast − 4.3 GW ≈ 90%-confirmed wind**. "If the trader had de-rated the forecast by 4.3 GW, they'd have covered ~90% of January's decision-time hours." Toggle cutoff to 05:00 and back — show the forecast revision (selection logic) shifting. |
| 3:15–4:00 | Accuracy Analysis | Show error-by-hour bar chart — early morning hours stick out (2–6 AM, MAE ≈ 2.4–2.5 GW). Point at error-by-horizon and the distribution histogram: right-skewed (85% of hours wind < forecast). |
| 4:00–4:45 | Revisions | Show 20 Jan: successive publishes converging on the actual across the day. "This is the information flow your team actually had." |
| 4:45–5:00 | Overview again | Close with the recommendation: "Hold a ≥4.3 GW wind buffer (P90), inspect the 02:00–06:00 ramp hours, and treat late-January as your stress week. That's the app's whole point: quantified trust in the forecast at decision time." |

## Part 2 — Technical walkthrough (≤ 5 min)

| Time | On screen | Say / do |
| --- | --- | --- |
| 5:00–5:40 | docs/ARCHITECTURE.md diagram | One sentence: "BMRS data is ingested once into a committed parquet snapshot; the FastAPI service computes decision-time analytics from it; a React SPA renders the five pages. The deployed app never calls Elexon live." |
| 5:40–6:30 | Code: `backend/app/core/decision.py` | Show `select_latest_forecast` (greatest `publishTime ≤ cutoff` per target hour) and `cutoff_utc_for_delivery` with zoneinfo DST handling. Emphasise "this is the unit-tested core: `pytest backend/tests` — 21 tests". |
| 6:30–7:10 | Code: `backend/app/core/metrics.py` | Point out bias/MAE/RMSE, percentile interpolation, and the MAPE ≥ 1,000 MW floor ("guard against near-zero actuals" — 1000 MW ≈ 5% of capacity). Show band inversion: P10(actual) = forecast − P90(error). |
| 7:10–7:50 | scripts/fetch_data.py + data/ | Show chunked fetching, retries/backoff, dedupe-latest-revision, sanity assertions (0–30,000 MW), `ingest_report.json` coverage stats. Mention it's a CLI: `python scripts/fetch_data.py [--actuals-only|--forecasts-only]`. |
| 7:50–8:30 | repository tour | Fast layout: `backend/app/{api,services,models,core}`, `backend/tests`, `frontend/src/{pages,api,hooks,components,utils}`, `docs/`. Mention npm/py scripts, Makefile targets, GitHub Actions CI (3 jobs: backend tests, typecheck+build, lint). |
| 8:30–9:15 | Docs + analysis | Flip through docs/ANALYSIS.md (real numbers: full 744/744 coverage, worst hours, worst days, buffer recommendation) and Methodology page in-app: "every metric has a plain-English definition; no black boxes". |
| 9:15–10:00 | Deployment reality | "One command locally: `docker compose up --build` (backend on :8000, frontend on :5174). On Vercel: static SPA + one Python serverless function reading the same committed data via `vercel.json` rewrites — steps in the README." End: "Everything runs offline from the committed snapshot; refreshing data is one command." |
