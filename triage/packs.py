"""Jargon pack discovery, loading and validation.

A jargon pack is one YAML file per game teaching the skill that game's slang.
Packs are found by **scanning the packs/ directory**, never from a hard-coded
list, because the whole claim of this project is that adding a game means adding
one file and nothing else. tests/test_add_game.py enforces that.

Pack rules, enforced by the schema here:
  * every term states where its meaning came from (`source`)
  * `official` requires a `source_url` pointing at the publisher
  * `inferred_from_reviews` requires at least one dev-split review id as evidence
  * meanings are written in our own words; source text is never copied

The evidence ids are what makes the no-leakage claim checkable:
tests/test_leakage.py asserts none of them belongs to the golden set.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from triage import paths

SOURCE_OFFICIAL = "official"
SOURCE_INFERRED = "inferred_from_reviews"
VALID_SOURCES = (SOURCE_OFFICIAL, SOURCE_INFERRED)

#: Files starting with "_" are templates and examples, not real packs.
TEMPLATE_PREFIX = "_"


class PackError(ValueError):
    """A pack file is missing or malformed."""


@dataclass(frozen=True)
class Term:
    term: str
    meaning: str
    source: str
    aliases: tuple[str, ...] = ()
    source_url: str | None = None
    evidence_review_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"term": self.term, "meaning": self.meaning}
        if self.aliases:
            payload["aliases"] = list(self.aliases)
        payload["source"] = self.source
        if self.source_url:
            payload["source_url"] = self.source_url
        return payload


@dataclass(frozen=True)
class Pack:
    game: str
    version: int
    description: str
    terms: tuple[Term, ...]
    path: Path

    def evidence_review_ids(self) -> list[str]:
        return [rid for term in self.terms for rid in term.evidence_review_ids]

    def as_dict(self) -> dict[str, Any]:
        """The payload handed to the skill when the pack is enabled."""
        return {
            "game": self.game,
            "version": self.version,
            "description": self.description,
            "term_count": len(self.terms),
            "terms": [term.as_dict() for term in self.terms],
        }


def pack_path_for(game: str, packs_dir: Path | None = None) -> Path:
    packs_dir = packs_dir or paths.PACKS_DIR
    return packs_dir / f"{paths.game_slug(game)}.yaml"


def list_pack_files(packs_dir: Path | None = None) -> list[Path]:
    packs_dir = packs_dir or paths.PACKS_DIR
    if not packs_dir.exists():
        return []
    return sorted(
        path
        for path in packs_dir.glob("*.yaml")
        if not path.name.startswith(TEMPLATE_PREFIX)
    )


def list_games(packs_dir: Path | None = None) -> list[str]:
    """Every game that has a pack, read from the filesystem.

    The game name comes from inside the file rather than from the filename, so a
    pack is self-describing and a typo in a filename cannot silently rename a game.
    """
    games: list[str] = []
    for path in list_pack_files(packs_dir):
        try:
            games.append(load_pack_file(path).game)
        except PackError:
            # A broken pack must not take down discovery for the others; the
            # dedicated pack tests are what fail loudly about it.
            continue
    return sorted(games)


def load_pack_file(path: Path) -> Pack:
    """Parse and validate one pack file."""
    if not path.exists():
        raise PackError(f"pack file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise PackError(f"{path.name}: pack must be a mapping")
    for key in ("game", "version", "terms"):
        if key not in raw:
            raise PackError(f"{path.name}: missing required key '{key}'")
    if not isinstance(raw["terms"], list) or not raw["terms"]:
        raise PackError(f"{path.name}: 'terms' must be a non-empty list")

    terms: list[Term] = []
    seen: set[str] = set()
    for entry in raw["terms"]:
        if not isinstance(entry, dict):
            raise PackError(f"{path.name}: each term must be a mapping, got {entry!r}")
        for key in ("term", "meaning", "source"):
            if not entry.get(key):
                raise PackError(f"{path.name}: term {entry.get('term')!r} is missing '{key}'")

        name = str(entry["term"]).strip()
        key = name.lower()
        if key in seen:
            raise PackError(f"{path.name}: duplicate term '{name}'")
        seen.add(key)

        source = str(entry["source"]).strip()
        if source not in VALID_SOURCES:
            raise PackError(
                f"{path.name}: term '{name}' has source {source!r}, expected one of {VALID_SOURCES}"
            )

        source_url = entry.get("source_url")
        evidence = tuple(str(rid) for rid in entry.get("evidence_review_ids", ()) or ())

        if source == SOURCE_OFFICIAL and not source_url:
            raise PackError(
                f"{path.name}: term '{name}' claims an official source but has no source_url"
            )
        if source == SOURCE_INFERRED and not evidence:
            raise PackError(
                f"{path.name}: term '{name}' is inferred from reviews but cites no "
                "evidence_review_ids"
            )
        if source == SOURCE_INFERRED and source_url:
            raise PackError(
                f"{path.name}: term '{name}' is inferred from reviews, so it must not "
                "carry a source_url (do not invent one)"
            )

        aliases = tuple(str(alias).strip() for alias in entry.get("aliases", ()) or ())
        if key in {alias.lower() for alias in aliases}:
            raise PackError(f"{path.name}: term '{name}' lists itself as an alias")

        terms.append(
            Term(
                term=name,
                meaning=str(entry["meaning"]).strip(),
                source=source,
                aliases=aliases,
                source_url=str(source_url).strip() if source_url else None,
                evidence_review_ids=evidence,
            )
        )

    return Pack(
        game=str(raw["game"]).strip(),
        version=int(raw["version"]),
        description=str(raw.get("description", "")).strip(),
        terms=tuple(terms),
        path=path,
    )


def load_pack(game: str, packs_dir: Path | None = None) -> Pack:
    """Load a game's pack by name, matching the `game` field inside the files."""
    for path in list_pack_files(packs_dir):
        pack = load_pack_file(path)
        if pack.game.lower() == game.lower():
            return pack
    raise PackError(f"no jargon pack for game {game!r}")


def empty_pack_payload(game: str, reason: str) -> dict[str, Any]:
    """What the skill receives when the pack is disabled or absent.

    Shape-identical to an enabled pack so the skill takes the same code path in
    both conditions: the pack OFF condition is this payload, not a different
    prompt.
    """
    return {
        "game": game,
        "version": 0,
        "description": "",
        "term_count": 0,
        "terms": [],
        "reason": reason,
    }
