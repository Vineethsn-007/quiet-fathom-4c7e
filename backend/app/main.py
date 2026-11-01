"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.models.schemas import ErrorOut

configure_logging()
log = logging.getLogger(__name__)

app = FastAPI(
    title="UK Wind Forecast Decision Support",
    version="1.0.0",
    description=(
        "Latest-available national wind forecast at decision time (day-ahead power "
        "purchasing) and empirical forecast-accuracy analytics for January 2026. "
        "Data: Elexon BMRS (FUELHH, WINDFORECAST)."
    ),
)

settings = get_settings()
app.add_middleware(
   CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    log.info("client error: %s", exc)
    return JSONResponse(status_code=422, content=ErrorOut(detail=str(exc)).model_dump())


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error")
    return JSONResponse(
        status_code=500,
        content=ErrorOut(detail="internal error; check logs or contact support").model_dump(),
    )


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
