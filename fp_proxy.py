#!/usr/bin/env python3
"""
Wreckineyez Mock Draft — FantasyPros Proxy
==========================================
Run this once before using the "Fetch live rankings" button in MockDraft.html.

  python3 fp_proxy.py

Requirements: Python 3.7+  (no pip installs needed — uses stdlib only)
"""

import json, gzip, re, sys, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

PORT = 5185
CACHE_SECONDS = 3600

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.fantasypros.com/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

ECR_URLS = [
    "https://www.fantasypros.com/nfl/rankings/consensus-cheatsheets.php",
    "https://www.fantasypros.com/nfl/rankings/half-point-ppr-cheatsheets.php",
]

_cache = {}   # source -> {data, fetched_at, raw_html}


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_url(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
        enc = resp.headers.get("Content-Encoding", "")
        if enc == "gzip":
            raw = gzip.decompress(raw)
        elif enc == "br":
            # stdlib has no brotli — ask server not to compress
            raw = gzip.decompress(raw)  # will fail gracefully
        return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Parsers — tried in order, first non-empty result wins
# ---------------------------------------------------------------------------

def parse_html(html, source):
    """Try every known pattern. Return list of player dicts or []."""

    for fn in [
        _try_var_ecrData,
        _try_var_adpData,
        _try_var_rankingsData,
        _try_any_js_array,
        _try_next_data,
        _try_html_table_with_attr,
        _try_html_table_generic,
    ]:
        try:
            players = fn(html)
            if players:
                print(f"  [parser] {fn.__name__} — {len(players)} players")
                return players
        except Exception as e:
            print(f"  [parser] {fn.__name__} failed: {e}")

    return []


# ── JS variable patterns ──

def _try_var_ecrData(html):
    m = re.search(r"var\s+ecrData\s*=\s*(\{.+?\});\s*(?:\n|var )", html, re.DOTALL)
    if not m: return []
    obj = json.loads(m.group(1))
    raw = obj.get("players") or obj.get("rankings") or []
    return [_norm(p, i) for i, p in enumerate(raw) if raw]

def _try_var_adpData(html):
    # ADP page uses adpData or similar
    m = re.search(r"var\s+(?:adpData|adp_data|ADP)\s*=\s*(\{.+?\});\s*(?:\n|var )", html, re.DOTALL)
    if not m: return []
    obj = json.loads(m.group(1))
    raw = obj.get("players") or obj.get("adp") or obj.get("data") or []
    return [_norm(p, i) for i, p in enumerate(raw) if raw]

def _try_var_rankingsData(html):
    m = re.search(r"var\s+rankingsData\s*=\s*(\[.+?\]);\s*\n", html, re.DOTALL)
    if not m: return []
    raw = json.loads(m.group(1))
    return [_norm(p, i) for i, p in enumerate(raw)]

def _try_any_js_array(html):
    """
    Scan every JS variable assignment that looks like an array of objects
    with player-like keys. Covers any variable name FantasyPros might use.
    """
    # Find all var x = [ ... ] blocks
    for m in re.finditer(r"var\s+\w+\s*=\s*(\[\s*\{.+?\}\s*\]);\s*\n", html, re.DOTALL):
        try:
            raw = json.loads(m.group(1))
            if not isinstance(raw, list) or not raw:
                continue
            first = raw[0]
            # Must look like a player object
            player_keys = {"player_name","name","player_id","position","pos",
                           "avg","rank","adp","player_team_id","team"}
            if len(player_keys & set(first.keys())) >= 2:
                result = [_norm(p, i) for i, p in enumerate(raw)]
                if result:
                    return result
        except Exception:
            continue
    return []

def _try_next_data(html):
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(\{.+?\})</script>', html, re.DOTALL)
    if not m: return []
    obj = json.loads(m.group(1))
    props = obj.get("props", {}).get("pageProps", {})
    for key in ("rankings", "players", "ecrData", "adpData", "data"):
        if key not in props: continue
        raw = props[key]
        if isinstance(raw, dict):
            raw = raw.get("players") or raw.get("rankings") or raw.get("data") or []
        if isinstance(raw, list) and raw:
            return [_norm(p, i) for i, p in enumerate(raw)]
    return []

def _try_html_table_with_attr(html):
    """FantasyPros tables often have data-player-id on <tr> tags."""
    rows = re.findall(r'<tr[^>]+data-player-id[^>]*>(.*?)</tr>', html, re.DOTALL)
    result = [r for r in (_parse_tr(row, i) for i, row in enumerate(rows)) if r]
    return result

def _try_html_table_generic(html):
    """
    Last resort: find the main rankings/adp table by its id, then parse rows.
    FantasyPros uses id="ranking-table" or id="adp-table" or class="tablesorter".
    """
    # Look for the table
    table_m = re.search(
        r'<table[^>]+(?:id="(?:ranking|adp|data)-table"|class="[^"]*tablesorter[^"]*")[^>]*>(.*?)</table>',
        html, re.DOTALL | re.IGNORECASE
    )
    if not table_m:
        # Fallback: any table with a thead containing "Player"
        table_m = re.search(
            r'<table[^>]*>.*?<th[^>]*>.*?Player.*?</th>.*?<tbody>(.*?)</tbody>',
            html, re.DOTALL | re.IGNORECASE
        )
    if not table_m:
        return []

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_m.group(1), re.DOTALL)
    result = [r for r in (_parse_tr(row, i) for i, row in enumerate(rows)) if r]
    return result


# ── Table row parser ──

def _parse_tr(row_html, idx):
    # Strip HTML tags for text extraction
    def text(s):
        return re.sub(r'<[^>]+>', '', s).strip()

    # Player name — look for fp-player-name class or player-name, or any <a> in a td
    name_m = (
        re.search(r'class="[^"]*fp-player-name[^"]*"[^>]*>([^<]+)', row_html) or
        re.search(r'class="[^"]*player-name[^"]*"[^>]*>\s*(?:<[^>]+>)*([^<]{3,})', row_html) or
        re.search(r'<td[^>]*>\s*<a[^>]+>([A-Z][a-z]+ [A-Z][a-z]+[^<]*)</a>', row_html)
    )
    if not name_m:
        return None
    name = text(name_m.group(1))
    if not name or len(name) < 4:
        return None

    # Position
    pos_m = (
        re.search(r'class="[^"]*position[^"]*"[^>]*>([A-Z]{1,3}\d*)', row_html) or
        re.search(r'<td[^>]*>\s*([A-Z]{2,3}\d?)\s*</td>', row_html)
    )
    pos_raw = pos_m.group(1).upper() if pos_m else ""
    pos_base = re.sub(r"\d+$", "", pos_raw)

    # Team
    team_m = (
        re.search(r'class="[^"]*player-team[^"]*"[^>]*>([A-Z]{2,4})', row_html) or
        re.search(r'class="[^"]*team[^"]*"[^>]*>([A-Z]{2,4})', row_html)
    )
    team = team_m.group(1) if team_m else ""

    # Rank / ADP — first numeric <td>
    nums = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', row_html)
    rank = int(float(nums[0])) if nums else idx + 1

    # Bye week — looks like a small integer (4-18) in a td
    bye = ""
    for n in nums[1:]:
        try:
            v = float(n)
            if 4 <= v <= 18 and v == int(v):
                bye = str(int(v))
                break
        except ValueError:
            pass

    return {
        "rank":    rank,
        "name":    name,
        "team":    team,
        "pos":     pos_base,
        "posRank": pos_raw,
        "bye":     bye,
        "tier":    1,
    }


# ── Normaliser for JSON player objects ──

def _norm(raw, idx):
    name = (raw.get("player_name") or raw.get("name") or
            (raw.get("player") or {}).get("name") or "")
    team = (raw.get("player_team_id") or raw.get("team") or
            (raw.get("player") or {}).get("team") or "")
    pos  = str(raw.get("player_position_id") or raw.get("position") or
               raw.get("pos") or (raw.get("player") or {}).get("position") or "").upper()
    pos_base = re.sub(r"\d+$", "", pos)

    # rank: ECR rank
    rank_raw = (raw.get("rank_ecr") or raw.get("rank") or raw.get("overall_rank") or
                raw.get("avg") or raw.get("adp") or idx + 1)
    try:
        rank = int(float(rank_raw))
    except (TypeError, ValueError):
        rank = idx + 1

    # adp: separate ADP field when available (avg column on ECR page)
    adp_raw = raw.get("avg") or raw.get("adp") or raw.get("adp_overall")
    try:
        adp = round(float(adp_raw), 1) if adp_raw else None
    except (TypeError, ValueError):
        adp = None

    tier_raw = raw.get("tier") or raw.get("tier_ecr") or 1
    try:
        tier = int(tier_raw)
    except (TypeError, ValueError):
        tier = 1

    bye = str(raw.get("player_bye_week") or raw.get("bye") or raw.get("bye_week") or "")

    return {
        "rank":    rank,
        "adp":     adp,
        "name":    name.strip(),
        "team":    str(team).strip().upper(),
        "pos":     pos_base,
        "posRank": pos,
        "bye":     bye,
        "tier":    tier,
    }


# ---------------------------------------------------------------------------
# Cache + orchestration
# ---------------------------------------------------------------------------

def assign_pos_ranks(players):
    """Fill in missing posRank values (e.g. 'RB5') by counting within each position."""
    counters = {}
    for p in sorted(players, key=lambda x: x["rank"]):
        if not p.get("posRank") or p["posRank"] == p["pos"]:
            pos = p["pos"]
            counters[pos] = counters.get(pos, 0) + 1
            p["posRank"] = pos + str(counters[pos])
    return players



def get_rankings(source):
    global _cache
    cached = _cache.get(source)
    if cached and (time.time() - cached["fetched_at"]) < CACHE_SECONDS:
        age = int(time.time() - cached["fetched_at"])
        print(f"  [cache] {source} — {len(cached['data'])} players, {age}s old")
        return cached["data"], None, cached.get("raw_html", "")

    urls = ECR_URLS
    last_err = None

    for url in urls:
        try:
            print(f"  [fetch] {url}")
            html = fetch_url(url)
            players = parse_html(html, source)
            if players:
                players = assign_pos_ranks(players)
                _cache[source] = {
                    "data": players,
                    "fetched_at": time.time(),
                    "raw_html": html,
                }
                print(f"  [ok] {len(players)} players")
                return players, None, html
            else:
                last_err = (
                    f"Fetched {url} but could not parse any players. "
                    f"Use /debug/{source} to inspect the raw page."
                )
                _cache[source] = {"data": [], "fetched_at": time.time(), "raw_html": html}
                print(f"  [warn] No players parsed")
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code} from {url}"
            print(f"  [http error] {e.code}")
        except Exception as e:
            last_err = str(e)
            print(f"  [error] {e}")

    return None, last_err or "Unknown error", ""


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] {fmt % args}")

    def do_OPTIONS(self):
        self._cors(200)
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path == "/ecr":
            source = path.lstrip("/")
            print(f"\n→ {source.upper()} requested")
            players, err, _ = get_rankings(source)
            self._cors(200 if players else 502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if players:
                body = json.dumps({"players": players, "source": source,
                                   "count": len(players),
                                   "fetched": datetime.now().isoformat()})
            else:
                body = json.dumps({"error": err})
            self.wfile.write(body.encode())

        elif path.startswith("/debug/"):
            # /debug/ecr or /debug/adp — returns a snippet of raw HTML
            # so you can see what the page actually contains
            source = path.split("/")[-1]
            if source != "ecr":
                self._cors(404); self.end_headers(); return

            print(f"\n→ DEBUG {source.upper()}")
            _, err, raw_html = get_rankings(source)

            self._cors(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            # Return useful diagnostic info
            snippet_size = 8000
            # Find script blocks in the HTML (where the data usually lives)
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', raw_html, re.DOTALL)
            big_scripts = [s[:2000] for s in scripts if len(s) > 200]

            body = json.dumps({
                "source": source,
                "html_length": len(raw_html),
                "parse_error": err,
                "html_start": raw_html[:snippet_size],
                "script_blocks": big_scripts[:5],
                "var_names": re.findall(r'var\s+(\w+)\s*=\s*[\[\{]', raw_html),
            }, indent=2)
            self.wfile.write(body.encode())

        elif path == "/health":
            self._cors(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "port": PORT}).encode())

        elif path == "/clearcache":
            _cache.clear()
            self._cors(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"cache cleared"}')

        else:
            self._cors(404); self.end_headers()
            self.wfile.write(b'{"error":"not found"}')

    def _cors(self, code):
        self.send_response(code)
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 58)
    print("  Wreckineyez Mock Draft — FantasyPros Proxy")
    print("=" * 58)
    print(f"  http://localhost:{PORT}/ecr      — ECR rankings")
    print(f"  http://localhost:{PORT}/adp      — ADP rankings")
    print(f"  http://localhost:{PORT}/debug/ecr — raw page diagnostic")
    print(f"  http://localhost:{PORT}/debug/adp — raw page diagnostic")
    print(f"  http://localhost:{PORT}/clearcache — force re-fetch")
    print()
    print("  Keep this window open while using MockDraft.html.")
    print("  Press Ctrl+C to stop.")
    print("=" * 58)
    print()
    try:
        server = HTTPServer(("localhost", PORT), Handler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Proxy stopped.")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n  ERROR: Port {PORT} is already in use.")
            print(f"  Run: lsof -ti:{PORT} | xargs kill")
        else:
            raise

if __name__ == "__main__":
    main()
