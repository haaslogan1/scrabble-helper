#!/usr/bin/env python3
"""Post-deploy smoke test."""

from __future__ import annotations

import os
import sys

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080").rstrip("/")


def main() -> int:
    client = httpx.Client(base_url=BASE_URL, timeout=60.0, follow_redirects=True)
    try:
        health = client.get("/health")
        health.raise_for_status()
        print(f"OK {BASE_URL}/health")

        if os.environ.get("DEV_AUTH_BYPASS", "").lower() == "true":
            me = client.get("/auth/me")
            me.raise_for_status()

        home = client.get("/")
        home.raise_for_status()
        print(f"OK {BASE_URL}/")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
