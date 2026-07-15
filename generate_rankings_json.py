#!/usr/bin/env python3
"""
generate_rankings_json.py
==========================
Run this locally (with fp_proxy.py in the same folder) to produce
rankings.json and rankings-adp.json — the two static files the hosted
app reads.

Usage:
    python3 generate_rankings_json.py

Both files are generated from a single ECR fetch. The ECR page includes
an ADP column (avg), so no separate ADP fetch is needed. rankings.json
uses ECR rank; rankings-adp.json uses the ADP value as the rank.
Upload both files next to index.html on GitHub Pages together in one
commit to update the live app.
"""
import copy
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
        players, error, _raw_html = fp_proxy.get_rankings("ecr")
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    if error or not players:
        print(f"  FAILED: {error or 'no players returned'}")
        sys.exit(1)

    print(f"  OK — {len(players)} players fetched\n")

    now = datetime.now(timezone.utc).isoformat()

    # ECR file — rank is ECR rank
    ecr_payload = {"players": players, "updated": now, "source": "ecr"}
    with open("rankings.json", "w") as f:
        json.dump(ecr_payload, f, indent=None, separators=(",", ":"))
    print(f"  OK — {len(players)} players written to rankings.json (ECR)")

    # ADP file — promote adp to rank, fall back to ecr rank if no adp available
    adp_players = []
    missing_adp = 0
    for p in players:
        ap = copy.copy(p)
        if ap.get("adp"):
            ap["rank"] = round(ap["adp"])
        else:
            missing_adp += 1
        adp_players.append(ap)

    # Sort by ADP rank
    adp_players.sort(key=lambda p: p["rank"])
    # Re-assign sequential posRank based on ADP order
    adp_players = fp_proxy.assign_pos_ranks(adp_players)

    adp_payload = {"players": adp_players, "updated": now, "source": "adp"}
    with open("rankings-adp.json", "w") as f:
        json.dump(adp_payload, f, indent=None, separators=(",", ":"))
    print(f"  OK — {len(adp_players)} players written to rankings-adp.json (ADP)")
    if missing_adp:
        print(f"  Note: {missing_adp} players had no ADP data, ECR rank used as fallback")

    print("\nDone. Upload BOTH .json files together in one commit to update the live app.")
