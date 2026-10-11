"""Canonical filesystem locations.

Everything resolves from the repository root so the code behaves the same on
Windows and POSIX, and regardless of the current working directory.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

RAW_CSV = REPO_ROOT / "data" / "raw" / "game_reviews.csv"

INTERIM_DIR = REPO_ROOT / "data" / "interim"
REVIEWS_JSONL = INTERIM_DIR / "reviews.jsonl"

SPLITS_DIR = REPO_ROOT / "data" / "splits"
SPLIT_MANIFEST = SPLITS_DIR / "split_manifest.json"

GOLDEN_DIR = REPO_ROOT / "data" / "golden"
GOLDEN_SET = GOLDEN_DIR / "golden_set.jsonl"
LABELS_PARTIAL = GOLDEN_DIR / "labels.partial.jsonl"

# Review ids held back from eval runs, with a reason but no labels. Written at
# export time. This exists so the tools can skip unlabelable reviews without
# ever reading the answer key.
EXCLUDED_REVIEWS = GOLDEN_DIR / "excluded_reviews.json"

PACKS_DIR = REPO_ROOT / "packs"
TAXONOMY_FILE = REPO_ROOT / "taxonomy" / "categories.yaml"

RUNS_DIR = REPO_ROOT / "runs"
RESULTS_DIR = REPO_ROOT / "results"

# The two games under evaluation. Adding a game to the *eval* means adding it
# here; adding a game the *skill* can triage only means dropping a pack file
# into packs/ (see triage.packs.list_games).
EVAL_GAMES = ("Clash of Clans", "Candy Crush Saga")

# Reserved as held-out games, never used to build or tune anything.
HELD_OUT_GAMES = ("PUBG Mobile", "Subway Surfers")


def game_slug(game: str) -> str:
    """'Clash of Clans' -> 'clash_of_clans' (used for pack filenames)."""
    return game.lower().replace(" ", "_")
