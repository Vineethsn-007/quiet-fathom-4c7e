import os
import sys

import pytest

# Ensure the backend package is importable whether pytest is run from repo root or backend/.
BACKEND_ROOT = __file__.rsplit("tests", 1)[0] if "tests" in __file__ else "backend/"
sys.path.insert(0, os.path.abspath(BACKEND_ROOT) if BACKEND_ROOT else "backend")


@pytest.fixture()
def sample_forecasts():
    from datetime import datetime, timezone

    T = datetime
    return [
        {"startTime": T(2026, 1, 15, 0, tzinfo=timezone.utc), "publishTime": T(2026, 1, 14, 2, 30, tzinfo=timezone.utc), "generation": 5000.0},
        {"startTime": T(2026, 1, 15, 0, tzinfo=timezone.utc), "publishTime": T(2026, 1, 14, 9, 0, tzinfo=timezone.utc), "generation": 6500.0},
        {"startTime": T(2026, 1, 15, 1, tzinfo=timezone.utc), "publishTime": T(2026, 1, 14, 2, 30, tzinfo=timezone.utc), "generation": 5500.0},
        {"startTime": T(2026, 1, 16, 0, tzinfo=timezone.utc), "publishTime": T(2026, 1, 15, 2, 30, tzinfo=timezone.utc), "generation": 7000.0},
    ]


@pytest.fixture(scope="session")
def _data_snapshot():
    """Skip tests needing the real snapshot if it is not present."""
    from app.services import data_store

    try:
        data_store.load_forecasts()
        data_store.load_actuals_hourly()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"data snapshot unavailable: {exc}")
