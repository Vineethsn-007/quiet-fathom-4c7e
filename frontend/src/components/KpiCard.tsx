interface Props {
  label: string;
  value: string;
  sub?: string;
  tooltip?: string;
  accent?: boolean;
}

export default function KpiCard({ label, value, sub, tooltip, accent }: Props) {
  return (
    <div
      className={
        "rounded-xl border bg-white p-4 shadow-sm " +
        (accent ? "border-brand-200 bg-brand-50" : "border-slate-200")
      }
      title={tooltip}
    >
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}
