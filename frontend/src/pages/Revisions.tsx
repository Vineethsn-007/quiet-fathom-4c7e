import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type { RevisionsResponse } from "../api/types";
import ChartCard from "../components/ChartCard";
import { Empty, ErrorState, Loading } from "../components/States";
import { fmtDateTimeLondon, fmtMw } from "../utils/format";

const JAN_DAYS = Array.from({ length: 31 }, (_, i) => `2026-01-${String(i + 1).padStart(2, "0")}`);
const ALL_HOURS = Array.from({ length: 24 }, (_, i) => i);
const COLORS = ["#1d6fd6", "#16a34a", "#b45309", "#7c3aed", "#be123c", "#0f766e"];

/** Pick up to 4 target hours to compare revisions. */
type Selected = number[];

export default function Revisions() {
  const [day, setDay] = useState("2026-01-20");
  const [selected, setSelected] = useState<Selected>([0, 6, 12, 18]);
  const [state, setState] = useState<
    { status: "loading" } | { status: "error"; error: string } | { status: "ready"; data: RevisionsResponse }
  >({ status: "loading" });

  useEffect(() => {
    let alive = true;
    setState({ status: "loading" });
    api
      .revisions(day)
      .then((r) => alive && setState({ status: "ready", data: r }))
      .catch((e: Error) => alive && setState({ status: "error", error: e.message }));
    return () => {
      alive = false;
    };
  }, [day]);

  const chartRows = (() => {
    if (state.status !== "ready") return [];
    const d = state.data;
    const rows: Record<string, Record<string, number | string | null>> = {};
    for (const h of ALL_HOURS) {
      if (!selected.includes(h)) continue;
      const key = `${String(h).padStart(2, "0")}:00`;
      rows[key] = { hour: key };
      const startTime = `2026-${day.slice(5, 7)}-${day.slice(8, 10)}T${String(h).padStart(2, "0")}:00:00Z`;
      const actual = d.actuals[startTime];
      if (actual != null) rows[key]["actual"] = actual;
    }
    for (const pub of d.publishes) {
      for (const t of pub.targets) {
        const h = new Date(t.startTime).getUTCHours();
        if (!selected.includes(h)) continue;
        const key = `${String(h).padStart(2, "0")}:00`;
        if (!rows[key]) continue;
        rows[key][pub.publishTime] = t.forecast;
      }
    }
    return Object.values(rows);
  })();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-4">
        <label className="flex flex-col text-sm">
          <span className="mb-1 font-medium text-slate-700">Delivery day (D)</span>
          <select
            value={day}
            onChange={(e) => setDay(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {JAN_DAYS.map((d) => (
              <option key={d} value={d}>{fmtDateTimeLondon(`${d}T12:00Z`)}</option>
            ))}
          </select>
        </label>
        <div className="ml-auto flex flex-wrap gap-1" role="group" aria-label="Target hours to compare">
          {ALL_HOURS.map((h) => (
            <button
              key={h}
              onClick={() =>
                setSelected(
                  selected.includes(h)
                    ? selected.filter((x) => x !== h)
                    : [...selected, h].slice(0, 4),
                )
              }
              aria-pressed={selected.includes(h)}
              className={
                "rounded px-2 py-1 text-xs " +
                (selected.includes(h)
                  ? "bg-brand-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200")
              }
            >
              {String(h).padStart(2, "0")}:00
            </button>
          ))}
        </div>
      </div>

      {state.status === "loading" ? (
        <Loading />
      ) : state.status === "error" ? (
        <ErrorState message={state.error} />
      ) : (
        <>
          <ChartCard
            title={`Forecast revisions for ${fmtDateTimeLondon(`${day}T12:00Z`)}`}
            subtitle="Each line is one forecast publish (window: 96h before the 09:00 D-1 cutoff). Teal bold line = actual."
          >
            {chartRows.length === 0 ? (
              <Empty message="No revision data for this selection." />
            ) : (
              <div className="h-96">
                <ResponsiveContainer>
                  <LineChart data={chartRows} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="hour" tick={{ fontSize: 11 }} label={{ value: "Target hour (GMT)", position: "insideBottom", offset: -10 }} />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                      label={{ value: "MW", angle: -90, position: "insideLeft" }}
                    />
                    <Tooltip
                      formatter={(v: number | string, n: string) => [fmtMw(Number(v)), n.replace(/T.*$/, " (publish)")]}
                      labelFormatter={(l: string) => `${l} GMT`}
                    />
                    <Legend wrapperStyle={{ fontSize: 10 }} formatter={(v) => fmtDateTimeLondon(String(v))} />
                    {state.data.publishes.map((pub, i) => (
                      <Line
                        key={pub.publishTime}
                        dataKey={pub.publishTime}
                        stroke={COLORS[i % COLORS.length]}
                        strokeWidth={1.4}
                        dot={false}
                        connectNulls
                        type="monotone"
                      />
                    ))}
                    <Line dataKey="actual" stroke="#0f766e" strokeWidth={2.5} dot={false} name="Actual" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartCard>

          {state.data.publishes.length > 0 && (
            <p className="text-xs text-slate-500">
              {state.data.publishes.length} revisions shown: publishes from{" "}
              {fmtDateTimeLondon(state.data.publishes[0]?.publishTime)} to{" "}
              {fmtDateTimeLondon(state.data.publishes[state.data.publishes.length - 1]?.publishTime)} — all
              strictly before the decision cutoff {fmtDateTimeLondon(state.data.cutoffUtc)}.
            </p>
          )}
        </>
      )}
    </div>
  );
}
