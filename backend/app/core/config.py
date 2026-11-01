"""Application configuration via environment variables (see .env.example)."""
from __future__ import annotations

import os
from datetime import timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel

LONDON_TZ = ZoneInfo("Europe/London")
UTC = timezone.utc


class Settings(BaseModel):
    app_name: str = "UK Wind Forecast Decision Support"
    data_dir: Path
    cors_origins: list[str] = ["*"]
    enable_live_refresh: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        cors = os.environ.get("CORS_ORIGINS", "*")
        origins = [o.strip() for o in cors.split(",") if o.strip()]
        backend_root = Path(__file__).resolve().parents[2]
        backend_data_dir = backend_root / "data"
        repository_data_dir = backend_root.parent / "data"
        data_dir = Path(
            os.environ.get(
                "DATA_DIR",
                backend_data_dir if backend_data_dir.is_dir() else repository_data_dir,
            )
        )
        return cls(
            data_dir=data_dir,
            cors_origins=origins or ["*"],
            enable_live_refresh=os.environ.get("ENABLE_LIVE_REFRESH", "0") == "1",
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


# Business defaults
DEFAULT_CUTOFF_LONDON = "09:00"
TIMEZONE = "Europe/London"

# Horizon buckets for error analysis (hours between startTime and publishTime)
HORIZON_BUCKETS = [
    ("0-6h", 0, 6),
    ("6-12h", 6, 12),
    ("12-18h", 12, 18),
    ("18-24h", 18, 24),
    ("24-36h", 24, 36),
    ("36-48h", 36, 48),
    ("48-72h", 48, 73),
]

# Normalised/percentage errors are computed only where actual >= this many MW,
# guarding against near-zero actuals (MA division).
NORMALISATION_FLOOR_MW = 1000.0
