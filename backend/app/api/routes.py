"""REST API routes. All endpoints validate input and return typed models."""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings

from app.models.schemas import (
    AccuracySummaryOut,
    ByHorizonOut,
    ByHourOut,
    DistributionOut,
    ForecastOut,
    HealthOut,
    MetaOut,
    RevisionsOut,
    ScatterPoint,
)
from app.services import analysis, data_store
from app.services.analysis import parse_cutoff

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def validate_day(day: str) -> date:
    try:
        d = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"invalid day {day!r}; use YYYY-MM-DD")
    if d.isoformat()[:4] != "2026" or d.month != 1:
        raise HTTPException(status_code=422, detail="day must be a January 2026 delivery day (YYYY-MM-01..31)")
    return d


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    settings = get_settings()
    details: dict = {"dataDir": str(settings.data_dir)}
    try:
        rows = len(data_store.load_forecasts())
        act = len(data_store.load_actuals_hourly())
        details.update({"forecastRows": rows, "actualHours": act})
        status = "ok"
    except Exception as exc:  # noqa: BLE001
        details["error"] = str(exc)
        status = "degraded"
    return HealthOut(status=status, details=details)


@router.get("/meta", response_model=MetaOut)
def meta() -> MetaOut:
    return MetaOut(**analysis.meta())


@router.get("/forecast", response_model=ForecastOut)
def forecast(
    day: str = Query(..., description="Delivery day, YYYY-MM-DD (January 2026)"),
    cutoff: str | None = Query(None, description="Decision cutoff on day D-1, HH:MM Europe/London; default 09:00"),
) -> ForecastOut:
    d = validate_day(day)
    try:
        ct = parse_cutoff(cutoff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return ForecastOut(**analysis.forecast_view(d, ct))
    except Exception as exc:  # noqa: BLE001
        log.exception("forecast failed")
        raise HTTPException(status_code=500, detail="internal error building forecast view") from exc


@router.get("/accuracy/summary", response_model=AccuracySummaryOut)
def accuracy_summary(cutoff: str | None = None) -> AccuracySummaryOut:
    try:
        ct = parse_cutoff(cutoff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return AccuracySummaryOut(**analysis.accuracy_summary(ct))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/accuracy/by-hour", response_model=list[ByHourOut])
def accuracy_by_hour(cutoff: str | None = None) -> list[ByHourOut]:
    try:
        ct = parse_cutoff(cutoff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [ByHourOut(**x) for x in analysis.accuracy_by_hour(ct)]


@router.get("/accuracy/by-horizon", response_model=list[ByHorizonOut])
def accuracy_by_horizon(cutoff: str | None = None) -> list[ByHorizonOut]:
    try:
        ct = parse_cutoff(cutoff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [ByHorizonOut(**x) for x in analysis.accuracy_by_horizon(ct)]


@router.get("/accuracy/distribution", response_model=DistributionOut)
def accuracy_distribution(cutoff: str | None = None) -> DistributionOut:
    try:
        ct = parse_cutoff(cutoff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DistributionOut(**analysis.accuracy_distribution(ct))


@router.get("/accuracy/scatter", response_model=list[ScatterPoint])
def accuracy_scatter(
    cutoff: str | None = None,
    maxPoints: int = Query(4000, ge=100, le=8000),
) -> list[ScatterPoint]:
    try:
        ct = parse_cutoff(cutoff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [ScatterPoint(**x) for x in analysis.accuracy_scatter(ct, max_points=maxPoints)]


@router.get("/revisions", response_model=RevisionsOut)
def revisions(
    day: str = Query(..., description="Delivery day, YYYY-MM-DD (January 2026)"),
    cutoff: str | None = None,
) -> RevisionsOut:
    d = validate_day(day)
    try:
        ct = parse_cutoff(cutoff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RevisionsOut(**analysis.revisions_view(d, ct))
