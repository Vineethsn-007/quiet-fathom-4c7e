const API_BASE = import.meta.env.VITE_API_BASE || "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(API_BASE + path, window.location.origin);
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== "" && v !== null) qs.set(k, v);
  }
  const full = url.pathname + (qs.toString() ? `?${qs.toString()}` : "") + url.search;
  let resp: Response;
  try {
    resp = await fetch(full, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError("Network error: cannot reach the API. Is the backend running?", 0);
  }
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore parse issues on error bodies */
    }
    throw new ApiError(detail, resp.status);
  }
  return (await resp.json()) as T;
}

import type {
  AccuracySummary,
  ByHorizon,
  ByHour,
  Distribution,
  ForecastResponse,
  Health,
  Meta,
  RevisionsResponse,
  ScatterPoint,
} from "./types";

export const api = {
  health: () => request<Health>("/api/health"),
  meta: () => request<Meta>("/api/meta"),
  forecast: (day: string, cutoff?: string) =>
    request<ForecastResponse>("/api/forecast", { day, cutoff }),
  accuracySummary: (cutoff?: string) => request<AccuracySummary>("/api/accuracy/summary", { cutoff }),
  byHour: (cutoff?: string) => request<ByHour[]>("/api/accuracy/by-hour", { cutoff }),
  byHorizon: (cutoff?: string) => request<ByHorizon[]>("/api/accuracy/by-horizon", { cutoff }),
  distribution: (cutoff?: string) => request<Distribution>("/api/accuracy/distribution", { cutoff }),
  scatter: (cutoff?: string) => request<ScatterPoint[]>("/api/accuracy/scatter", { cutoff }),
  revisions: (day: string, cutoff?: string) =>
    request<RevisionsResponse>("/api/revisions", { day, cutoff }),
};
