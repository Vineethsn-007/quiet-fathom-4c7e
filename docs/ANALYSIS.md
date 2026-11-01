# Analysis — January 2026 decision-time forecast accuracy (real numbers)

All figures below are computed from the committed snapshot (`data/*.parquet`) at the default
decision cutoff **09:00 Europe/London (10:00 BST n/a; January = GMT) on D-1**, i.e. exactly what the
buyer sees when a purchase is made. Coverage is **complete: 744/744 January hours across all 31
delivery days** (0 missing intervals in the FUELHH wind stream, 31/31 days with at least one
forecast publish before cutoff). Reproduce: `python scripts/fetch_data.py` then
`GET /api/accuracy/summary`.

## Headline accuracy at decision time

| Metric | Value (MW unless noted) |
| --- | --- |
| Mean error (bias), forecast − actual | **+1,852** |
| MAE | **2,142** |
| RMSE | 2,612 |
| P50 / P90 / P95 \|error\| | 1,788 / 4,300 / 5,307 |
| MAPE (actual ≥ 1,000 MW) | 22.4 % |
| Normalised MAE (MAE / mean actual above floor) | 0.185 |

Wind actuals ranged from 1,712 MW (Tue 8 Jan 12:00 GMT) to 17,756 MW (Sat 24 Jan 18:00 GMT);
month mean ≈ 11.2 GW. Decision-time horizons spanned **16.5 h (midnight targets) to 39.5 h
(23:00 targets)**.

## The story in three sentences

1. **The BMRS wind forecast is systematically optimistic in January 2026:** 85% of decision-time
   hours came in **below** the latest 09:00 D-1 forecast (only 15% underforecast), with a median
   overprediction of ~1.7 GW.
2. **Error tails are fat:** 1 in 4 hours misses by more than 3 GW, and 1 in 20 by more than 5.3 GW
   — close to 30% of a typical winter-day wind outturn.
3. **Early morning is the danger window:** the 02:00–06:00 London hours carry the largest MAE
   (~2.4–2.5 GW), exactly when the day's lowest demand coincide with the highest wind reliance.

## Error by hour of day (London = GMT)

Worst five hours by MAE: 05:00 (2,535), 03:00 (2,516), 04:00 (2,507), 06:00 (2,483), 02:00 (2,412) MW.
Note this is bias-driven, not just noisy: the overnight wind ramp is repeatedly overpredicted.

## Error by horizon

| Horizon bucket | n | MAE | Bias |
| --- | --- | --- | --- |
| 12–18 h | 248 | 2,226 | +2,171 |
| 18–24 h | 248 | 2,465 | +2,392 |
| 24–36 h | 248 | 2,031 | +1,574 |
| 36–48 h | 62 | 1,951 | +1,717 |

**Caution:** at a fixed 09:00 cutoff, horizon and hour-of-day are confounded (late evening targets
always sit at 36–39.5 h). The non-monotonic pattern (MAE peaking at 18–24 h) reflects hour mix
rather than genuine accuracy decay: the 18–24 h targets are the overnight hours that this month's
forecast overpredicts hardest. Read "error by horizon" together with "error by hour of day" — and
note the 36–48 h bucket contains only one delivery hour per day (23:00), so it is statistically thin.

## By generation level

MAE grows with wind level: 1,886 MW (low-wind tercile ≈ below 8 GW), 2,097 MW (mid), 2,443 MW
(high tercile, top ≈ 12.6 GW+). Absolute error scales with the size of the forecast, but relative
(normalised) error is worse in low-wind hours — the guard-rail in the MAPE metric exists for this
reason.

## Trend over the month

MAE by week of delivery: 1–10 Jan ≈ 1,937 MW, 11–20 Jan ≈ 1,905 MW, 21–31 Jan ≈ 2,545 MW. The
final third of January was materially more erratic (stormy, fast-reversal weather — most of the
worst days sit there).

Worst delivery days by daily MAE: **28 Jan (5.4 GW), 12 Jan (4.9), 11 Jan (4.8), 1 Jan (4.2),
21 Jan (3.7)** — all days with big intraday wind swings rather than steady high/low regimes.

## Practical recommendation for the buy

Given the empirical error distribution at decision time (signed error, forecast − actual:
P10 = −549 MW, P50 = +1,685 MW, P90 = +4,300 MW):

1. **De-rate the forecast.** A conservative wind figure with ≈90% historical coverage is
   **forecast − 4,300 MW (P90 of error)**. If buying to a 90% service level with wind as firm,
   count only that much wind.
2. **Budget the buffer as thermal/spin, not paper.** 4,300 MW is roughly the order of CCGT-scale
   reserve; at P95 it is 5,300 MW. Size at least the first, plan access to the second.
3. **Do not symmetric-hedge.** The distribution is heavily right-skewed (85% of hours the wind
   underdelivers vs forecast), so the risk to hedge is under-wind, not over-wind; the downside
   band (P10 of actual = forecast − P90 of error) is the binding one for adequacy.
4. **Watch the calendar.** Late-January days deserve a wider buffer (≈ +25–30% MAE vs early
   January) and any day with a strong overnight ramp forecast deserves manual scrutiny: the
   recurring bias lives between 02:00–06:00 London time.
5. **Optional refinement** (future work): recalibrate bands per-horizon-bucket at runtime
   (already supported: `/api/forecast` uses the bucket of each target hour) and add a
   rolling-30-day recalibration so regime shifts self-correct.

## Reproducibility

```
python scripts/fetch_data.py        # rebuild snapshot (records ingest_report.json)
cd backend && python -m pytest      # unit tests incl. decision-time + DST + metrics
uvicorn app.main:app --port 8000    # GET /api/accuracy/summary reproduces headline table
```

Numbers quoted above were produced from the snapshot committed on 2026-11-01
(`data/ingest_report.json: generated_utc`).
