#!/usr/bin/env python3
"""Zero-dependency HTTP + AI CLI API + SQLite Telemetry Server for Interaction Lab.

Serves compiled static site from dist/, exposes /api/categories and /api/search for
the `ilab` CLI and AI coding agents, serves dynamically configured /cli/ilab and
/SKILL.md, tracks server-side AI fetches + CLI queries, and ingests batched web
telemetry via POST /api/t into SQLite (WAL).
"""
from __future__ import annotations

import hashlib
import hmac
import http.server
import json
import os
import pathlib
import re
import secrets
import sys
import threading
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.db import TelemetryDB  # noqa: E402

DIST = ROOT / "dist"
DEFAULT_DB = ROOT / "data" / "telemetry.sqlite"
PATTERN_MD_RE = re.compile(r"^/patterns/([a-z0-9-]+)\.md$")
SPECIMEN_HTML_RE = re.compile(r"^/specimens/([a-z0-9-]+)\.html$")


def load_or_create_salt(db_path: pathlib.Path) -> bytes:
    env_salt = os.environ.get("IL_TELEMETRY_SALT")
    if env_salt:
        return env_salt.encode("utf-8")
    salt_file = db_path.parent / ".telemetry_salt"
    salt_file.parent.mkdir(parents=True, exist_ok=True)
    if salt_file.exists():
        return salt_file.read_text(encoding="utf-8").strip().encode("utf-8")
    token = secrets.token_hex(32)
    salt_file.write_text(token, encoding="utf-8")
    try:
        os.chmod(salt_file, 0o600)
    except OSError:
        pass
    return token.encode("utf-8")


def classify_ua(ua: str) -> str:
    low = (ua or "").lower()
    if not low:
        return "unknown"
    if "ilab-cli" in low:
        m = re.search(r"ilab-cli/[^\s]+\s*\(([^)]+)\)", ua or "", re.I)
        return f"ilab-CLI/{m.group(1)[:24]}" if m else "ilab-CLI"
    if "claudebot" in low or "anthropic" in low or "claude-code" in low:
        return "Claude/Anthropic"
    if "chatgpt" in low or "openai" in low or "gptbot" in low:
        return "OpenAI/ChatGPT"
    if "cursor" in low:
        return "Cursor"
    if "gemini" in low or "google-extended" in low or "antigravity" in low:
        return "Google/Gemini"
    if "perplexity" in low:
        return "Perplexity"
    if "curl/" in low or "wget/" in low or "httpie" in low or "python-requests" in low or "python-urllib" in low or "node" in low:
        return "CLI/HTTP-Agent"
    if "edg/" in low:
        return "Edge"
    if "chrome/" in low and "safari/" in low:
        return "Chrome"
    if "firefox/" in low:
        return "Firefox"
    if "safari/" in low:
        return "Safari"
    if "bot" in low or "spider" in low or "crawler" in low:
        return "Bot/Crawler"
    return "Other"


class RateLimiter:
    """In-memory per-visitor sliding-window limiter (default 150 hits/min)."""

    def __init__(self, max_hits: int = 150, window_sec: int = 60):
        self.max_hits = max_hits
        self.window_sec = window_sec
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, weight: int = 1) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_sec
        with self._lock:
            arr = self._hits.get(key)
            if arr is None:
                arr = []
                self._hits[key] = arr
            else:
                arr[:] = [t for t in arr if t >= cutoff]
            if len(arr) + weight > self.max_hits:
                return False
            arr.extend([now] * weight)
            if len(self._hits) > 5000:
                stale = [k for k, v in self._hits.items() if not v or v[-1] < cutoff]
                for k in stale:
                    del self._hits[k]
            return True


def load_catalog(dist_dir: pathlib.Path) -> Dict[str, Any]:
    return json.loads((dist_dir / "api" / "patterns.json").read_text(encoding="utf-8"))


def score_pattern(p: Dict[str, Any], q: str) -> int:
    ql = q.strip().lower()
    if not ql:
        return 1
    fields = [
        (p.get("name_cn", ""), 10),
        (p.get("name_en", ""), 9),
        (p.get("id", ""), 9),
        (" ".join(p.get("symptoms", [])), 8),
        (p.get("essence", ""), 5),
        (" ".join(p.get("drive", [])), 4),
        (" ".join(p.get("tech", [])), 4),
        (p.get("category", ""), 3),
    ]
    score = 0
    for txt, w in fields:
        if ql in txt.lower():
            score += w
    return score


class ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True


def make_handler(dist_dir: pathlib.Path, db: TelemetryDB, salt: bytes, limiter: RateLimiter, telemetry: bool = True):
    def get_catalog() -> Dict[str, Any]:
        # Always fresh if rebuilt without restart
        return load_catalog(dist_dir)

    class InteractionLabHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dist_dir), **kwargs)

        def log_message(self, fmt: str, *args) -> None:
            if os.environ.get("IL_QUIET") == "1":
                return
            super().log_message(fmt, *args)

        def _client_ip(self) -> str:
            cf = self.headers.get("CF-Connecting-IP")
            if cf:
                return cf.strip()
            xff = self.headers.get("X-Forwarded-For")
            if xff:
                return xff.split(",")[0].strip()
            return self.client_address[0] if self.client_address else "0.0.0.0"

        def _origin(self) -> str:
            proto = self.headers.get("X-Forwarded-Proto") or "http"
            host = self.headers.get("Host") or "127.0.0.1:8900"
            return f"{proto}://{host}"

        def _visitor_context(self) -> Tuple[str, str, str, str, str]:
            ip = self._client_ip()
            ua = self.headers.get("User-Agent", "")
            vh = hmac.new(salt, f"{ip}|{ua}".encode("utf-8"), hashlib.sha256).hexdigest()[:24]
            ua_fam = classify_ua(ua)
            country = (self.headers.get("CF-IPCountry") or self.headers.get("X-Country") or "").strip()[:8]
            ref = self.headers.get("Referer", "")
            ref_host = "direct"
            if ref:
                try:
                    ref_host = urllib.parse.urlparse(ref).hostname or "direct"
                except ValueError:
                    ref_host = "direct"
            return vh, ua_fam, country, ref_host, ua

        def _send_bytes(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(code, raw, "application/json; charset=utf-8")

        def end_headers(self) -> None:
            path = urllib.parse.urlsplit(self.path).path
            if path.endswith(".md") or path == "/llms.txt":
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
            if path.startswith("/api/") or path in ("/llms.txt", "/SKILL.md", "/") or path.endswith(".html"):
                self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            super().end_headers()

        def do_GET(self) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            if path == "/api/health":
                self._send_json(200, db.health_summary())
                return

            if path == "/api/categories":
                cat = get_catalog()
                counts: Dict[str, int] = {}
                for p in cat.get("patterns", []):
                    counts[p["category"]] = counts.get(p["category"], 0) + 1
                out = [dict(c, count=counts.get(c["id"], 0)) for c in cat.get("categories", [])]
                vh, ua_fam, country, ref_host, raw_ua = self._visitor_context()
                if telemetry and limiter.allow("ai:" + vh, 1):
                    try:
                        db.record_ai_fetch(
                            path=path, pattern_id=None, visitor_hash=vh, referrer_host=ref_host,
                            ua_family=ua_fam, country=country, raw_ua=raw_ua, event_type="ai_categories",
                        )
                    except Exception:
                        pass
                self._send_json(200, {"total_patterns": len(cat.get("patterns", [])), "categories": out})
                return

            if path == "/api/search":
                cat = get_catalog()
                q = (qs.get("q", [""])[0] or "").strip()
                category = (qs.get("category", [""])[0] or "").strip()
                drive = (qs.get("drive", [""])[0] or "").strip()
                pid_filter = (qs.get("id", [""])[0] or "").strip()

                items = cat.get("patterns", [])
                if pid_filter:
                    items = [p for p in items if p["id"] == pid_filter]
                if category and category != "all":
                    items = [p for p in items if p["category"] == category]
                if drive:
                    items = [p for p in items if drive in p.get("drive", [])]
                if q:
                    scored = [(score_pattern(p, q), p) for p in items]
                    scored = [x for x in scored if x[0] > 0]
                    scored.sort(key=lambda x: x[0], reverse=True)
                    items = [x[1] for x in scored]

                vh, ua_fam, country, ref_host, raw_ua = self._visitor_context()
                if telemetry and limiter.allow("ai:" + vh, 1):
                    try:
                        db.record_ai_fetch(
                            path=path,
                            pattern_id=pid_filter or None,
                            visitor_hash=vh,
                            referrer_host=ref_host,
                            ua_family=ua_fam,
                            country=country,
                            raw_ua=raw_ua,
                            event_type="search_query" if q else "ai_fetch",
                            extra_props={"query": q[:64], "category": category or None, "result_count": len(items)},
                        )
                    except Exception:
                        pass
                self._send_json(200, {"query": q, "category": category or "all", "count": len(items), "patterns": items})
                return

            # Dynamically inject deployed origin into downloadable /cli/ilab script
            if path == "/cli/ilab":
                cli_file = dist_dir / "cli" / "ilab"
                if cli_file.exists():
                    txt = cli_file.read_text(encoding="utf-8").replace("@@DEFAULT_URL@@", self._origin())
                    vh, ua_fam, country, ref_host, raw_ua = self._visitor_context()
                    if telemetry and limiter.allow("ai:" + vh, 1):
                        try:
                            db.record_ai_fetch(
                                path=path, pattern_id=None, visitor_hash=vh, referrer_host=ref_host,
                                ua_family=ua_fam, country=country, raw_ua=raw_ua, event_type="ai_fetch",
                            )
                        except Exception:
                            pass
                    self._send_bytes(200, txt.encode("utf-8"), "text/x-python; charset=utf-8")
                    return

            # Server-side AI Agent & machine-readable surface telemetry
            is_ai_surface = False
            pid: Optional[str] = None
            same_origin = self.headers.get("Sec-Fetch-Site") == "same-origin"

            if path in ("/llms.txt", "/SKILL.md"):
                is_ai_surface = True
            elif path == "/api/patterns.json" and not same_origin:
                is_ai_surface = True
            else:
                m_md = PATTERN_MD_RE.match(path)
                if m_md:
                    is_ai_surface = True
                    pid = m_md.group(1)
                else:
                    m_sp = SPECIMEN_HTML_RE.match(path)
                    if m_sp and not same_origin:
                        is_ai_surface = True
                        pid = m_sp.group(1)

            if is_ai_surface:
                vh, ua_fam, country, ref_host, raw_ua = self._visitor_context()
                if telemetry and limiter.allow("ai:" + vh, 1):
                    try:
                        db.record_ai_fetch(
                            path=path,
                            pattern_id=pid,
                            visitor_hash=vh,
                            referrer_host=ref_host,
                            ua_family=ua_fam,
                            country=country,
                            raw_ua=raw_ua,
                        )
                    except Exception:
                        pass

            super().do_GET()

        def do_POST(self) -> None:
            path = urllib.parse.urlsplit(self.path).path
            if path != "/api/t":
                self._send_json(404, {"error": "not_found"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json(400, {"error": "bad_length"})
                return
            if length <= 0 or length > 32_768:
                self._send_json(413, {"error": "payload_too_large"})
                return

            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                self._send_json(400, {"error": "invalid_json"})
                return

            events = data.get("events")
            if not isinstance(events, list) or not events or len(events) > 25:
                self._send_json(400, {"error": "invalid_events"})
                return

            vh, ua_fam, country, header_ref, _ = self._visitor_context()
            if telemetry and not limiter.allow("web:" + vh, len(events)):
                self._send_json(429, {"error": "rate_limited"})
                return

            if not telemetry:
                self._send_json(202, {"accepted": 0})
                return

            client_id = str(data.get("client_id") or "")[:64] or None
            session_id = str(data.get("session_id") or "")[:64] or None
            ref_host = str(data.get("referrer_host") or header_ref or "direct")[:128]

            written = db.write_web_batch(
                client_id=client_id,
                session_id=session_id,
                visitor_hash=vh,
                referrer_host=ref_host,
                ua_family=ua_fam,
                country=country,
                events=events,
            )
            self._send_json(202, {"accepted": written})

    return InteractionLabHandler


def main() -> None:
    if not DIST.exists() or not (DIST / "index.html").exists():
        sys.exit("dist/ missing — run `python3 build.py` first.")

    host = os.environ.get("IL_HOST", "127.0.0.1")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("IL_PORT", "8900"))
    db_path = pathlib.Path(os.environ.get("IL_DB_PATH", str(DEFAULT_DB)))

    db = TelemetryDB(db_path)
    salt = load_or_create_salt(db_path)
    limiter = RateLimiter(max_hits=150, window_sec=60)
    telemetry = os.environ.get("IL_TELEMETRY", "on").strip().lower() not in ("off", "0", "false", "no")
    handler = make_handler(DIST, db, salt, limiter, telemetry=telemetry)

    srv = ReusableThreadingHTTPServer((host, port), handler)
    print(f"Interaction Lab serving {DIST}")
    print(f"  Gallery : http://{host}:{port}/")
    print(f"  Skill   : http://{host}:{port}/SKILL.md")
    print(f"  CLI     : http://{host}:{port}/cli/ilab")
    print(f"  SQLite  : {db_path} (WAL)")
    print(f"  Telemetry: {'on' if telemetry else 'off (IL_TELEMETRY=off)'}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        srv.server_close()
        db.close()


if __name__ == "__main__":
    main()
