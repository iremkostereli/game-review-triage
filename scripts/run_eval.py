"""Run the triage eval through the real skill and the real MCP server.

    uv run scripts/run_eval.py --games "Clash of Clans" --conditions on --limit 5 --repeats 1
    uv run scripts/run_eval.py --limit 20 --repeats 1          # cheap smoke run
    uv run scripts/run_eval.py                                 # full: 2 conditions x 3 repeats

Each run is a headless `claude -p` invocation that loads the review-triage skill
and talks to the review-triage MCP server over stdio. Nothing here reimplements
the triage: the measured path is the same one a person gets interactively.

Four things make this trustworthy and restartable:

1. **The prompt is built once** per batch and reused byte-for-byte across
   conditions, so pack OFF and pack ON cannot differ by wording. Asserted below.

2. **The condition travels in a generated MCP config**, not an exported variable.
   An `env` block in an MCP config overrides the shell, so exporting
   TRIAGE_PACK_MODE silently does nothing.

3. **The trace decides whether a run counts, not the exit code.** A run can do
   all of its work and still exit non-zero, which is exactly what happened when a
   session usage limit landed after the final tool call: 20 reviews were triaged
   and saved, yet the process returned 1. So every run is judged on what its
   trace and saved output show.

4. **Work is batched and resumable.** Reviews are split into batches, and a batch
   already recorded as complete is skipped. If a usage limit interrupts a full
   run, the same command picks up where it stopped instead of repeating paid work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import packs, paths
from triage.jsonl_io import read_json, write_json
from triage.trace_checks import TraceError, verify_run

MCP_TOOLS = [
    "mcp__review-triage__list_games",
    "mcp__review-triage__get_taxonomy",
    "mcp__review-triage__get_jargon_pack",
    "mcp__review-triage__get_reviews",
    "mcp__review-triage__save_triage",
]
ALLOWED_TOOLS = ",".join(["Skill", "ToolSearch", *MCP_TOOLS])

CONDITIONS = ("off", "on")

#: Reviews available per game in the golden split, after withheld ones are
#: filtered out. Used to plan batches without loading the corpus.
GOLDEN_COUNTS = {"Clash of Clans": 99, "Candy Crush Saga": 79}


class UsageLimitReached(RuntimeError):
    """The account's session limit was hit; stop rather than burn more runs."""


def build_prompt(game: str, run_id: str, offset: int, limit: int) -> str:
    """The task given to the model. Identical across conditions by construction."""
    return (
        "Use the review-triage skill to triage game reviews.\n\n"
        f"Game: {game}\n"
        f"Run id: {run_id}\n"
        f"Triage reviews {offset + 1} to {offset + limit} of the golden split for "
        f"this game: call get_reviews with offset={offset} and limit={limit}.\n\n"
        "Follow the skill's procedure exactly: fetch the taxonomy, fetch the jargon "
        "pack for this game, fetch that page of reviews, triage every one of them, "
        "group them into issues with evidence, and save the results with save_triage "
        "using the run id above.\n\n"
        "Reply with one line when you are done: the number of reviews you triaged."
    )


def write_mcp_config(directory: Path, pack_mode: str, runs_dir: Path) -> Path:
    """One config per condition. This is what actually selects pack OFF or ON."""
    config = {
        "mcpServers": {
            "review-triage": {
                "command": "uv",
                "args": ["run", "mcp_server/server.py"],
                "env": {"TRIAGE_PACK_MODE": pack_mode, "TRIAGE_RUNS_DIR": str(runs_dir)},
            }
        }
    }
    path = directory / f"mcp_{pack_mode}.json"
    write_json(path, config)
    return path


def pack_fingerprint(game: str, pack_mode: str) -> dict[str, Any]:
    """Which pack a run saw, so a result can be traced back to it."""
    if pack_mode == "off":
        return {"present": False, "reason": "pack mode off"}
    try:
        pack = packs.load_pack(game)
    except packs.PackError as error:
        return {"present": False, "reason": str(error)}
    return {
        "present": True,
        "file": pack.path.name,
        "terms": len(pack.terms),
        "sha256": hashlib.sha256(pack.path.read_bytes()).hexdigest()[:16],
    }


def plan_batches(game: str, limit: int, batch_size: int) -> list[tuple[int, int]]:
    """(offset, size) windows covering `limit` reviews of one game."""
    total = min(limit, GOLDEN_COUNTS.get(game, limit))
    batches: list[tuple[int, int]] = []
    offset = 0
    while offset < total:
        size = min(batch_size, total - offset)
        batches.append((offset, size))
        offset += size
    return batches


def already_done(out_dir: Path, expected: int) -> dict[str, Any] | None:
    """A previous meta.json recording a complete, verified run of this batch."""
    meta_path = out_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        meta = read_json(meta_path)
    except (json.JSONDecodeError, OSError):
        return None
    if meta.get("status") == "ok" and meta.get("result_count") == expected:
        return meta
    return None


def read_result_event(trace: str) -> dict[str, Any]:
    """The final `result` event, which carries the API error fields."""
    for line in reversed(trace.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            return event
    return {}


def run_once(
    game: str,
    pack_mode: str,
    repeat: int,
    batch: int,
    offset: int,
    size: int,
    model: str,
    runs_dir: Path,
    config_path: Path,
    prompt: str,
    timeout: int,
    force: bool,
) -> dict[str, Any]:
    """Execute one batch and judge it on its trace, not on its exit code."""
    run_id = f"{paths.game_slug(game)}-{pack_mode}-r{repeat}-b{batch}"
    out_dir = runs_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if not force:
        previous = already_done(out_dir, size)
        if previous is not None:
            print(f"  {run_id} ... skipped (already complete, {size} reviews)")
            previous["skipped"] = True
            return previous

    command = [
        "claude", "-p", prompt,
        "--model", model,
        "--mcp-config", str(config_path),
        "--strict-mcp-config",
        "--allowedTools", ALLOWED_TOOLS,
        "--output-format", "stream-json",
        "--verbose",
    ]

    started = time.time()
    print(f"  {run_id} ... ", end="", flush=True)
    completed = subprocess.run(
        command,
        cwd=paths.REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    elapsed = round(time.time() - started, 1)
    (out_dir / "trace.jsonl").write_text(completed.stdout, encoding="utf-8", newline="\n")

    final = read_result_event(completed.stdout)
    meta: dict[str, Any] = {
        "run_id": run_id,
        "game": game,
        "pack_mode": pack_mode,
        "repeat": repeat,
        "batch": batch,
        "offset": offset,
        "limit": size,
        "model": model,
        "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(timespec="seconds"),
        "elapsed_seconds": elapsed,
        "exit_code": completed.returncode,
        "cost_usd": round(float(final.get("total_cost_usd") or 0), 4),
        "api_error": final.get("api_error"),
        "permission_denials": final.get("permission_denials"),
        "pack": pack_fingerprint(game, pack_mode),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16],
    }

    output_path = out_dir / "output.json"
    if output_path.exists():
        try:
            saved = read_json(output_path)
            meta["result_count"] = saved.get("result_count")
            meta["issue_groups"] = len(saved.get("issue_groups") or [])
        except (json.JSONDecodeError, OSError):
            meta["result_count"] = None

    try:
        meta["trace"] = verify_run(completed.stdout.splitlines(), pack_mode)
        if meta.get("result_count") == size:
            meta["status"] = "ok"
            print(
                f"ok ({elapsed}s, {meta['trace']['tool_calls']} tool calls, "
                f"{meta['result_count']} reviews, ${meta['cost_usd']})"
            )
        else:
            meta["status"] = "incomplete"
            meta["error"] = f"expected {size} triaged reviews, saved {meta.get('result_count')}"
            print(f"INCOMPLETE ({elapsed}s) - {meta['error']}")
    except TraceError as error:
        meta["status"] = "rejected"
        meta["error"] = str(error)
        print(f"REJECTED ({elapsed}s) - {error}")

    if final.get("api_error") == "usage_limit_reached":
        meta["usage_limit"] = True
        meta["usage_limit_message"] = str(final.get("result"))[:200]

    write_json(out_dir / "meta.json", meta)

    if meta.get("usage_limit") and meta["status"] != "ok":
        raise UsageLimitReached(meta.get("usage_limit_message") or "usage limit reached")
    return meta


def build_jobs(args) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for game in args.games:
        for repeat in range(1, args.repeats + 1):
            for batch, (offset, size) in enumerate(
                plan_batches(game, args.limit, args.batch_size), start=1
            ):
                prompts = {
                    mode: build_prompt(
                        game,
                        f"{paths.game_slug(game)}-{mode}-r{repeat}-b{batch}",
                        offset,
                        size,
                    )
                    for mode in args.conditions
                }
                # The run id is the only place the condition may appear. Blank it
                # out and the prompts must be identical, or the comparison is
                # confounded by wording rather than by the pack.
                stripped = {
                    mode: prompt.replace(f"-{mode}-", "-CONDITION-")
                    for mode, prompt in prompts.items()
                }
                assert len(set(stripped.values())) == 1, (
                    "prompts differ between conditions beyond the run id"
                )
                for mode in args.conditions:
                    jobs.append(
                        {
                            "game": game,
                            "pack_mode": mode,
                            "repeat": repeat,
                            "batch": batch,
                            "offset": offset,
                            "size": size,
                            "prompt": prompts[mode],
                        }
                    )
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", nargs="*", default=list(paths.EVAL_GAMES))
    parser.add_argument(
        "--conditions", nargs="*", default=list(CONDITIONS), choices=list(CONDITIONS)
    )
    parser.add_argument("--repeats", type=int, default=3,
                        help="runs per game per condition, for variance")
    parser.add_argument("--limit", type=int, default=100,
                        help="reviews per game per repeat; capped at the golden count")
    parser.add_argument("--batch-size", type=int, default=20,
                        help="reviews per claude invocation; smaller batches resume better")
    parser.add_argument("--model", default="sonnet", help="never opus, for usage budget")
    parser.add_argument("--runs-dir", type=Path, default=paths.RUNS_DIR)
    parser.add_argument("--timeout", type=int, default=1800, help="seconds per batch")
    parser.add_argument("--force", action="store_true",
                        help="re-run batches already recorded as complete")
    args = parser.parse_args()

    if shutil.which("claude") is None:
        raise SystemExit("the `claude` CLI is not on PATH")

    args.runs_dir.mkdir(parents=True, exist_ok=True)
    config_dir = args.runs_dir / "_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    configs = {m: write_mcp_config(config_dir, m, args.runs_dir) for m in args.conditions}

    jobs = build_jobs(args)
    print(
        f"{len(jobs)} batches: {len(args.games)} game(s) x {len(args.conditions)} "
        f"condition(s) x {args.repeats} repeat(s), {args.batch_size} reviews per batch, "
        f"model {args.model}\n"
    )

    results: list[dict[str, Any]] = []
    stopped_early = None
    for job in jobs:
        try:
            results.append(
                run_once(
                    game=job["game"],
                    pack_mode=job["pack_mode"],
                    repeat=job["repeat"],
                    batch=job["batch"],
                    offset=job["offset"],
                    size=job["size"],
                    model=args.model,
                    runs_dir=args.runs_dir,
                    config_path=configs[job["pack_mode"]],
                    prompt=job["prompt"],
                    timeout=args.timeout,
                    force=args.force,
                )
            )
        except UsageLimitReached as error:
            stopped_early = str(error)
            print(f"\nStopping: {error}")
            print("Re-run the same command later; completed batches are skipped.")
            break

    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "planned_batches": len(jobs),
        "attempted": len(results),
        "status_counts": counts,
        "total_cost_usd": round(sum(r.get("cost_usd", 0) or 0 for r in results), 4),
        "stopped_early": stopped_early,
        "golden_set_sha256": (
            read_json(paths.SPLIT_MANIFEST).get("golden_set_sha256")
            if paths.SPLIT_MANIFEST.exists()
            else None
        ),
        "runs": results,
    }
    write_json(args.runs_dir / "summary.json", summary)

    done = counts.get("ok", 0)
    others = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()) if k != "ok")
    print(f"\n{done}/{len(jobs)} batches ok{', ' + others if others else ''} "
          f"| ${summary['total_cost_usd']}")
    print(f"Wrote {args.runs_dir / 'summary.json'}")
    return 0 if done == len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
