"""Local hand-labeling tool for the golden set.

    python scripts/labeler.py

Serves a small keyboard-driven page on localhost and saves every label as soon
as you press next. Stop any time; re-running resumes where you left off.

Why a local server rather than a plain HTML file: a static page cannot write to
disk, and the whole point is that your work is durably saved after every single
review. The server is stdlib-only, binds to 127.0.0.1, and does nothing except
read the review pool and append labels.

No model is involved anywhere in this tool. Nothing is pre-filled or suggested;
the golden set has to be entirely your own judgement for the eval to mean
anything.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import paths
from triage.jsonl_io import read_jsonl
from triage.labels import LabelStore, export_golden_set
from triage.taxonomy import LabelError, load_taxonomy

UI_DIR = Path(__file__).resolve().parent / "label_ui"
POOL_PATH = paths.GOLDEN_DIR / "golden_pool.jsonl"


def build_bootstrap(pool: list[dict], store: LabelStore) -> dict:
    """Everything the page needs on load: the pool, the label space, prior work."""
    taxonomy = load_taxonomy()

    categories = []
    for category in taxonomy.categories:
        guidance = category.severity_guidance or {}
        categories.append(
            {
                "id": category.id,
                "name": category.name,
                "definition": category.definition,
                "typical_severity": guidance.get("typical", ""),
                "exclusive": category.exclusive,
                # The annotator needs the escalation rules at a glance, not the
                # whole YAML, so only the reasons are sent.
                "escalate": _reason(guidance, "escalate"),
                "de_escalate": _reason(guidance, "de_escalate"),
            }
        )

    return {
        "pool": pool,
        "categories": categories,
        "severity_levels": list(taxonomy.severity_levels),
        "severity_definitions": {
            level["id"]: level["definition"] for level in taxonomy.severity["levels"]
        },
        "jargon_help": taxonomy.flags["has_jargon"]["definition"],
        "unclear_help": taxonomy.flags["unclear"]["definition"],
        "labels": store.load(),
        "no_issue_id": "no_issue",
        "other_issue_id": "other_issue",
    }


def _reason(guidance: dict, prefix: str) -> str:
    for key, value in guidance.items():
        if key.startswith(prefix) and isinstance(value, dict):
            return value.get("reason", "")
    return ""


class Handler(BaseHTTPRequestHandler):
    """Tiny JSON API plus one static page."""

    pool: list[dict] = []
    store: LabelStore

    def log_message(self, fmt, *args):  # noqa: A003 - quiet the default access log
        pass

    # -- helpers ---------------------------------------------------------
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    # -- routes ----------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path in ("/", "/index.html"):
            html = (UI_DIR / "index.html").read_text(encoding="utf-8")
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/bootstrap":
            self._send_json(build_bootstrap(self.pool, self.store))
        elif self.path == "/api/progress":
            self._send_json(self.store.counts(r["reviewId"] for r in self.pool))
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
        except json.JSONDecodeError as error:
            self._send_json({"error": f"bad JSON: {error}"}, status=400)
            return

        if self.path == "/api/label":
            try:
                stored = self.store.save(payload)
            except (LabelError, KeyError) as error:
                self._send_json({"error": str(error)}, status=400)
                return
            self._send_json(
                {
                    "saved": stored,
                    "progress": self.store.counts(r["reviewId"] for r in self.pool),
                }
            )
        elif self.path == "/api/export":
            try:
                result = export_golden_set(self.pool, self.store)
            except LabelError as error:
                self._send_json({"error": str(error)}, status=400)
                return
            self._send_json(result)
        else:
            self._send_json({"error": "not found"}, status=404)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    parser.add_argument("--pool", type=Path, default=POOL_PATH)
    args = parser.parse_args()

    if not args.pool.exists():
        raise SystemExit(
            f"Review pool not found at {args.pool}\nRun: python scripts/prepare_data.py"
        )

    pool = read_jsonl(args.pool)
    store = LabelStore()

    Handler.pool = pool
    Handler.store = store

    progress = store.counts(r["reviewId"] for r in pool)
    url = f"http://127.0.0.1:{args.port}/"

    print(f"Reviews to label: {progress['total']}")
    print(f"Already labeled:  {progress['labeled']} (remaining {progress['remaining']})")
    print(f"Labels are appended to: {store.path}")
    print(f"\nOpen {url}")
    print("Press Ctrl+C here when you are done.\n")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Your labels are saved.")
        final = store.counts(r["reviewId"] for r in pool)
        print(f"Labeled {final['labeled']}/{final['total']}, {final['noted']} with notes.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
