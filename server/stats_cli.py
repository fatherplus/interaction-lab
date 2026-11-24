#!/usr/bin/env python3
"""Quick CLI inspector for Interaction Lab SQLite telemetry (pre-dashboard)."""
from __future__ import annotations

import os
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "telemetry.sqlite"


def main() -> None:
    db_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("IL_DB_PATH", str(DEFAULT_DB)))
    if not db_path.exists():
        sys.exit(f"No telemetry database yet at {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    print("=" * 68)
    print(f"Interaction Lab Telemetry Summary  ({db_path})")
    print("=" * 68)

    ov = conn.execute("""
        SELECT
          COUNT(*) AS total_events,
          COUNT(DISTINCT visitor_hash) AS unique_visitors,
          COUNT(DISTINCT session_id) AS sessions,
          SUM(CASE WHEN source = 'server_ai' THEN 1 ELSE 0 END) AS ai_fetches,
          SUM(CASE WHEN event_type = 'specimen_interact' THEN 1 ELSE 0 END) AS interacts,
          SUM(CASE WHEN event_type = 'copy_prompt' THEN 1 ELSE 0 END) AS copy_prompts,
          SUM(CASE WHEN event_type = 'copy_code' THEN 1 ELSE 0 END) AS copy_codes,
          SUM(CASE WHEN event_type = 'export_bundle' THEN 1 ELSE 0 END) AS bundles
        FROM events
    """).fetchone()
    print(
        f"Events: {ov['total_events']} | Unique Visitors: {ov['unique_visitors']} | "
        f"Sessions: {ov['sessions']} | AI Fetches: {ov['ai_fetches']}\n"
        f"Interacts: {ov['interacts']} | Copy Prompt: {ov['copy_prompts']} | "
        f"Copy Code: {ov['copy_codes']} | Bundles: {ov['bundles']}"
    )

    print("\n--- Top Patterns (Leaderboard) ---")
    rows = conn.execute("""
        SELECT * FROM v_pattern_leaderboard
        ORDER BY (copy_prompts * 5 + copy_codes * 4 + ai_fetches * 3 + opens * 2 + interacts) DESC
        LIMIT 12
    """).fetchall()
    if not rows:
        print("  (no pattern events yet)")
    else:
        print(f"  {'PATTERN':<28} {'UV':>4} {'PLAY':>5} {'OPEN':>5} {'PROMPT':>6} {'CODE':>5} {'AI_GET':>6}")
        for r in rows:
            print(
                f"  {r['pattern_id']:<28} {r['unique_users']:>4} {r['interacts']:>5} "
                f"{r['opens']:>5} {r['copy_prompts']:>6} {r['copy_codes']:>5} {r['ai_fetches']:>6}"
            )

    print("\n--- Client / AI Agent Families ---")
    uas = conn.execute("""
        SELECT COALESCE(ua_family, 'unknown') AS ua, COUNT(*) AS hits, COUNT(DISTINCT visitor_hash) AS uv
        FROM events GROUP BY ua ORDER BY hits DESC LIMIT 10
    """).fetchall()
    for r in uas:
        print(f"  {r['ua']:<20} hits={r['hits']:<6} uv={r['uv']}")

    print("\n--- Search Queries & Gaps ---")
    qs = conn.execute("SELECT * FROM v_search_gaps LIMIT 10").fetchall()
    if not qs:
        print("  (no searches yet)")
    else:
        for r in qs:
            flag = " [GAP]" if (r["min_results"] or 0) == 0 else ""
            print(f"  {r['query']!r:<24} count={r['searches']} min_results={r['min_results']}{flag}")

    conn.close()


if __name__ == "__main__":
    main()
