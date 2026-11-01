export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white p-10 text-slate-500" role="status">
      <span
        aria-hidden="true"
        className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent"
      />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-800" role="alert">
      <p className="font-semibold">Something went wrong</p>
      <p className="mt-1 text-sm">{message}</p>
    </div>
  );
}

export function Empty({ message = "No data available for this selection." }: { message?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-slate-500" role="status">
      {message}
    </div>
  );
}
