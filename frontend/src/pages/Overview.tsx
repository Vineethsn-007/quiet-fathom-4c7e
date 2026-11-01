import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AccuracySummary, Meta } from "../api/types";
import KpiCard from "../components/KpiCard";
import { Loading, ErrorState, Empty } from "../components/States";
import ChartCard from "../components/ChartCard";
import { fmtDateTimeLondon, fmtMw, fmtNum } from "../utils/format";

export default function Overview() {
  const [summary, setSummary] = useState<AccuracySummary | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all([api.accuracySummary(), api.meta()])
      .then(([s, m]) => {
        if (!alive) return;
        setSummary(s);
        setMeta(m);
        setError(null);
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  if (loading) return <Loading label="Loading January 2026 analysis…" />;
  if (error) return <ErrorState message={error} />;
  if (!summary || !meta) return <Empty />;

  const m = summary.metrics;
  const a = meta.actuals;
  const f = meta.forecasts;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">January 2026 — headline accuracy</h2>
        <p className="mt-1 text-sm text-slate-600">
          Forecast accuracy at decision time: for each delivery day, the latest forecast available on
          D-1 at the cutoff ({summary.cutoffLondon} Europe/London — the wind used when the purchase is made).
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="MAE" value={fmtMw(m.mae)} sub="mean absolute error" tooltip="Average size of the forecast miss (MW) across all decision-time hours." />
        <KpiCard label="RMSE" value={fmtMw(m.rmse)} sub="root mean square error" accent tooltip="Penalises large misses; RMSE > MAE means occasional large errors exist." />
        <KpiCard label="Bias (mean error)" value={fmtMw(m.bias)} sub={m.bias >= 0 ? "forecasts run high" : "forecasts run low"} tooltip="Mean of forecast − actual. Negative = wind underforecast/secured buffer too big." />
        <KpiCard label="P95 absolute error" value={fmtMw(m.p95Abs)} sub="worst 5% of hours miss by more" tooltip="95th percentile of |error|: a risk ceiling for the wind forecast at decision time." />
      </div>

      <ChartCard title="Key insights" subtitle="Computed from the January 2026 snapshot (decision-time forecasts)">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
          {summary.insights.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
          <li>
            Residual demand to buy = demand − wind. Underforecasting wind (negative bias) causes
            over-buying thermal; P95/P90 error bands size a prudent wind buffer.
          </li>
        </ul>
      </ChartCard>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard title="Data coverage — actuals (FUELHH, WIND)">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div><dt className="text-slate-500">Window</dt><dd className="font-medium">{fmtDateTimeLondon(a.first)} → {fmtDateTimeLondon(a.last)}</dd></div>
            <div><dt className="text-slate-500">Resolution</dt><dd className="font-medium">{a.resolutionMinutes} min (30-min wind data, aligned to hourly averages)</dd></div>
            <div><dt className="text-slate-500">Hours normalised</dt><dd className="font-medium">{fmtNum(a.hoursNormalized)}</dd></div>
          </dl>
        </ChartCard>
        <ChartCard title="Data coverage — forecasts (WINDFOR)">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div><dt className="text-slate-500">Publish window</dt><dd className="font-medium">{fmtDateTimeLondon(f.firstPublish)} → {fmtDateTimeLondon(f.lastPublish)}</dd></div>
            <div><dt className="text-slate-500">Publishes / rows</dt><dd className="font-medium">{fmtNum(f.nPublishes)} publishes · {fmtNum(f.nRows)} rows</dd></div>
            <div><dt className="text-slate-500">Resolution</dt><dd className="font-medium">{f.resolutionMinutes} min revised every ~3h (up to ~72h ahead)</dd></div>
            <div><dt className="text-slate-500">Snapshot generated</dt><dd className="font-medium">{fmtDateTimeLondon(meta.generatedUtc)}</dd></div>
          </dl>
        </ChartCard>
      </div>

      <p className="text-xs text-slate-500">
        Evaluated {summary.nHours} of {summary.totalHoursJan} January hours across{" "}
        {summary.nDaysWithPairs} delivery days. Times UTC unless labelled London/GMT (identical for January).
      </p>
    </div>
  );
}
