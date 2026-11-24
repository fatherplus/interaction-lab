"""SQLite (WAL) telemetry storage for Interaction Lab."""
from __future__ import annotations

import datetime
import json
import pathlib
import sqlite3
import threading
import time
from typing import Any, Dict, Iterable, Optional

ALLOWED_WEB_EVENTS = frozenset({
    "page_view",
    "search_query",
    "filter_change",
    "specimen_interact",
    "specimen_open",
    "knob_adjust",
    "copy_prompt",
    "copy_code",
    "export_bundle",
})

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ts            INTEGER NOT NULL,
  day           TEXT NOT NULL,
  event_type    TEXT NOT NULL,
  source        TEXT NOT NULL DEFAULT 'web',
  pattern_id    TEXT,
  category      TEXT,
  client_id     TEXT,
  session_id    TEXT,
  visitor_hash  TEXT NOT NULL,
  referrer_host TEXT,
  ua_family     TEXT,
  country       TEXT,
  props_json    TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_day_type    ON events(day, event_type);
CREATE INDEX IF NOT EXISTS idx_events_pattern     ON events(pattern_id, event_type);
CREATE INDEX IF NOT EXISTS idx_events_visitor_day ON events(visitor_hash, day);
CREATE INDEX IF NOT EXISTS idx_events_session     ON events(session_id);

CREATE TABLE IF NOT EXISTS sessions (
  session_id     TEXT PRIMARY KEY,
  client_id      TEXT,
  visitor_hash   TEXT NOT NULL,
  first_ts       INTEGER NOT NULL,
  last_ts        INTEGER NOT NULL,
  day            TEXT NOT NULL,
  referrer_host  TEXT,
  ua_family      TEXT,
  country        TEXT,
  page_views     INTEGER NOT NULL DEFAULT 0,
  interacts      INTEGER NOT NULL DEFAULT 0,
  copies         INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_day    ON sessions(day);
CREATE INDEX IF NOT EXISTS idx_sessions_client ON sessions(client_id);

CREATE VIEW IF NOT EXISTS v_pattern_leaderboard AS
SELECT
  pattern_id,
  COALESCE(MAX(category), '') AS category,
  COUNT(DISTINCT visitor_hash) AS unique_users,
  SUM(CASE WHEN event_type = 'specimen_interact' THEN 1 ELSE 0 END) AS interacts,
  SUM(CASE WHEN event_type = 'specimen_open'     THEN 1 ELSE 0 END) AS opens,
  SUM(CASE WHEN event_type = 'knob_adjust'       THEN 1 ELSE 0 END) AS knob_adjusts,
  SUM(CASE WHEN event_type = 'copy_prompt'       THEN 1 ELSE 0 END) AS copy_prompts,
  SUM(CASE WHEN event_type = 'copy_code'         THEN 1 ELSE 0 END) AS copy_codes,
  SUM(CASE WHEN event_type = 'ai_fetch'          THEN 1 ELSE 0 END) AS ai_fetches
FROM events
WHERE pattern_id IS NOT NULL AND pattern_id != ''
GROUP BY pattern_id;

CREATE VIEW IF NOT EXISTS v_daily_overview AS
SELECT
  day,
  COUNT(*) AS total_events,
  COUNT(DISTINCT visitor_hash) AS unique_visitors,
  SUM(CASE WHEN source = 'server_ai' THEN 1 ELSE 0 END) AS ai_fetches,
  SUM(CASE WHEN event_type = 'specimen_interact' THEN 1 ELSE 0 END) AS interacts,
  SUM(CASE WHEN event_type IN ('copy_prompt', 'copy_code', 'export_bundle') THEN 1 ELSE 0 END) AS copies
FROM events
GROUP BY day
ORDER BY day DESC;

CREATE VIEW IF NOT EXISTS v_search_gaps AS
SELECT
  json_extract(props_json, '$.query') AS query,
  COUNT(*) AS searches,
  MIN(CAST(json_extract(props_json, '$.result_count') AS INTEGER)) AS min_results
FROM events
WHERE event_type = 'search_query' AND props_json IS NOT NULL
GROUP BY query
ORDER BY searches DESC;
"""


def day_from_ts(ts_ms: int) -> str:
    return datetime.datetime.fromtimestamp(ts_ms / 1000.0, tz=datetime.timezone.utc).strftime("%Y-%m-%d")


class TelemetryDB:
    def __init__(self, db_path: pathlib.Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA busy_timeout=5000;")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def write_web_batch(
        self,
        *,
        client_id: Optional[str],
        session_id: Optional[str],
        visitor_hash: str,
        referrer_host: str,
        ua_family: str,
        country: str,
        events: Iterable[Dict[str, Any]],
    ) -> int:
        now_ms = int(time.time() * 1000)
        rows = []
        pv_inc = 0
        int_inc = 0
        copy_inc = 0
        min_ts = now_ms
        max_ts = now_ms

        for ev in events:
            ev_type = str(ev.get("event_type") or "")
            if ev_type not in ALLOWED_WEB_EVENTS:
                continue
            raw_ts = ev.get("ts")
            ts = int(raw_ts) if isinstance(raw_ts, (int, float)) and abs(now_ms - int(raw_ts)) < 86_400_000 else now_ms
            min_ts = min(min_ts, ts)
            max_ts = max(max_ts, ts)
            day = day_from_ts(ts)
            pid = str(ev["pattern_id"])[:80] if ev.get("pattern_id") else None
            cat = str(ev["category"])[:64] if ev.get("category") else None
            props_raw = json.dumps(ev.get("props") or {}, ensure_ascii=False, separators=(",", ":"))
            if len(props_raw.encode("utf-8")) > 1024:
                props_raw = json.dumps({"truncated": True})

            rows.append((
                ts, day, ev_type, "web", pid, cat,
                client_id, session_id, visitor_hash,
                referrer_host, ua_family, country, props_raw,
            ))
            if ev_type == "page_view":
                pv_inc += 1
            elif ev_type == "specimen_interact":
                int_inc += 1
            elif ev_type in ("copy_prompt", "copy_code", "export_bundle"):
                copy_inc += 1

        if not rows:
            return 0

        with self._lock:
            cur = self._conn.cursor()
            cur.executemany(
                """
                INSERT INTO events (
                  ts, day, event_type, source, pattern_id, category,
                  client_id, session_id, visitor_hash,
                  referrer_host, ua_family, country, props_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            if session_id:
                cur.execute(
                    """
                    INSERT INTO sessions (
                      session_id, client_id, visitor_hash, first_ts, last_ts, day,
                      referrer_host, ua_family, country, page_views, interacts, copies
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                      last_ts = MAX(sessions.last_ts, excluded.last_ts),
                      page_views = sessions.page_views + excluded.page_views,
                      interacts = sessions.interacts + excluded.interacts,
                      copies = sessions.copies + excluded.copies
                    """,
                    (
                        session_id, client_id, visitor_hash, min_ts, max_ts, day_from_ts(min_ts),
                        referrer_host, ua_family, country, pv_inc, int_inc, copy_inc,
                    ),
                )
            self._conn.commit()
        return len(rows)

    def record_ai_fetch(
        self,
        *,
        path: str,
        pattern_id: Optional[str],
        visitor_hash: str,
        referrer_host: str,
        ua_family: str,
        country: str,
        raw_ua: str,
        event_type: str = "ai_fetch",
        extra_props: Optional[Dict[str, Any]] = None,
    ) -> None:
        ts = int(time.time() * 1000)
        day = day_from_ts(ts)
        payload: Dict[str, Any] = {"path": path[:160], "ua_sample": raw_ua[:140]}
        if extra_props:
            payload.update(extra_props)
        props = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(props.encode("utf-8")) > 1024:
            props = json.dumps({"path": path[:160], "truncated": True})
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO events (
                  ts, day, event_type, source, pattern_id, category,
                  client_id, session_id, visitor_hash,
                  referrer_host, ua_family, country, props_json
                ) VALUES (?, ?, ?, 'server_ai', ?, ?, NULL, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    ts, day, event_type, pattern_id,
                    (extra_props or {}).get("category"),
                    visitor_hash, referrer_host, ua_family, country, props,
                ),
            )
            self._conn.commit()

    def health_summary(self) -> Dict[str, Any]:
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            sessions = self._conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "status": "ok",
            "events": total,
            "sessions": sessions,
            "db_bytes": size_bytes,
        }
