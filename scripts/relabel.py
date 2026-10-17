"""Blind re-labeling tool: label a mixed sample again, then settle the differences.

    uv run scripts/relabel.py

Two passes, in one page.

Pass 1 - **blind**. You label a shuffled mix of reviews from scratch. You are
shown neither your original label nor the system's, and nothing tells you which
group a review came from. A reference panel with the category definitions, the
four hard cases and the keyword traps stays open beside the review.

Pass 2 - **decide**. Only the reviews where your new label differs from your
original one come back. Both labels are shown side by side, the system's
reasoning is one keypress away, and you pick which label the guide supports. A
change needs a reason from a fixed list, so reasons can be counted afterwards.

Decisions are written to data/golden/corrections.jsonl as you go, and the whole
thing is resumable. No model is called anywhere in this tool.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import corrections as corrections_module
from triage import paths, relabel, scoring
from triage.jsonl_io import read_jsonl, write_jsonl
from triage.taxonomy import LabelError, load_taxonomy, validate_labels

UI_DIR = Path(__file__).resolve().parent / "relabel_ui"


def guide_payload() -> dict[str, Any]:
    """The reference panel's contents, taken from the taxonomy itself."""
    taxonomy = load_taxonomy()
    categories = []
    for category in taxonomy.categories:
        guidance = category.severity_guidance or {}
        movers = []
        for key, value in guidance.items():
            if key.startswith(("escalate", "de_escalate")) and isinstance(value, dict):
                label = "Higher when" if key.startswith("escalate") else "Lower when"
                movers.append({"label": label, "reason": value.get("reason", "")})
        categories.append(
            {
                "id": category.id,
                "name": category.name,
                "definition": category.definition,
                "typical": guidance.get("typical", ""),
                "movers": movers,
                "exclusive": category.exclusive,
            }
        )

    boundaries = taxonomy.boundaries or {}
    cases = [
        {
            "question": case.get("question", ""),
            "rule": case.get("rule", ""),
            "examples": [
                {
                    "quote": case[key].get("quote", ""),
                    "labels": case[key].get("labels", []),
                }
                for key in ("both_labels", "single_label", "three_labels")
                if isinstance(case.get(key), dict)
            ],
        }
        for case in boundaries.get("cases", [])
    ]
    traps = [
        {"quote": trap.get("quote", ""), "labels": trap.get("labels", []),
         "why": trap.get("why", "")}
        for trap in boundaries.get("keyword_traps", [])
    ]

    return {
        "categories": categories,
        "severity_levels": list(taxonomy.severity_levels),
        "severity_definitions": {
            level["id"]: level["definition"] for level in taxonomy.severity["levels"]
        },
        "general_rule": boundaries.get("general_rule", ""),
        "cases": cases,
        "keyword_traps": traps,
        "jargon_help": taxonomy.flags["has_jargon"]["definition"],
        "rules": taxonomy.labeling_rules,
    }


class Handler(BaseHTTPRequestHandler):
    tasks: list[relabel.Task] = []
    gold_rows: dict[str, dict[str, Any]] = {}
    gold: dict[str, scoring.GoldReview] = {}
    unanimous: dict[str, dict[str, Any]] = {}
    store: relabel.RelabelStore
    corrections_path: Path

    def log_message(self, fmt, *args):  # noqa: A003
        pass

    # -- helpers ---------------------------------------------------------
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        self._send(
            status,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    # -- state -----------------------------------------------------------
    def _decisions(self) -> dict[str, dict[str, Any]]:
        if not self.corrections_path.exists():
            return {}
        return {row["reviewId"]: row for row in read_jsonl(self.corrections_path)}

    def _differences(self) -> list[dict[str, Any]]:
        """Reviews whose blind label differs from the original. Pass 2's work list."""
        blind = self.store.load()
        rows = []
        for task in self.tasks:
            record = blind.get(task.review_id)
            if record is None:
                continue
            original = self.gold_rows[task.review_id]
            old_categories = sorted(original.get("categories") or [])
            new_categories = sorted(record.get("categories") or [])
            old_severity = original.get("severity") or None
            new_severity = record.get("severity") or None
            if old_categories == new_categories and old_severity == new_severity:
                continue
            agreed = self.unanimous.get(task.review_id, {})
            rows.append(
                {
                    "reviewId": task.review_id,
                    "game": original.get("game"),
                    "score": original.get("score"),
                    "content": original.get("content"),
                    "old_categories": old_categories,
                    "old_severity": old_severity,
                    "old_has_jargon": bool(original.get("has_jargon")),
                    "new_categories": new_categories,
                    "new_severity": new_severity,
                    "new_has_jargon": bool(record.get("has_jargon")),
                    "model_categories": sorted(agreed.get("categories") or []),
                    "model_severity": agreed.get("severity"),
                    "model_rationales": agreed.get("rationales") or [],
                }
            )
        return rows

    # -- routes ----------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            html = (UI_DIR / "index.html").read_text(encoding="utf-8")
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/bootstrap":
            blind = self.store.load()
            self._json(
                {
                    # Provenance is deliberately absent: knowing a review was
                    # queued would reveal that the system disagreed with the
                    # original label.
                    "tasks": [
                        {
                            "reviewId": task.review_id,
                            "game": self.gold_rows[task.review_id].get("game"),
                            "score": self.gold_rows[task.review_id].get("score"),
                            "content": self.gold_rows[task.review_id].get("content"),
                        }
                        for task in self.tasks
                    ],
                    "blind_labels": blind,
                    "guide": guide_payload(),
                    "change_reasons": relabel.CHANGE_REASONS,
                    "decisions": self._decisions(),
                }
            )
        elif self.path == "/api/differences":
            blind = self.store.load()
            remaining = [t.review_id for t in self.tasks if t.review_id not in blind]
            self._json(
                {
                    "blind_done": len(blind),
                    "blind_total": len(self.tasks),
                    "remaining": remaining,
                    "differences": self._differences() if not remaining else [],
                    "decisions": self._decisions(),
                }
            )
        else:
            self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
        except json.JSONDecodeError as error:
            self._json({"error": f"bad JSON: {error}"}, status=400)
            return

        if self.path == "/api/blind_label":
            categories = payload.get("categories") or []
            severity = payload.get("severity") or None
            unclear = bool(payload.get("unclear"))
            if not (unclear and not categories):
                try:
                    validate_labels(categories, severity)
                except LabelError as error:
                    self._json({"error": str(error)}, status=400)
                    return
            record = {
                "reviewId": str(payload.get("reviewId")),
                "categories": sorted(str(c) for c in categories),
                "severity": severity,
                "has_jargon": bool(payload.get("has_jargon")),
                "unclear": unclear,
            }
            self.store.save(record)
            blind = self.store.load()
            self._json({"saved": record, "done": len(blind), "total": len(self.tasks)})

        elif self.path == "/api/decision":
            try:
                self._write_decision(payload)
            except (LabelError, ValueError) as error:
                self._json({"error": str(error)}, status=400)
                return
            self._json({"saved": True, "decisions": len(self._decisions())})

        else:
            self._json({"error": "not found"}, status=404)

    def _write_decision(self, payload: dict[str, Any]) -> None:
        """Record one pass-2 decision into corrections.jsonl."""
        review_id = str(payload.get("reviewId") or "")
        if review_id not in self.gold_rows:
            raise ValueError(f"unknown review {review_id}")
        choice = str(payload.get("choice") or "")
        if choice not in ("keep", "change"):
            raise ValueError("choice must be 'keep' or 'change'")

        original = self.gold_rows[review_id]
        old_categories = sorted(original.get("categories") or [])
        old_severity = original.get("severity") or None

        if choice == "keep":
            new_categories, new_severity, reason = old_categories, old_severity, ""
        else:
            new_categories = sorted(str(c) for c in payload.get("new_categories") or [])
            new_severity = payload.get("new_severity") or None
            validate_labels(new_categories, new_severity)
            reason_code = str(payload.get("reason_code") or "")
            if reason_code not in relabel.CHANGE_REASONS:
                raise ValueError(f"reason must be one of {sorted(relabel.CHANGE_REASONS)}")
            note = str(payload.get("note") or "").strip()
            reason = relabel.CHANGE_REASONS[reason_code]
            if note:
                reason = f"{reason}: {note}"
            if reason_code == "other" and not note:
                raise ValueError("'Other' needs a note")

        row = {
            "reviewId": review_id,
            "action": "change" if choice == "change" else "keep",
            "old_categories": old_categories,
            "old_severity": old_severity,
            "new_categories": new_categories,
            "new_severity": new_severity,
            "reason": reason,
            "reason_code": payload.get("reason_code") if choice == "change" else None,
            "decided_in": "blind_relabel",
        }

        existing = self._decisions()
        existing[review_id] = row
        ordered = [existing[t.review_id] for t in self.tasks if t.review_id in existing]
        write_jsonl(self.corrections_path, ordered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--controls", type=int, default=relabel.DEFAULT_CONTROL_COUNT)
    parser.add_argument("--corrections", type=Path, default=paths.GOLDEN_CORRECTIONS)
    args = parser.parse_args()

    gold = scoring.load_gold()
    if not gold:
        raise SystemExit("no answer key; label the golden set first")
    gold_rows = {row["reviewId"]: row for row in read_jsonl(paths.GOLDEN_SET)}

    unanimous = relabel.unanimous_predictions()
    if not unanimous:
        raise SystemExit("no completed runs; run scripts/run_eval.py first")

    manifest = relabel.load_manifest()
    if manifest:
        tasks = [
            relabel.Task(t["reviewId"], t["source"], t["order"]) for t in manifest["tasks"]
        ]
        print(f"Reusing the existing task list ({manifest['counts']['total']} reviews, "
              f"fingerprint {manifest['fingerprint']})")
    else:
        tasks = relabel.build_task_list(gold, unanimous, control_count=args.controls)
        manifest = relabel.write_manifest(tasks)
        print(f"Built a task list of {manifest['counts']['total']} reviews "
              f"(fingerprint {manifest['fingerprint']})")

    store = relabel.RelabelStore()
    done = len(store.load())

    Handler.tasks = tasks
    Handler.gold_rows = gold_rows
    Handler.gold = gold
    Handler.unanimous = unanimous
    Handler.store = store
    Handler.corrections_path = args.corrections

    url = f"http://127.0.0.1:{args.port}/"
    print(f"Blind labeling: {done}/{len(tasks)} done")
    print("Which group each review came from is recorded in")
    print(f"  {relabel.RELABEL_MANIFEST.relative_to(paths.REPO_ROOT)}")
    print("and is never sent to the page.")
    print(f"\nOpen {url}")
    print("Press Ctrl+C here when you are finished.\n")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        blind = store.load()
        decisions = (
            read_jsonl(args.corrections) if args.corrections.exists() else []
        )
        changes = [d for d in decisions if d.get("action") == "change"]
        print(f"\nStopped. Blind labels: {len(blind)}/{len(tasks)}. "
              f"Decisions recorded: {len(decisions)}, of which {len(changes)} change a label.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
