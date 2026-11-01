export const fmtMw = (v: number | null | undefined): string =>
  v == null ? "—" : new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 }).format(v) + " MW";

export const fmtNum = (v: number | null | undefined, digits = 0): string =>
  v == null ? "—" : new Intl.NumberFormat("en-GB", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(v);

export const fmtSignedMw = (v: number | null | undefined): string => {
  if (v == null) return "—";
  const s = new Intl.NumberFormat("en-GB", { signDisplay: "always", maximumFractionDigits: 0 }).format(v);
  return `${s} MW`;
};

export const fmtTime = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  // January winter: UTC == London (GMT); display clearly.
  const d = new Date(iso);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" }) + " GMT";
};

export const fmtDateTimeLondon = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  const d = new Date(iso);
  return (
    d.toLocaleString("en-GB", {
      weekday: "short",
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Europe/London",
    }) + " GMT"
  );
};

export const fmtHourRange = (iso: string | undefined | null): string => {
  if (!iso) return "—";
  const d = new Date(iso);
  const h1 = d.getUTCHours();
  return `${String(h1).padStart(2, "0")}:00–${String(h1).padStart(2, "0")}:59 GMT`;
};
