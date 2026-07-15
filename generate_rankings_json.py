#!/usr/bin/env python3
"""
generate_rankings_json.py
==========================
Run this locally (with fp_proxy.py in the same folder) to produce
rankings.json — the static file the hosted app reads.

Usage:
    python3 generate_rankings_json.py

Fetches ECR rankings from FantasyPros and writes rankings.json.
Upload it next to index.html on GitHub Pages to update the live app.
"""
import json
import sys
from datetime import datetime, timezone

try:
    import fp_proxy
except ImportError:
    print("ERROR: fp_proxy.py must be in the same folder as this script.")
    sys.exit(1)

if __name__ == "__main__":
    print("Fetching ECR rankings from FantasyPros...\n")
    try:
        players, error, _raw = fp_proxy.get_rankings("ecr")
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)
    if error or not players:
        print(f"  FAILED: {error or 'no players returned'}")
        sys.exit(1)
    payload = {"players": players, "updated": datetime.now(timezone.utc).isoformat(), "source": "ecr"}
    with open("rankings.json", "w") as f:
        json.dump(payload, f, indent=None, separators=(",", ":"))
    print(f"  OK — {len(players)} players written to rankings.json")
    print("\nDone. Upload rankings.json next to index.html to update the live app.")
