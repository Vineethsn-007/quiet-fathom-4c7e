export interface Meta {
  actuals: { first: string; last: string; resolutionMinutes: number; hoursNormalized: number };
  forecasts: { firstPublish: string; lastPublish: string; nPublishes: number; nRows: number; resolutionMinutes: number };
  generatedUtc: string | null;
  source: string;
  defaultCutoffLondon: string;
}

export interface Health {
  status: "ok" | "degraded";
  details: Record<string, unknown>;
}

export interface MetricSummary {
  n: number;
  bias: number;
  mae: number;
  rmse: number;
  p50Abs: number;
  p90Abs: number;
  p95Abs: number;
  mapePct: number | null;
  normMae: number | null;
}

export interface RiskInfo {
  method: string;
  /** Delta added to the latest forecast to get the P10 outcome of actual wind (90% historically above this). */
  lowWindP10Delta: number;
  medianDelta: number;
  highWindP90Delta: number;
  nDays: number;
}

export interface ForecastPoint {
  startTime: string;
  actual: number | null;
  halfHours: number;
  forecast: number | null;
  publishTime: string | null;
  horizonHours: number | null;
  horizonBucket: string | null;
  bandLow: number | null;
  bandHigh: number | null;
}

export interface ForecastResponse {
  day: string;
  cutoff: { london: string; utc: string };
  points: ForecastPoint[];
  risk: RiskInfo | null;
}

export interface AccuracySummary {
  cutoff: string;
  cutoffLondon: string;
  metrics: MetricSummary;
  nHours: number;
  nDaysWithPairs: number;
  totalHoursJan: number;
  insights: string[];
  coverage: Record<string, unknown>;
}

export interface ByHour {
  hourLondon: number;
  bias: number | null;
  mae: number | null;
  rmse: number | null;
  meanActual: number | null;
  meanForecast: number | null;
  n: number;
}

export interface ByHorizon {
  horizonBucket: string;
  loHours: number;
  hiHours: number;
  n: number;
  bias: number | null;
  mae: number | null;
  rmse: number | null;
}

export interface Distribution {
  binsMw: number[];
  histogram: { edges: number[]; counts: number[]; labels: string[] };
  percentiles: Record<string, number>;
  n: number;
}

export interface ScatterPoint {
  startTime: string;
  forecast: number;
  actual: number;
  horizonHours: number;
}

export interface RevisionsResponse {
  day: string;
  cutoffUtc: string;
  actuals: Record<string, number>;
  publishes: Array<{
    publishTime: string;
    targets: Array<{ startTime: string; forecast: number; horizonHours: number }>;
  }>;
}
