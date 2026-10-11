"""Tests for run-trace verification.

The point of these checks is to make a silently-broken run impossible to keep: a
run labelled pack ON whose server was actually in pack OFF would produce numbers
that look like a comparison but compare a condition against itself.
"""

from __future__ import annotations

import json

import pytest

from triage.trace_checks import (
    TraceError,
    extract_tool_calls,
    pack_modes,
    parse_trace,
    short_tool_name,
    verify_run,
)


def tool_use(name, call_id, arguments=None):
    return json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": call_id,
                        "name": f"mcp__review-triage__{name}",
                        "input": arguments or {},
                    }
                ]
            },
        }
    )


def tool_result(call_id, payload, is_error=False):
    return json.dumps(
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": call_id,
                        "is_error": is_error,
                        "content": [{"type": "text", "text": json.dumps(payload)}],
                    }
                ]
            },
        }
    )


def good_trace(pack_mode="on", term_count=12):
    return [
        tool_use("get_taxonomy", "c1"),
        tool_result("c1", {"version": 1}),
        tool_use("get_jargon_pack", "c2", {"game": "Clash of Clans"}),
        tool_result("c2", {"pack_mode": pack_mode, "term_count": term_count, "terms": []}),
        tool_use("get_reviews", "c3", {"game": "Clash of Clans"}),
        tool_result("c3", {"returned": 10}),
        tool_use("save_triage", "c4", {"run_id": "r"}),
        tool_result("c4", {"saved": "runs/r/output.json"}),
    ]


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def test_short_tool_name_strips_the_mcp_namespace():
    assert short_tool_name("mcp__review-triage__get_jargon_pack") == "get_jargon_pack"
    assert short_tool_name("Read") == "Read"


def test_parse_trace_skips_unparseable_lines():
    events = parse_trace(['{"type":"a"}', "not json", "", '{"type":"b"}'])
    assert [event["type"] for event in events] == ["a", "b"]


def test_tool_calls_are_paired_with_their_results():
    calls = extract_tool_calls(parse_trace(good_trace()))
    assert [call.name for call in calls] == [
        "get_taxonomy",
        "get_jargon_pack",
        "get_reviews",
        "save_triage",
    ]
    pack_call = calls[1]
    assert pack_call.arguments == {"game": "Clash of Clans"}
    assert pack_call.result["pack_mode"] == "on"


def test_structured_content_results_are_understood():
    """Newer SDKs return structured content alongside the text block."""
    lines = [
        tool_use("get_jargon_pack", "c1"),
        json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "c1",
                            "structuredContent": {"pack_mode": "off", "term_count": 0},
                        }
                    ]
                },
            }
        ),
    ]
    assert pack_modes(extract_tool_calls(parse_trace(lines))) == ["off"]


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------


def test_a_good_run_passes_and_reports_a_summary():
    summary = verify_run(good_trace("on", 12), expected_pack_mode="on")
    assert summary["pack_mode"] == "on"
    assert summary["get_jargon_pack_calls"] == 1
    assert summary["pack_term_counts"] == [12]
    assert "save_triage" in summary["tools_used"]


def test_pack_off_run_passes_with_zero_terms():
    summary = verify_run(good_trace("off", 0), expected_pack_mode="off")
    assert summary["pack_term_counts"] == [0]


def test_mode_mismatch_is_rejected():
    """The central guard: a run that silently ran in the wrong condition."""
    with pytest.raises(TraceError, match="supposed to be pack ON"):
        verify_run(good_trace("off", 0), expected_pack_mode="on")
    with pytest.raises(TraceError, match="supposed to be pack OFF"):
        verify_run(good_trace("on", 12), expected_pack_mode="off")


def test_pack_on_with_no_terms_anywhere_is_rejected():
    """Pack ON that delivered nothing is indistinguishable from pack OFF."""
    with pytest.raises(TraceError, match="indistinguishable from pack OFF"):
        verify_run(good_trace("on", 0), expected_pack_mode="on")


def test_missing_pack_mode_is_rejected():
    lines = [
        tool_use("get_taxonomy", "c1"), tool_result("c1", {}),
        tool_use("get_jargon_pack", "c2"), tool_result("c2", {"term_count": 5}),
        tool_use("get_reviews", "c3"), tool_result("c3", {}),
        tool_use("save_triage", "c4"), tool_result("c4", {}),
    ]
    with pytest.raises(TraceError, match="no result reported pack_mode"):
        verify_run(lines, expected_pack_mode="on")


def test_skipping_a_required_tool_is_rejected():
    """A run that never fetched the pack is not a test of the pack."""
    lines = [
        tool_use("get_taxonomy", "c1"), tool_result("c1", {}),
        tool_use("get_reviews", "c2"), tool_result("c2", {}),
        tool_use("save_triage", "c3"), tool_result("c3", {}),
    ]
    with pytest.raises(TraceError, match="get_jargon_pack"):
        verify_run(lines, expected_pack_mode="on")


def test_tool_errors_are_rejected():
    lines = good_trace()
    lines[3] = tool_result("c2", {"pack_mode": "on"}, is_error=True)
    with pytest.raises(TraceError, match="returned errors"):
        verify_run(lines, expected_pack_mode="on")


def test_empty_trace_is_rejected():
    with pytest.raises(TraceError, match="trace is empty"):
        verify_run([], expected_pack_mode="on")


def test_bad_expected_mode_is_a_programming_error():
    with pytest.raises(ValueError, match="must be 'on' or 'off'"):
        verify_run(good_trace(), expected_pack_mode="maybe")
