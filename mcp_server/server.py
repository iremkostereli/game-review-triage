"""MCP server exposing the review corpus, the taxonomy and the jargon packs.

Built on the official Model Context Protocol Python SDK. In mcp 2.x the class
formerly called FastMCP is `MCPServer` (`mcp.server.mcpserver`); the old
`mcp.server.fastmcp` path deliberately raises a migration error.

Run it directly for stdio:

    uv run mcp_server/server.py

The tool bodies live in triage/tools.py so they can be tested without a protocol
round-trip. This module only declares the interface: names, descriptions and
argument schemas, which the SDK derives from the type hints and docstrings below.

Pack OFF vs pack ON is decided entirely by the TRIAGE_PACK_MODE environment
variable, and only get_jargon_pack reads it. Every pack response reports the mode
it was in so run traces can be verified instead of trusted.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer

from triage import tools

server = MCPServer(
    name="review-triage",
    version="0.1.0",
    instructions=(
        "Tools for triaging mobile game app reviews into actionable LiveOps issues. "
        "Call get_taxonomy for the label space and get_jargon_pack for the game's "
        "vocabulary before triaging. get_jargon_pack may legitimately return zero "
        "terms; use exactly what it gives you."
    ),
)


@server.tool()
def list_games() -> dict[str, Any]:
    """List the games that have a jargon pack.

    Discovered by scanning the packs/ directory, so adding a game needs only a
    new YAML file, with no code or skill changes.
    """
    return tools.list_games()


@server.tool()
def get_taxonomy() -> dict[str, Any]:
    """The issue categories, their boundary rules and the severity rubric.

    This is the single source of truth for the label space. Use these category
    ids and severity values exactly as spelled here.
    """
    return tools.get_taxonomy()


@server.tool()
def get_jargon_pack(game: str) -> dict[str, Any]:
    """The game-specific vocabulary pack for one game.

    May return zero terms, either because the pack is switched off for this run
    or because the game has no pack. The payload shape is identical either way,
    and `pack_mode` states which it was. Always call this before triaging and
    use whatever it returns rather than remembered knowledge about the game.

    Args:
        game: Game name, for example "Clash of Clans".
    """
    return tools.get_jargon_pack(game)


@server.tool()
def get_reviews(
    game: str = "",
    split: Literal["golden", "dev"] = "golden",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Fetch a page of reviews to triage.

    Returns review text and the metadata a triager would legitimately see. It
    never returns hand-made labels or the reasons a review was sampled.

    Args:
        game: Restrict to one game. Omit for all games.
        split: Which split to read. "golden" is what the eval scores.
        limit: Page size, 1 to 200.
        offset: Number of reviews to skip, for paging.
    """
    return tools.get_reviews(game=game, split=split, limit=limit, offset=offset)


@server.tool()
def save_triage(
    run_id: str,
    results: list[dict[str, Any]],
    game: str = "",
    issue_groups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Save the triage results for a run.

    Call once per game with every review you triaged, plus your issue groups.

    Args:
        run_id: Run identifier given to you in the task.
        results: One object per review with reviewId, categories, severity,
            has_jargon, jargon_terms and a one-sentence rationale.
        game: The game these results are for.
        issue_groups: Grouped issues, each with a title, category, severity,
            review_ids and short verbatim evidence quotes.
    """
    return tools.save_triage(
        run_id=run_id, results=results, game=game, issue_groups=issue_groups
    )


if __name__ == "__main__":
    server.run()
