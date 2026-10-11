"""Tests for the MCP tool behaviour, called directly as plain functions.

The most important test here is that get_reviews cannot hand the hand-made
answer key to the system being evaluated. If a single label field leaked into a
review payload, every result in this repo would be worthless, and it would not
be visible from the numbers.
"""

from __future__ import annotations

import json

import pytest

from triage import paths, tools
from triage.jsonl_io import read_jsonl, write_jsonl

needs_corpus = pytest.mark.skipif(
    not (paths.GOLDEN_DIR / "golden_pool.jsonl").exists(),
    reason="run scripts/prepare_data.py first",
)


# --------------------------------------------------------------------------
# get_reviews must never expose the answer key
# --------------------------------------------------------------------------


@needs_corpus
def test_get_reviews_returns_no_golden_labels():
    page = tools.get_reviews(limit=200)
    assert page["returned"] > 0

    for review in page["reviews"]:
        for field in tools.GOLDEN_LABEL_FIELDS:
            assert field not in review, f"label field '{field}' leaked into get_reviews"


@needs_corpus
def test_get_reviews_returns_no_sampling_hints():
    """Why a review was sampled must stay hidden, in both directions.

    Knowing a review was picked because a keyword matched would let the jargon
    slice be scored by the heuristic instead of by the hand-set flag.
    """
    page = tools.get_reviews(limit=200)
    for review in page["reviews"]:
        for field in tools.SAMPLING_HINT_FIELDS:
            assert field not in review, f"sampling hint '{field}' leaked into get_reviews"


@needs_corpus
def test_get_reviews_returns_exactly_the_public_fields():
    page = tools.get_reviews(limit=5)
    for review in page["reviews"]:
        assert set(review) == set(tools.REVIEW_PUBLIC_FIELDS)


@needs_corpus
def test_get_reviews_ignores_the_exported_golden_set(tmp_path, monkeypatch):
    """Even with a finished answer key on disk, reviews come from the pool.

    This is the regression guard: golden_set.jsonl holds labels, so the tool must
    read golden_pool.jsonl and nothing else.
    """
    pool = read_jsonl(paths.GOLDEN_DIR / "golden_pool.jsonl")[:3]

    fake_golden_dir = tmp_path / "golden"
    write_jsonl(fake_golden_dir / "golden_pool.jsonl", pool)
    # A plausible answer key sitting right next to the pool.
    write_jsonl(
        fake_golden_dir / "golden_set.jsonl",
        [
            {**review, "categories": ["ads"], "severity": "high", "has_jargon": True,
             "note": "secret", "unclear": False}
            for review in pool
        ],
    )
    monkeypatch.setattr(paths, "GOLDEN_DIR", fake_golden_dir)

    page = tools.get_reviews(limit=10)
    assert page["returned"] == 3
    serialised = json.dumps(page)
    assert "secret" not in serialised
    for review in page["reviews"]:
        assert "categories" not in review and "severity" not in review


@needs_corpus
def test_unclear_reviews_are_never_sent_to_the_model():
    """Reviews the annotator could not label are withheld from eval runs.

    They stay in the golden set and are reported separately. Scoring a model on
    text a person could not label would measure nothing.
    """
    withheld = tools.excluded_review_ids()
    if not withheld:
        pytest.skip("no reviews are currently withheld")

    page = tools.get_reviews(limit=200)
    returned = {review["reviewId"] for review in page["reviews"]}
    assert returned & withheld == set()
    assert page["withheld"] == len(withheld)


def test_the_exclusions_file_carries_no_labels(tmp_path, monkeypatch):
    """It may contain ids and reasons only, never a hint of the answer."""
    from triage.labels import write_exclusions

    out = tmp_path / "excluded_reviews.json"
    write_exclusions(
        [
            {"reviewId": "r1", "unclear": True, "categories": ["ads"], "severity": "high",
             "has_jargon": True, "note": "secret"},
            {"reviewId": "r2", "unclear": False, "categories": ["no_issue"]},
        ],
        out,
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["count"] == 1
    assert payload["excluded"] == [{"reviewId": "r1", "reason": "unclear"}]
    serialised = out.read_text(encoding="utf-8")
    for leak in ("ads", "high", "secret", "has_jargon", "no_issue"):
        assert leak not in serialised


def test_missing_exclusions_file_means_nothing_is_withheld(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "EXCLUDED_REVIEWS", tmp_path / "nope.json")
    assert tools.excluded_review_ids() == set()


def test_no_code_path_in_the_tools_touches_the_answer_key():
    """Belt and braces: no executable code may reference golden_set.

    Docstrings are stripped first, because the module deliberately explains in
    prose that it does not read that file.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(tools))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]

    code = ast.unparse(ast.fix_missing_locations(tree))
    assert "golden_set" not in code.lower(), "tools.py has a code path reaching the answer key"


# --------------------------------------------------------------------------
# get_jargon_pack always declares its mode
# --------------------------------------------------------------------------


def test_pack_mode_is_reported_in_both_conditions(monkeypatch):
    monkeypatch.setenv(tools.PACK_MODE_ENV, "on")
    assert tools.get_jargon_pack("Clash of Clans")["pack_mode"] == "on"

    monkeypatch.setenv(tools.PACK_MODE_ENV, "off")
    off = tools.get_jargon_pack("Clash of Clans")
    assert off["pack_mode"] == "off"
    assert "disabled" in off["reason"]


def test_pack_off_and_on_payloads_have_the_same_shape(monkeypatch):
    monkeypatch.setenv(tools.PACK_MODE_ENV, "on")
    on = tools.get_jargon_pack("Clash of Clans")
    monkeypatch.setenv(tools.PACK_MODE_ENV, "off")
    off = tools.get_jargon_pack("Clash of Clans")
    assert set(on) == set(off)


def test_unset_pack_mode_defaults_to_on(monkeypatch):
    monkeypatch.delenv(tools.PACK_MODE_ENV, raising=False)
    assert tools.pack_mode() == "on"


def test_pack_mode_accepts_common_falsey_spellings(monkeypatch):
    for value in ("off", "OFF", "0", "false", "no"):
        monkeypatch.setenv(tools.PACK_MODE_ENV, value)
        assert tools.pack_mode() == "off", value


def test_missing_game_is_rejected():
    with pytest.raises(ValueError, match="'game' is required"):
        tools.get_jargon_pack("")


# --------------------------------------------------------------------------
# Other tools
# --------------------------------------------------------------------------


def test_list_games_reports_its_discovery_method():
    result = tools.list_games()
    assert "directory scan" in result["source"]
    assert result["count"] == len(result["games"])


def test_get_taxonomy_exposes_the_full_label_space():
    taxonomy = tools.get_taxonomy()
    assert len(taxonomy["categories"]) == 8
    assert "cases" in taxonomy["boundaries"]
    assert all(category["severity_guidance"] for category in taxonomy["categories"])


@needs_corpus
def test_get_reviews_pages_without_overlap():
    first = tools.get_reviews(limit=10, offset=0)
    second = tools.get_reviews(limit=10, offset=10)
    ids_first = {review["reviewId"] for review in first["reviews"]}
    ids_second = {review["reviewId"] for review in second["reviews"]}
    assert ids_first & ids_second == set()


@needs_corpus
def test_get_reviews_validates_its_arguments():
    with pytest.raises(ValueError, match="must be 'golden' or 'dev'"):
        tools.get_reviews(split="test")
    with pytest.raises(ValueError, match="between 1 and 200"):
        tools.get_reviews(limit=500)
    with pytest.raises(ValueError, match="must not be negative"):
        tools.get_reviews(offset=-1)


def test_save_triage_writes_where_told_and_records_the_mode(tmp_path, monkeypatch):
    monkeypatch.setenv(tools.RUNS_DIR_ENV, str(tmp_path))
    monkeypatch.setenv(tools.PACK_MODE_ENV, "off")

    result = tools.save_triage(
        run_id="test-run",
        results=[{"reviewId": "r1", "categories": ["ads"], "severity": "low"}],
        game="Clash of Clans",
        issue_groups=[{"title": "Ads interrupt play", "review_ids": ["r1"]}],
    )

    saved = tmp_path / "test-run" / "output.json"
    assert saved.exists()
    payload = json.loads(saved.read_text(encoding="utf-8"))
    assert payload["pack_mode"] == "off"
    assert payload["result_count"] == 1
    assert len(payload["issue_groups"]) == 1
    assert result["saved"] == str(saved)


def test_save_triage_rejects_unsafe_run_ids(tmp_path, monkeypatch):
    monkeypatch.setenv(tools.RUNS_DIR_ENV, str(tmp_path))
    for bad in ("", "../escape", "a/b", "c:\\x"):
        with pytest.raises(ValueError, match="safe directory name"):
            tools.save_triage(run_id=bad, results=[{"reviewId": "r"}])


def test_save_triage_rejects_empty_results(tmp_path, monkeypatch):
    monkeypatch.setenv(tools.RUNS_DIR_ENV, str(tmp_path))
    with pytest.raises(ValueError, match="non-empty list"):
        tools.save_triage(run_id="r", results=[])
