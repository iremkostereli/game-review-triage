"""Adding a game must require only a new YAML file.

This is one of the project's explicit claims, so it is tested rather than
asserted in a README. Every test here works on a temporary directory: dropping a
file in makes a game appear, and nothing in the code names the games.
"""

from __future__ import annotations

import pytest

from triage import packs

MINIMAL_PACK = """
game: Imaginary Battle Arena
version: 1
description: A test game.
terms:
  - term: Nexus Core
    aliases: [nc, nexus]
    meaning: The structure a team defends, worded in our own words.
    triage_hint: Complaints about it being destroyed too fast are difficulty_balance.
    source: official
    source_url: https://example.com/help/nexus-core
  - term: gigacamp
    meaning: Players appear to use this for holding one position for a long time.
    triage_hint: Usually a fairness complaint, so difficulty_balance.
    source: inferred_from_reviews
    evidence_review_ids: [dev-review-1]
"""


def write_pack(directory, filename, body):
    path = directory / filename
    path.write_text(body, encoding="utf-8")
    return path


def test_a_new_game_appears_from_a_single_file(tmp_path):
    assert packs.list_games(tmp_path) == []

    write_pack(tmp_path, "imaginary_battle_arena.yaml", MINIMAL_PACK)

    assert packs.list_games(tmp_path) == ["Imaginary Battle Arena"]


def test_the_new_game_pack_loads_and_is_usable(tmp_path):
    write_pack(tmp_path, "imaginary_battle_arena.yaml", MINIMAL_PACK)

    pack = packs.load_pack("Imaginary Battle Arena", tmp_path)
    payload = pack.as_dict()

    assert payload["term_count"] == 2
    assert payload["terms"][0]["aliases"] == ["nc", "nexus"]
    assert {term["source"] for term in payload["terms"]} == {
        "official",
        "inferred_from_reviews",
    }


def test_game_name_comes_from_the_file_not_the_filename(tmp_path):
    """A filename typo must not silently rename a game."""
    write_pack(tmp_path, "totally_wrong_name.yaml", MINIMAL_PACK)
    assert packs.list_games(tmp_path) == ["Imaginary Battle Arena"]


def test_lookup_is_case_insensitive(tmp_path):
    write_pack(tmp_path, "imaginary_battle_arena.yaml", MINIMAL_PACK)
    assert packs.load_pack("imaginary battle arena", tmp_path).game == "Imaginary Battle Arena"


def test_templates_are_not_treated_as_packs(tmp_path):
    write_pack(tmp_path, "_TEMPLATE.yaml", MINIMAL_PACK)
    assert packs.list_games(tmp_path) == []


def test_a_broken_pack_does_not_hide_the_working_ones(tmp_path):
    write_pack(tmp_path, "imaginary_battle_arena.yaml", MINIMAL_PACK)
    write_pack(tmp_path, "broken.yaml", "game: Broken\nversion: 1\n")  # no terms

    assert packs.list_games(tmp_path) == ["Imaginary Battle Arena"]
    with pytest.raises(packs.PackError, match="missing required key 'terms'"):
        packs.load_pack_file(tmp_path / "broken.yaml")


def test_missing_game_is_a_clear_error(tmp_path):
    with pytest.raises(packs.PackError, match="no jargon pack"):
        packs.load_pack("Nonexistent Game", tmp_path)


def test_the_shipped_template_is_valid(tmp_path):
    """The template people copy must itself parse, or the first new game breaks."""
    from triage import paths

    pack = packs.load_pack_file(paths.PACKS_DIR / "_TEMPLATE.yaml")
    assert pack.game == "Example Game"
    assert len(pack.terms) == 2


def test_no_game_list_is_hard_coded_in_the_pack_loader():
    """Game names may only live in packs/ and in the eval-games constant."""
    import inspect

    source = inspect.getsource(packs)
    for game in ("Clash of Clans", "Candy Crush Saga", "PUBG", "Subway Surfers"):
        assert game not in source, f"{game} is hard-coded in triage/packs.py"
