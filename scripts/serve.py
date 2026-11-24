#!/usr/bin/env python3
"""Local dev launcher — delegates to server/app.py (static + SQLite telemetry)."""
import pathlib
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
runpy.run_path(str(ROOT / "server" / "app.py"), run_name="__main__")
