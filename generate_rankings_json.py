#!/usr/bin/env python3
"""
generate_rankings_json.py
==========================
Run this locally (with fp_proxy.py in the same folder) to produce
rankings.json and rankings-adp.json — the two static files the hosted
version of the app reads.

Usage:
    python3 generate_rankings_json.py

This starts fp_proxy's fetch logic directly (no server needed), pulls
ECR and ADP from FantasyPros, and writes both JSON files to this folder.
Upload those two files next to index.html on GitHub Pages whenever you
want to refresh rankings — no app changes needed.
"""
import json
import sys
from datetime import datetime, timezone

try:
    import fp_proxy
except ImportError:
    print("ERROR: fp_proxy.py must be in the same folder as this script.")
    sys.exit(1)

def fetch_and_save(source, outfile):
    print(f"Fetching {source.upper()} rankings from FantasyPros...")
    try:
        players, error, _raw_html = fp_proxy.get_rankings(source)
    except Exception as e:
        print(f"  FAILED: {e}")
        return False
    if error or not players:
        print(f"  FAILED: {error or 'no players returned'}")
        return False
    payload = {
        "players": players,
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }
    with open(outfile, "w") as f:
        json.dump(payload, f, indent=None, separators=(",", ":"))
    print(f"  OK — {len(players)} players written to {outfile}")
    return True

if __name__ == "__main__":
    print("Generating static rankings files for the hosted app...\n")
    ok1 = fetch_and_save("ecr", "rankings.json")
    ok2 = fetch_and_save("adp", "rankings-adp.json")
    print()
    if ok1 or ok2:
        print("Done. Upload the generated .json file(s) to your hosting")
        print("provider, next to index.html, to update the live app.")
    else:
        print("Both fetches failed. Check your internet connection or")
        print("see fp_proxy.py's debug output for details.")
        sys.exit(1)
