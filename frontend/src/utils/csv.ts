/** Minimal CSV serialisation for download links (RFC 4180-ish quoting). */
export function toCsv(rows: Record<string, unknown>[], columns: string[]): string {
  const esc = (v: unknown): string => {
    if (v == null) return "";
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const head = columns.map(esc).join(",");
  const body = rows.map((r) => columns.map((c) => esc(r[c])).join(","));
  return [head, ...body].join("\n");
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
