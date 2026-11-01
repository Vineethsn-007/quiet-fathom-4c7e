import { useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type { ForecastPoint } from "../api/types";
import ChartCard from "../components/ChartCard";
import { Empty, ErrorState, Loading } from "../components/States";
import { useFetch } from "../hooks/useFetch";
import { downloadCsv, toCsv } from "../utils/csv";
import { fmtDateTimeLondon, fmtMw, fmtNum } from "../utils/format";

const JAN_DAYS = Array.from({ length: 31 }, (_, i) => `2026-01-${String(i + 1).padStart(2, "0")}`);

export default function Explorer() {
  const [day, setDay] = useState("2026-01-15");
  const [cutoff, setCutoff] = useState("09:00");

  const state = useFetch(
    () => api.forecast(day, cutoff),
    [day, cutoff],
  );

  const table = useMemo(() => {
    if (state.status !== "ready") return [];
    return state.data.points.map((p) => ({
      // Target hour start shown in GMT (January == London time)
      startTime: p.startTime.replace("T", " ").replace(":00Z", " GMT"),
      actual: p.actual ?? "",
      halfHours: p.halfHours,
      forecast: p.forecast ?? "",
      publishTime: p.publishTime ? p.publishTime.replace("T", " ").replace(":00Z", " GMT") : "",
      horizonHours: p.horizonHours != null ? fmtNum(p.horizonHours, 1) : "",
      bandLow: p.bandLow != null ? fmtNum(p.bandLow) : "",
      bandHigh: p.bandHigh != null ? fmtNum(p.bandHigh) : "",
    }));
  }, [state]);

  const chartData = useMemo(() => {
    if (state.status !== "ready") return [];
    return state.data.points.map((p: ForecastPoint) => ({
      hour: p.startTime.slice(11, 16),
      actual: p.actual,
      forecast: p.forecast,
      bandLow: p.bandLow,
      bandHigh: Math.max(p.bandHigh ?? 0, p.forecast ?? 0),
    }));
  }, [state]);

  const dayLabel = (d: string) => fmtDateTimeLondon(`${d}T12:00Z`);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-4">
        <label className="flex flex-col text-sm">
          <span className="mb-1 font-medium text-slate-700">Delivery day (D)</span>
          <select
            value={day}
            onChange={(e) => setDay(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          >
            {JAN_DAYS.map((d) => (
              <option key={d} value={d}>{dayLabel(d)}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-sm">
          <span className="mb-1 font-medium text-slate-700">Decision cutoff (D-1, Europe/London)</span>
          <input
            type="time"
            value={cutoff}
            onChange={(e) => setCutoff(e.target.value || "09:00")}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
        </label>
        <button
          onClick={() => downloadCsv(`forecast_${day}_cutoff${cutoff.replace(":", "")}.csv`, toCsv(table, Object.keys(table[0] ?? { startTime: "" })))}
          disabled={table.length === 0}
          className="ml-auto rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40"
        >
          Download CSV
        </button>
      </div>

      <p className="text-xs text-slate-500">
        Cutoff {day ? `on ${day.slice(0, 8)}${day.slice(8)} − 1 day at ${cutoff} GMT` : ""} — the latest forecast
        revision published at or before that instant is shown (cutoff on D-1).
      </p>

      {state.status === "loading" ? (
        <Loading />
      ) : state.status === "error" ? (
        <ErrorState message={state.error} />
      ) : state.status === "empty" ? (
        <Empty message="No forecast was published at or before this cutoff for this day." />
      ) : (
        <>
          <ChartCard
            title={`Latest forecast at decision time vs actual — ${dayLabel(day)}`}
            subtitle={`Shaded band: empirical P10–P90 of error at the relevant horizon. Decision made on D-1 at ${cutoff} GMT; each hour uses the newest revision published by then.`}
          >
            <div className="h-80">
              <ResponsiveContainer>
                <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="hour" tick={{ fontSize: 11 }} tickMargin={8} />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                    label={{ value: "MW", angle: -90, position: "insideLeft" }}
                  />
                  <Tooltip
                    formatter={(value: number | string, name: string) => [fmtMw(Number(value)), name]}
                    labelFormatter={(l: string) => `${l} GMT`}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area dataKey="bandLow" stackId="band" stroke="none" fill="transparent" name="Band low (P10 actual)" />
                  <Area
                    dataKey="bandHigh"
                    stackId="band"
                    stroke="none"
                    fill="#94a3b8"
                    fillOpacity={0.25}
                    name="P10–P90 band"
                    legendType="none"
                  />
                  <Line type="monotone" dataKey="actual" stroke="#0f766e" strokeWidth={2} dot={false} name="Actual (hourly)" />
                  <Line type="monotone" dataKey="forecast" stroke="#1d6fd6" strokeWidth={2} dot={false} name="Latest forecast at cutoff" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {state.data.risk && (
            <div
              className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
              role="note"
            >
              <strong>Risk-adjusted wind for this day:</strong> pooling decision-time errors over all January
              days ({state.data.risk.nDays} days × 24h), 90% of historical wind outcomes were above
              <strong> forecast + {fmtMw(state.data.risk.lowWindP10Delta)}</strong> (P10 of actual)
              and 90% were within <strong>forecast + {fmtMw(state.data.risk.highWindP90Delta)}</strong>.
              Buying against the low-wind figure (forecast + {fmtMw(state.data.risk.lowWindP10Delta)}) leaves a
              buffer with ≈90% historical coverage against wind under-delivery.
            </div>
          )}

          <ChartCard title="Table view">
            <div className="max-h-96 overflow-auto rounded-lg border border-slate-200">
              <table className="min-w-full text-sm">
                <thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-600">
                  <tr>
                    {["Hour (GMT)", "Actual MW", "Forecast MW", "Published", "Horizon h", "Band low", "Band high"].map((h) => (
                      <th key={h} scope="col" className="px-3 py-2">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {table.map((r) => (
                    <tr key={r.startTime} className="hover:bg-slate-50">
                      <td className="px-3 py-1.5">{r.startTime}</td>
                      <td className="px-3 py-1.5 tabular-nums">{r.actual === "" ? "—" : fmtNum(Number(r.actual))}</td>
                      <td className="px-3 py-1.5 tabular-nums">{r.forecast === "" ? "—" : fmtNum(Number(r.forecast))}</td>
                      <td className="px-3 py-1.5">{r.publishTime || "—"}</td>
                      <td className="px-3 py-1.5 tabular-nums">{r.horizonHours}</td>
                      <td className="px-3 py-1.5 tabular-nums">{r.bandLow}</td>
                      <td className="px-3 py-1.5 tabular-nums">{r.bandHigh}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ChartCard>
        </>
      )}
    </div>
  );
}
