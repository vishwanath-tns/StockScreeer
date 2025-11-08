#!/usr/bin/env python3
"""
Small REST API tester for the scanner API.
Saves responses to chart_tool/tmp_{endpoint}.json and prints summaries.
"""
import os
import sys
import json
import traceback
from pathlib import Path

import requests

BASE = os.environ.get("REST_API_BASE", "http://127.0.0.1:5000").rstrip("/")
OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)


def save(name, data):
    p = OUT_DIR / f"tmp_{name}.json"
    with p.open("w", encoding="utf8") as fh:
        json.dump(data, fh, indent=2, default=str)
    print(f"Saved full response to: {p}")


def call(path, params=None, name=None):
    url = f"{BASE}{path}"
    name = name or path.strip("/").replace("/", "_")
    print(f"\n-> GET {url}  params={params}")
    try:
        r = requests.get(url, params=params, timeout=15)
    except Exception as e:
        print("Request failed:", repr(e))
        traceback.print_exc()
        return False
    print("Status:", r.status_code)
    try:
        body = r.json()
    except Exception:
        body = r.text
    if r.ok:
        print("OK. Response summary:")
        if isinstance(body, dict):
            # print lightweight summary for known shapes
            if "symbol" in body and "data" in body:
                print(f" symbol: {body.get('symbol')}, rows: {len(body.get('data') or [])}")
                if body.get("data"):
                    print(" first row keys:", list(body["data"][0].keys()))
            elif "data" in body:
                print(" rows:", len(body.get("data") or []))
                if body.get("data"):
                    print(" first row keys:", list(body["data"][0].keys()))
            else:
                print(" keys:", list(body.keys()))
        elif isinstance(body, list):
            print(" list length:", len(body))
        else:
            print(" body type:", type(body))
        save(name, body)
        return True
    else:
        print("ERROR response (non-2xx). Response body (raw):")
        print(r.text[:4000])
        if isinstance(body, dict):
            print("Returned JSON detail:", json.dumps(body, indent=2))
        save(name + "_error", {"status_code": r.status_code, "headers": dict(r.headers), "body": body})
        return False


def main():
    failures = 0
    # 1) /api/ohlcv
    ok = call("/api/ohlcv", params={"symbol": "SBIN", "days": 5}, name="ohlcv_sbin_5")
    if not ok:
        failures += 1

    # 2) /api/rsi
    ok = call("/api/rsi", params={"symbol": "SBIN", "period": 14, "days": 5}, name="rsi_sbin_5")
    if not ok:
        failures += 1

    # 3) /api/fractal_breaks
    ok = call("/api/fractal_breaks", params=None, name="fractal_breaks")
    if not ok:
        failures += 1

    print("\nSummary: failures =", failures)
    if failures:
        print("Check the saved files in:", OUT_DIR)
        sys.exit(2)
    print("All tests passed (2xx).")


if __name__ == "__main__":
    main()
