#!/usr/bin/env python3
"""Validate PostgreSQL test schema and auth endpoints in CI."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DEV_AUTH_BYPASS", "true")
os.environ.setdefault("SESSION_SECRET", "test-secret")


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        print(f"skip: DATABASE_URL is not postgres ({database_url[:20]}...)")
        return 0

    try:
        from fastapi.testclient import TestClient

        from app.config import settings
        from app.main import app
        from tests.conftest import _reset_schema

        print("reset_schema...")
        _reset_schema()
        print("reset_schema ok")

        settings.dev_auth_bypass = True
        with patch("app.main.run_migrations", lambda: None):
            with TestClient(app) as client:
                checks = {
                    "health": client.get("/health"),
                    "health_db": client.get("/health", params={"db": True}),
                    "auth_me": client.get("/auth/me"),
                    "auth_config": client.get("/auth/config"),
                }
        for name, response in checks.items():
            print(f"{name}: {response.status_code} {response.text[:200]}")
            if response.status_code >= 400:
                print(f"::error title={name} failed::{name} returned {response.status_code}: {response.text}")
                return 1
        return 0
    except Exception as exc:
        print(f"::error title=postgres smoke exception::{type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
