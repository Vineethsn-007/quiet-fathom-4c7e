import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.main import app  # noqa: E402

client = TestClient(app)


@pytest.mark.usefixtures("_data_snapshot")
class TestApi:
    def test_health(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] in ("ok", "degraded")

    def test_meta(self):
        r = client.get("/api/meta")
        assert r.status_code == 200
        body = r.json()
        assert body["source"].startswith("Elexon")
        assert body["defaultCutoffLondon"] == "09:00"

    def test_forecast_valid_day(self):
        r = client.get("/api/forecast", params={"day": "2026-01-15"})
        assert r.status_code == 200
        body = r.json()
        assert len(body["points"]) == 24
        assert body["cutoff"]["utc"].startswith("2026-01-14T09:00")

    def test_forecast_rejects_non_jan(self):
        r = client.get("/api/forecast", params={"day": "2026-02-01"})
        assert r.status_code == 422

    def test_forecast_rejects_junk_cutoff(self):
        r = client.get("/api/forecast", params={"day": "2026-01-15", "cutoff": "9am"})
        assert r.status_code == 422

    def test_accuracy_summary(self):
        r = client.get("/api/accuracy/summary")
        assert r.status_code == 200
        ms = r.json()["metrics"]
        assert ms["n"] > 0
        assert ms["mae"] >= 0 and ms["rmse"] >= ms["mae"]

    def test_by_hour_and_horizon(self):
        for ep in ("by-hour", "by-horizon"):
            r = client.get(f"/api/accuracy/{ep}")
            assert r.status_code == 200
            assert len(r.json()) > 0

    def test_distribution_and_scatter(self):
        r = client.get("/api/accuracy/distribution")
        assert r.status_code == 200
        assert r.json()["histogram"]["counts"]
        r = client.get("/api/accuracy/scatter")
        assert r.status_code == 200

    def test_revisions(self):
        r = client.get("/api/revisions", params={"day": "2026-01-20"})
        assert r.status_code == 200
        body = r.json()
        assert body["publishes"], "expected at least one publish before cutoff"
