import { useState, type ReactNode } from "react";
import {
  Bar,  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer, 
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { api } from "../api/client";
import ChartCard from "../components/ChartCard";
import { Empty, ErrorState, Loading } from "../components/States";
import { useFetch } from "../hooks/useFetch";
import { fmtMw, fmtNum, fmtSignedMw } from "../utils/format";

/** Recharts Formatter-compatible numeric tooltip (value may be scalar or 2-uple). */
type ValueLike = number | string | Array<number | string>;
const tipMw = (v: ValueLike, n: string | number): [string, string] => [
  fmtMw(Number(Array.isArray(v) ? v[0] : v)),
  String(n),
];

export default function Accuracy() {
  const [cutoff, setCutoff] = useState("09:00");

  const byHour = useFetch(() => api.byHour(cutoff), [cutoff]);
  const byHorizon = useFetch(() => api.byHorizon(cutoff), [cutoff]);
  const distribution = useFetch(() => api.distribution(cutoff), [cutoff]);
  const scatter = useFetch(() => api.scatter(cutoff), [cutoff]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col text-sm">
          <span className="mb-1 font-medium text-slate-700">Decision cutoff (Europe/London)</span>
          <input
            type="time"
            value={cutoff}
            onChange={(e) => setCutoff(e.target.value || "09:00")}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
        </label>
        <p className="text-xs text-slate-500">
          All charts recomputed using the forecast revision available at this cutoff on D-1 for each January day.
        </p>
      </div>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard title="Error by hour of day (London = GMT in January)" subtitle="Mean signed error (bias) and MAE, MW">
          {block(byHour, (data) => (
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={data} margin={{ top: 5, right: 10, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="hourLondon" tick={{ fontSize: 11 }} tickMargin={6} label={{ value: "Hour (GMT)", position: "insideBottom", offset: -10 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v / 1000}k`} />
                  <Tooltip formatter={tipMw} labelFormatter={(l) => `${l}:00 GMT`} />
                  <Bar dataKey="bias" name="Bias (mean error)" radius={[2, 2, 0, 0]}>
                    {(byHour.status === "ready" ? byHour.data : []).map((d, i) => (
                      <Cell key={i} fill={(d.bias ?? 0) >= 0 ? "#16a34a" : "#dc2626"} />
                    ))}
                  </Bar>
                  <Bar dataKey="mae" name="MAE" fill="#1d6fd6" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ))}
        </ChartCard>

        <ChartCard title="Error by forecast horizon" subtitle="How accuracy degrades from 6h to 72h before delivery">
          {block(byHorizon, (data) => (
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={data} margin={{ top: 5, right: 10, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="horizonBucket" tick={{ fontSize: 11 }} tickMargin={6} label={{ value: "Horizon (startTime − publishTime)", position: "insideBottom", offset: -10 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v / 1000}k`} />
                  <Tooltip formatter={tipMw} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="mae" name="MAE" fill="#1d6fd6" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="bias" name="Bias" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ))}
        </ChartCard>

        <ChartCard title="Error distribution (all decision-time hours)" subtitle="Signed error, forecast − actual, MW">
          {block(distribution, (d) => (
            <>
              <div className="h-56">
                <ResponsiveContainer>
                  <BarChart data={d.histogram.labels.map((label: string, i: number) => ({ label, count: d.histogram.counts[i] }))} margin={{ top: 5, right: 10, bottom: 35, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 9 }} interval={0} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip labelFormatter={(l: string) => `Error bin ${l} MW`} formatter={(v: number) => [v, "Hours"]} />
                    <Bar dataKey="count" fill="#1d6fd6" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                P10 {fmtSignedMw(d.percentiles.p10)} · P50 {fmtSignedMw(d.percentiles.p50)} · P90{" "}
                {fmtSignedMw(d.percentiles.p90)} (n = {fmtNum(d.n)} hours)
              </p>
            </>
          ))}
        </ChartCard>
      </section>

      <ChartCard title="Actual vs forecast (scatter)" subtitle="Diagonal = perfect forecast; points above the line = wind lower than forecast">
        {block(scatter, (data) => (
          <div className="h-96">
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 10, right: 20, bottom: 25, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  type="number"
                  dataKey="actual"
                  name="Actual"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                  label={{ value: "Actual MW", position: "insideBottom", offset: -12 }}
                />
                <YAxis
                  type="number"
                  dataKey="forecast"
                  name="Forecast"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                  label={{ value: "Forecast MW", angle: -90, position: "insideLeft" }}
                />
                <ZAxis range={[30, 30]} />
                <Tooltip formatter={(v: number, n: string) => [fmtMw(v), n]} />
                <Scatter data={data} fill="#1d6fd6" fillOpacity={0.45} />
                <Scatter
                  line={{ stroke: "#94a3b8", strokeWidth: 2, strokeDasharray: "6 4" }}
                  data={[
                    { actual: 0, forecast: 0 },
                    { actual: 20000, forecast: 20000 },
                  ]}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        ))}
      </ChartCard>
    </div>
  );
}

function block<T>(state: { status: string; error?: string; data?: T }, render: (data: T) => ReactNode) {
  if (state.status === "loading") return <Loading label="Loading chart…" />;
  if (state.status === "error") return <ErrorState message={state.error ?? "error"} />;
  if (state.status === "empty") return <Empty />;
  return render(state.data as T);
}
