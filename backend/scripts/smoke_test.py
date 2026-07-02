#!/usr/bin/env python3
"""Post-deploy smoke test."""

from __future__ import annotations

import argparse
import os
import sys
import time

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080").rstrip("/")


def run_checks(client: httpx.Client, *, deep: bool) -> None:
    health = client.get("/health")
    health.raise_for_status()

    health_db = client.get("/health", params={"db": True})
    health_db.raise_for_status()
    body = health_db.json()
    if body.get("db") != "ok":
        raise RuntimeError(f"Unexpected /health?db=1 body: {body}")

    home = client.get("/")
    home.raise_for_status()

    if deep:
        email = os.environ.get("SMOKE_EMAIL", "")
        password = os.environ.get("SMOKE_PASSWORD", "")
        if not email or not password:
            raise RuntimeError("SMOKE_EMAIL and SMOKE_PASSWORD required for --deep")
        login = client.post("/auth/login", json={"email": email, "password": password})
        login.raise_for_status()
        me = client.get("/api/me")
        me.raise_for_status()
        api_home = client.get("/api/home")
        api_home.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-deploy smoke test")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Login + authenticated API checks",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Retries while machine starts",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=10.0,
        help="Seconds between retries",
    )
    args = parser.parse_args()

    last_error: Exception | None = None
    for attempt in range(1, args.retries + 1):
        client = httpx.Client(base_url=BASE_URL, timeout=60.0, follow_redirects=True)
        try:
            run_checks(client, deep=args.deep)
            print(f"OK {BASE_URL}/health")
            print(f"OK {BASE_URL}/health?db=1")
            print(f"OK {BASE_URL}/")
            if args.deep:
                print(f"OK {BASE_URL}/api/me (deep)")
            return 0
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < args.retries:
                print(
                    f"Attempt {attempt}/{args.retries} failed: {exc}; retrying in {args.retry_delay}s",
                    file=sys.stderr,
                )
                time.sleep(args.retry_delay)
        finally:
            client.close()

    print(f"FAIL: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
