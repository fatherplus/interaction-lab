#!/usr/bin/env python3
"""Smoke tests for the build output, every HTTP surface, and telemetry ingest.

Standard library only:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SKIP_DIRS = {".git", "dist", "mirror", ".impeccable", ".zcode", "__pycache__", "telemetry-data"}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get(url: str, timeout: float = 5.0):
    req = urllib.request.Request(url, headers={"User-Agent": "interaction-lab-tests/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def post_json(url: str, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "interaction-lab-tests/1.0"},
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        return resp.status, json.loads(resp.read() or b"{}")


class BuildOutputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        proc = subprocess.run(
            [sys.executable, "build.py"], cwd=ROOT, capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise AssertionError(f"build.py failed:\n{proc.stdout}\n{proc.stderr}")
        cls.catalog = json.loads((DIST / "api" / "patterns.json").read_text(encoding="utf-8"))

    def test_catalog_shape(self) -> None:
        self.assertEqual(len(self.catalog["categories"]), 6)
        self.assertEqual(len(self.catalog["patterns"]), 48)
        ids = [p["id"] for p in self.catalog["patterns"]]
        self.assertEqual(len(ids), len(set(ids)), "pattern ids must be unique")

    def test_every_pattern_has_required_fields(self) -> None:
        for p in self.catalog["patterns"]:
            for field in ("id", "category", "name_cn", "name_en", "essence", "tokens", "state_machine", "do_not"):
                self.assertIn(field, p, f"{p.get('id')} missing {field}")
            self.assertTrue(p["tokens"], f"{p['id']} has no tokens")
            self.assertTrue(p["state_machine"], f"{p['id']} has no state machine")

    def test_specimens_exist_and_are_standalone(self) -> None:
        files = sorted((DIST / "specimens").glob("*.html"))
        self.assertEqual(len(files), 48)
        for f in files:
            html = f.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE", html.upper(), f"{f.name} is not a full document")
            # No external requests: reject remote script/link/img/font loads.
            for attr in ('src="http', "src='http", 'href="http', "href='http"):
                self.assertNotIn(attr, html, f"{f.name} loads a remote asset")

    def test_markdown_specs_and_indexes(self) -> None:
        for name in ("llms.txt", "robots.txt", "SKILL.md", "index.html"):
            self.assertTrue((DIST / name).is_file(), f"missing dist/{name}")
        self.assertEqual(len(list((DIST / "patterns").glob("*.md"))), 48)
        self.assertTrue((DIST / "cli" / "ilab").is_file())

    def test_index_is_cache_busted(self) -> None:
        html = (DIST / "index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r'href="css/[^"]+\.css\?v=')
        self.assertRegex(html, r'src="js/[^"]+\.js\?v=')

    def test_no_secrets_or_internal_hosts(self) -> None:
        for path in DIST.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            self.assertNotRegex(text, r"\b192\.168\.\d{1,3}\.\d{1,3}\b", f"LAN address in {path}")
            self.assertNotIn("-----BEGIN", text, f"key material in {path}")


class NoThirdPartyImportsTest(unittest.TestCase):
    """The zero-dependency promise: only stdlib and this repo's own modules."""

    LOCAL = {"server", "scripts", "extract_specimens", "db", "app"}

    def test_python_sources_use_stdlib_only(self) -> None:
        if not hasattr(sys, "stdlib_module_names"):
            self.skipTest("sys.stdlib_module_names requires Python 3.10+")
        sources = [
            p for p in ROOT.rglob("*.py")
            if not (set(p.relative_to(ROOT).parts) & SKIP_DIRS)
        ]
        cli = ROOT / "cli" / "ilab"
        if cli.is_file():
            sources.append(cli)

        offenders = []
        for path in sources:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules = [node.module]
                for mod in modules:
                    top = mod.split(".")[0]
                    if top in sys.stdlib_module_names or top in self.LOCAL or top == "__future__":
                        continue
                    offenders.append(f"{path.relative_to(ROOT)}: {mod}")

        self.assertEqual(offenders, [], f"third-party imports found: {offenders}")


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = pathlib.Path(cls.tmp.name) / "telemetry.sqlite"
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = os.environ.copy()
        env.update(
            IL_HOST="127.0.0.1",
            IL_PORT=str(cls.port),
            IL_DB_PATH=str(cls.db_path),
            IL_TELEMETRY_SALT="test-salt",
            IL_QUIET="1",
        )
        cls.proc = subprocess.Popen(
            [sys.executable, "server/app.py", str(cls.port)],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                if get(cls.base + "/api/health", timeout=1)[0] == 200:
                    return
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.2)
        cls.proc.terminate()
        raise AssertionError("server did not become healthy within 15s")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
        cls.tmp.cleanup()

    def test_index_served(self) -> None:
        status, body = get(self.base + "/")
        self.assertEqual(status, 200)
        self.assertIn(b"INTERACTION LAB", body.upper())

    def test_security_headers(self) -> None:
        req = urllib.request.Request(self.base + "/", headers={"User-Agent": "test"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(resp.headers["X-Frame-Options"], "SAMEORIGIN")
            self.assertIn("Referrer-Policy", resp.headers)

    def test_categories(self) -> None:
        status, body = get(self.base + "/api/categories")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["total_patterns"], 48)
        self.assertEqual(len(data["categories"]), 6)
        self.assertEqual(sum(c["count"] for c in data["categories"]), 48)

    def test_search_hit_and_miss(self) -> None:
        _, body = get(self.base + "/api/search?q=%E6%8C%89%E9%92%AE%E6%B2%A1%E5%8F%8D%E9%A6%88")  # 按钮没反馈
        data = json.loads(body)
        self.assertGreaterEqual(data["count"], 1)

        _, body = get(self.base + "/api/search?q=zzzz-no-such-pattern")
        self.assertEqual(json.loads(body)["count"], 0)

    def test_specimen_and_markdown(self) -> None:
        status, body = get(self.base + "/specimens/coverflow-depth-stage.html")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE", body.upper())

        status, body = get(self.base + "/patterns/coverflow-depth-stage.md")
        self.assertEqual(status, 200)
        self.assertIn("Token Contract".encode(), body)

    def test_cli_origin_injection(self) -> None:
        status, body = get(self.base + "/cli/ilab")
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        self.assertIn(self.base, text)
        self.assertNotIn("@@DEFAULT_URL@@", text)

    def test_health(self) -> None:
        status, body = get(self.base + "/api/health")
        self.assertEqual(json.loads(body)["status"], "ok")

    def test_telemetry_ingest(self) -> None:
        status, data = post_json(self.base + "/api/t", {
            "client_id": "c-test",
            "session_id": "s-test",
            "events": [
                {"event_type": "page_view", "ts": int(time.time() * 1000)},
                {"event_type": "specimen_interact", "pattern_id": "coverflow-depth-stage",
                 "category": "spatial-hierarchy", "ts": int(time.time() * 1000)},
            ],
        })
        self.assertEqual(status, 202)
        self.assertEqual(data["accepted"], 2)

        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT event_type FROM events WHERE session_id = 's-test' ORDER BY event_type"
            ).fetchall()
        self.assertEqual([r[0] for r in rows], ["page_view", "specimen_interact"])

        # Unknown event types are dropped, not stored.
        _, data = post_json(self.base + "/api/t", {"events": [{"event_type": "evil_type"}]})
        self.assertEqual(data["accepted"], 0)

    def test_telemetry_rejects_bad_payload(self) -> None:
        try:
            post_json(self.base + "/api/t", {"events": []})
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 400)
        else:
            self.fail("empty event list should be rejected")


if __name__ == "__main__":
    unittest.main(verbosity=2)
