"""Tests for the jargon pack schema.

The schema is what keeps the project's sourcing rules honest: every term says
where its meaning came from, an official claim needs a real URL, and a term
inferred from player usage must cite the reviews it was inferred from and must
not carry a made-up URL.
"""

from __future__ import annotations

import pytest

from triage import packs


def pack_with(term_yaml: str) -> str:
    return f"game: Test Game\nversion: 1\nterms:\n{term_yaml}"


def write(tmp_path, body):
    path = tmp_path / "test_game.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_official_term_requires_a_source_url(tmp_path):
    path = write(
        tmp_path,
        pack_with(
            "  - term: Gold Pass\n"
            "    meaning: A paid seasonal subscription.\n"
            "    source: official\n"
        ),
    )
    with pytest.raises(packs.PackError, match="no source_url"):
        packs.load_pack_file(path)


def test_inferred_term_requires_evidence_reviews(tmp_path):
    path = write(
        tmp_path,
        pack_with(
            "  - term: barch\n"
            "    meaning: A cheap raiding army composition.\n"
            "    source: inferred_from_reviews\n"
        ),
    )
    with pytest.raises(packs.PackError, match="cites no evidence_review_ids"):
        packs.load_pack_file(path)


def test_inferred_term_must_not_invent_a_url(tmp_path):
    """A term with no official definition must not carry an official-looking URL."""
    path = write(
        tmp_path,
        pack_with(
            "  - term: barch\n"
            "    meaning: A cheap raiding army composition.\n"
            "    source: inferred_from_reviews\n"
            "    source_url: https://example.com/invented\n"
            "    evidence_review_ids: [dev-1]\n"
        ),
    )
    with pytest.raises(packs.PackError, match="must not\\s+carry a source_url"):
        packs.load_pack_file(path)


def test_unknown_source_is_rejected(tmp_path):
    path = write(
        tmp_path,
        pack_with(
            "  - term: Gold Pass\n"
            "    meaning: A paid seasonal subscription.\n"
            "    source: fan_wiki\n"
            "    source_url: https://example.com\n"
        ),
    )
    with pytest.raises(packs.PackError, match="expected one of"):
        packs.load_pack_file(path)


def test_missing_meaning_is_rejected(tmp_path):
    path = write(
        tmp_path,
        pack_with("  - term: Gold Pass\n    source: official\n    source_url: https://e.com\n"),
    )
    with pytest.raises(packs.PackError, match="missing 'meaning'"):
        packs.load_pack_file(path)


def test_duplicate_terms_are_rejected(tmp_path):
    body = pack_with(
        "  - term: Town Hall\n"
        "    meaning: The central building.\n"
        "    source: official\n"
        "    source_url: https://e.com/a\n"
        "  - term: town hall\n"
        "    meaning: Same thing again.\n"
        "    source: official\n"
        "    source_url: https://e.com/b\n"
    )
    with pytest.raises(packs.PackError, match="duplicate term"):
        packs.load_pack_file(write(tmp_path, body))


def test_term_cannot_be_its_own_alias(tmp_path):
    body = pack_with(
        "  - term: Town Hall\n"
        "    aliases: [town hall, th]\n"
        "    meaning: The central building.\n"
        "    source: official\n"
        "    source_url: https://e.com/a\n"
    )
    with pytest.raises(packs.PackError, match="lists itself as an alias"):
        packs.load_pack_file(write(tmp_path, body))


def test_empty_terms_list_is_rejected(tmp_path):
    path = write(tmp_path, "game: Test Game\nversion: 1\nterms: []\n")
    with pytest.raises(packs.PackError, match="non-empty list"):
        packs.load_pack_file(path)


def test_valid_pack_exposes_evidence_ids_for_the_leakage_check(tmp_path):
    body = pack_with(
        "  - term: Gold Pass\n"
        "    meaning: A paid seasonal subscription.\n"
        "    source: official\n"
        "    source_url: https://e.com/a\n"
        "  - term: barch\n"
        "    meaning: A cheap raiding army composition.\n"
        "    source: inferred_from_reviews\n"
        "    evidence_review_ids: [dev-1, dev-2]\n"
    )
    pack = packs.load_pack_file(write(tmp_path, body))
    assert pack.evidence_review_ids() == ["dev-1", "dev-2"]


def test_empty_pack_payload_matches_a_real_pack_shape():
    """Pack OFF must be shape-identical to pack ON, or the skill would branch."""
    body_keys = {"game", "version", "description", "term_count", "terms"}
    empty = packs.empty_pack_payload("Test Game", reason="disabled")
    assert body_keys <= set(empty)
    assert empty["terms"] == []
    assert empty["term_count"] == 0
