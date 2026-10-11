"""Verify what a run actually did, from its trace.

A run of the eval is only evidence if we can show it went through the real skill
and the real MCP server, in the condition it claims. Claude Code's
`--output-format stream-json` gives one JSON object per line, including every
tool call and every tool result, so these checks read that trace and either
confirm the run or reject it.

The check that matters most:

    A pack ON run whose get_jargon_pack came back with pack_mode "off" is a
    silently broken run. Its numbers would look like a real comparison while
    actually comparing a condition against itself.

The eval runner calls `verify_run` after every single run and refuses to keep a
run that fails, rather than discovering it later while reading results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

#: Claude Code namespaces MCP tools as mcp__<server>__<tool>.
MCP_PREFIX = "mcp__"

#: Tools a valid triage run must have used.
REQUIRED_TOOLS = ("get_taxonomy", "get_jargon_pack", "get_reviews", "save_triage")


class TraceError(AssertionError):
    """The trace does not show what the run claimed to do."""


@dataclass
class ToolCall:
    name: str
    tool_use_id: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    is_error: bool = False


def short_tool_name(name: str) -> str:
    """'mcp__review-triage__get_jargon_pack' -> 'get_jargon_pack'."""
    if name.startswith(MCP_PREFIX):
        return name.split("__")[-1]
    return name


def parse_trace(lines: Iterable[str]) -> list[dict[str, Any]]:
    """Parse stream-json lines, skipping anything unparseable."""
    events: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _blocks(event: dict[str, Any]) -> list[dict[str, Any]]:
    message = event.get("message")
    content = message.get("content") if isinstance(message, dict) else event.get("content")
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []


def _result_payload(block: dict[str, Any]) -> Any:
    """Pull a tool result out of a block, parsing JSON text when present."""
    if "structuredContent" in block:
        return block["structuredContent"]
    if "structured_content" in block:
        return block["structured_content"]

    content = block.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    else:
        return content

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def extract_tool_calls(events: Iterable[dict[str, Any]]) -> list[ToolCall]:
    """Pair tool_use blocks with their tool_result blocks."""
    calls: list[ToolCall] = []
    by_id: dict[str, ToolCall] = {}

    for event in events:
        for block in _blocks(event):
            kind = block.get("type")
            if kind == "tool_use":
                call = ToolCall(
                    name=short_tool_name(str(block.get("name", ""))),
                    tool_use_id=block.get("id"),
                    arguments=block.get("input") or {},
                )
                calls.append(call)
                if call.tool_use_id:
                    by_id[call.tool_use_id] = call
            elif kind == "tool_result":
                call = by_id.get(str(block.get("tool_use_id")))
                if call is not None:
                    call.result = _result_payload(block)
                    call.is_error = bool(block.get("is_error") or block.get("isError"))
    return calls


def pack_modes(calls: Iterable[ToolCall]) -> list[str]:
    """Every pack_mode reported by a get_jargon_pack result."""
    modes: list[str] = []
    for call in calls:
        if call.name != "get_jargon_pack":
            continue
        if isinstance(call.result, dict) and "pack_mode" in call.result:
            modes.append(str(call.result["pack_mode"]))
    return modes


def verify_run(
    lines: Iterable[str],
    expected_pack_mode: str,
    required_tools: Iterable[str] = REQUIRED_TOOLS,
) -> dict[str, Any]:
    """Check one run's trace. Raises TraceError on anything suspicious.

    Returns a small summary that is stored next to the run so the claim is
    auditable later without re-reading the whole trace.
    """
    expected_pack_mode = expected_pack_mode.strip().lower()
    if expected_pack_mode not in ("on", "off"):
        raise ValueError(f"expected_pack_mode must be 'on' or 'off', got {expected_pack_mode!r}")

    events = parse_trace(lines)
    if not events:
        raise TraceError("trace is empty: the run produced no parseable events")

    calls = extract_tool_calls(events)
    called = [call.name for call in calls]

    missing = [tool for tool in required_tools if tool not in called]
    if missing:
        raise TraceError(
            f"run did not go through the expected path; these tools were never called: "
            f"{missing}. Tools actually called: {sorted(set(called)) or 'none'}"
        )

    failed = sorted({call.name for call in calls if call.is_error})
    if failed:
        raise TraceError(f"these tool calls returned errors: {failed}")

    modes = pack_modes(calls)
    if not modes:
        raise TraceError(
            "get_jargon_pack was called but no result reported pack_mode, so the "
            "condition of this run cannot be verified"
        )
    wrong = sorted({mode for mode in modes if mode != expected_pack_mode})
    if wrong:
        raise TraceError(
            f"run was supposed to be pack {expected_pack_mode.upper()} but the server "
            f"reported pack_mode {wrong}. Check TRIAGE_PACK_MODE in the run environment; "
            "the run is discarded rather than scored."
        )

    pack_calls = [call for call in calls if call.name == "get_jargon_pack"]
    term_counts = [
        call.result.get("term_count")
        for call in pack_calls
        if isinstance(call.result, dict) and "term_count" in call.result
    ]
    if expected_pack_mode == "on" and term_counts and all(
        count == 0 for count in term_counts
    ):
        raise TraceError(
            "run claims pack ON but every get_jargon_pack returned zero terms, so it "
            "is indistinguishable from pack OFF. Is there a pack for this game?"
        )

    return {
        "pack_mode": expected_pack_mode,
        "events": len(events),
        "tool_calls": len(calls),
        "tools_used": sorted(set(called)),
        "get_jargon_pack_calls": len(pack_calls),
        "pack_term_counts": term_counts,
    }
