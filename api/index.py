"""Vercel Python serverless entrypoint.

Runs the FastAPI app from backend/app against the committed data snapshot
(data/*.parquet is bundled into the lambda via vercel.json includeFiles).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
for p in (str(BACKEND), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DATA_DIR", str(ROOT / "data"))

from app.main import app  # noqa: E402

handler = app  # ASGI callable consumed by the Vercel Python runtime
