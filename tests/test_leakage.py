"""The no-leakage guarantee, enforced rather than promised.

The golden set is held out. A jargon pack is allowed to be built from the dev
split and from official publisher documentation, and from nothing else. If a
pack term were derived from a golden review, the pack ON condition would be
partly fitted to the test set and the headline comparison would be worthless -
and crucially, nothing in the numbers would reveal it.

So the rule is checked here, over the real packs, on every test run.
"""

from __future__ import annotations

import pytest

from triage import packs, paths
from triage.jsonl_io import read_jsonl
from triage.taxonomy import load_taxonomy

needs_corpus = pytest.mark.skipif(
    not paths.REVIEWS_JSONL.exists(),
    reason="run scripts/prepare_data.py first (needs data/raw)",
)


@pytest.fixture(scope="module")
def splits():
    rows = read_jsonl(paths.REVIEWS_JSONL)
    return {
        "golden": {row["reviewId"] for row in rows if row["split"] == "golden"},
        "dev": {row["reviewId"] for row in rows if row["split"] == "dev"},
        "all": {row["reviewId"] for row in rows},
    }


@needs_corpus
def test_no_pack_cites_a_golden_review(splits):
    """The central guard of the whole project."""
    for path in packs.list_pack_files():
        pack = packs.load_pack_file(path)
        leaked = sorted(set(pack.evidence_review_ids()) & splits["golden"])
        assert not leaked, f"{path.name} cites held-out golden reviews: {leaked}"


@needs_corpus
def test_pack_evidence_points_at_real_dev_reviews(splits):
    """A fabricated or mistyped review id would make the evidence unverifiable."""
    for path in packs.list_pack_files():
        pack = packs.load_pack_file(path)
        cited = set(pack.evidence_review_ids())
        unknown = sorted(cited - splits["all"])
        assert not unknown, f"{path.name} cites review ids not in the corpus: {unknown}"
        assert cited <= splits["dev"], f"{path.name} cites non-dev reviews"


@needs_corpus
def test_taxonomy_examples_stay_in_the_dev_split(splits):
    """The taxonomy ships inside the prompt too, so it is bound by the same rule."""
    cited = set(load_taxonomy().example_review_ids())
    assert cited
    assert not cited & splits["golden"]
    assert cited <= splits["dev"]


@needs_corpus
def test_every_inferred_term_is_backed_by_evidence_that_mentions_it():
    """An inferred meaning must be checkable against the reviews it came from.

    Guards against a meaning written from memory and then given an unrelated
    review id to satisfy the schema.
    """
    rows = {row["reviewId"]: row for row in read_jsonl(paths.REVIEWS_JSONL)}

    for path in packs.list_pack_files():
        pack = packs.load_pack_file(path)
        for term in pack.terms:
            if term.source != packs.SOURCE_INFERRED:
                continue
            wanted = [term.term.lower()] + [alias.lower() for alias in term.aliases]
            matched = False
            for review_id in term.evidence_review_ids:
                content = rows[review_id]["content"].lower()
                if any(word in content for word in wanted):
                    matched = True
                    break
            assert matched, (
                f"{path.name}: term '{term.term}' is inferred from reviews, but none of "
                f"its cited reviews contains the term or any of its aliases"
            )


#: Spellings that mean the same element.
_SPELLINGS = {"colour": "color", "liquorice": "licorice"}

#: Words that carry no meaning when comparing an alias with its term.
_FILLER = {"and", "the", "a"}


def _normalise(text: str) -> str:
    """Reduce a phrase to a comparable core: lowercase, de-pluralised, no filler."""
    words = []
    for raw in text.lower().replace("&", " ").replace("-", " ").split():
        word = "".join(char for char in raw if char.isalnum())
        if not word or word in _FILLER:
            continue
        word = _SPELLINGS.get(word, word)
        if word.endswith("ies") and len(word) > 4:
            word = word[:-3] + "y"
        elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            word = word[:-1]
        words.append(word)
    return "".join(words)


def _is_surface_variant(alias: str, term: str) -> bool:
    """True when the alias is the term restated rather than a new word.

    Covers plurals, British spelling, punctuation, and compounds that contain
    the term ("super hard level" for "Hard Level", "extra moves x5" for "Extra
    Moves"). Anything that is genuinely a different word has to be attested in a
    dev review instead.
    """
    alias_norm, term_norm = _normalise(alias), _normalise(term)
    if not alias_norm or not term_norm:
        return False
    return alias_norm in term_norm or term_norm in alias_norm


@needs_corpus
def test_every_alias_is_attested_in_dev_or_is_a_spelling_of_the_term():
    """An alias has to be something players or the publisher actually say.

    Without this, aliases drift into invented synonyms, and an invented alias is
    how vocabulary from the held-out set slips into a pack: a term remembered
    from a golden review looks exactly like a reasonable guess.
    """
    rows = read_jsonl(paths.REVIEWS_JSONL)
    dev_text = {}
    for row in rows:
        if row["split"] == "dev":
            dev_text.setdefault(row["game"], []).append(row["content"].lower())

    problems = []
    for path in packs.list_pack_files():
        pack = packs.load_pack_file(path)
        corpus = dev_text.get(pack.game, [])
        for term in pack.terms:
            for alias in term.aliases:
                if _is_surface_variant(alias, term.term):
                    continue
                if alias in term.source_aliases:
                    # Declared as appearing in the cited official page; auditable
                    # against source_url, like the meaning itself.
                    continue
                if any(alias.lower() in content for content in corpus):
                    continue
                problems.append(f"{path.name}: '{term.term}' alias {alias!r}")

    assert not problems, (
        "these aliases are not in any dev review, not a spelling of their term, and "
        "not declared as coming from the official page:\n  " + "\n  ".join(problems)
    )


def test_packs_do_not_quote_long_runs_of_source_text():
    """Meanings are paraphrased. A long verbatim quote would be a copyright risk.

    A crude but useful proxy: no meaning should be a single very long sentence
    lifted wholesale, and no meaning may contain a source URL.
    """
    for path in packs.list_pack_files():
        pack = packs.load_pack_file(path)
        for term in pack.terms:
            assert "http" not in term.meaning, f"{term.term}: meaning contains a URL"
            assert len(term.meaning) < 600, f"{term.term}: meaning is suspiciously long"
