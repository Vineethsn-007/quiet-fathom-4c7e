"""Pydantic response models (typed API surface)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MetricSummaryOut(BaseModel):
    n: int
    bias: float
    mae: float
    rmse: float
    p50Abs: float
    p90Abs: float
    p95Abs: float
    mapePct: float | None = None
    normMae: float | None = None


class CoverageMeta(BaseModel):
    actuals: dict
    forecasts: dict
    generatedUtc: str | None = None
    source: str
    defaultCutoffLondon: str


class MetaOut(BaseModel):
    actuals: dict
    forecasts: dict
    generatedUtc: str | None = None
    source: str
    defaultCutoffLondon: str


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    details: dict = Field(default_factory=dict)


class CutoffInfo(BaseModel):
    london: str
    utc: str


class ForecastPoint(BaseModel):
    startTime: str
    actual: float | None = None
    halfHours: int = 0
    forecast: float | None = None
    publishTime: str | None = None
    horizonHours: float | None = None
    horizonBucket: str | None = None
    bandLow: float | None = None
    bandHigh: float | None = None


class RiskInfo(BaseModel):
    method: str
    lowWindP10Delta: float
    medianDelta: float
    highWindP90Delta: float
    nDays: int


class ForecastOut(BaseModel):
    day: str
    cutoff: CutoffInfo
    points: list[ForecastPoint]
    risk: RiskInfo | None = None


class AccuracySummaryOut(BaseModel):
    cutoff: str
    cutoffLondon: str
    metrics: MetricSummaryOut
    nHours: int
    nDaysWithPairs: int
    totalHoursJan: int
    insights: list[str]
    coverage: dict


class ByHourOut(BaseModel):
    hourLondon: int
    bias: float | None
    mae: float | None
    rmse: float | None
    meanActual: float | None
    meanForecast: float | None
    n: int


class ByHorizonOut(BaseModel):
    horizonBucket: str
    loHours: int
    hiHours: int
    n: int
    bias: float | None
    mae: float | None
    rmse: float | None


class DistributionOut(BaseModel):
    binsMw: list[float]
    histogram: dict
    percentiles: dict
    n: int


class ScatterPoint(BaseModel):
    startTime: str
    forecast: float
    actual: float
    horizonHours: float


class RevisionTarget(BaseModel):
    startTime: str
    forecast: float
    horizonHours: float


class RevisionPublish(BaseModel):
    publishTime: str
    targets: list[RevisionTarget]


class RevisionsOut(BaseModel):
    day: str
    cutoffUtc: str
    actuals: dict[str, float]
    publishes: list[RevisionPublish]


class ErrorOut(BaseModel):
    detail: str
