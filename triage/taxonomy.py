"""Load and validate the issue taxonomy, and validate labels against it.

`taxonomy/categories.yaml` is the single source of truth for the label space.
This module is the only way the rest of the project reads it, so the labeling UI,
the MCP server and the scorer can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

import yaml

from triage import paths

#: The label that may not be combined with any other.
NO_ISSUE = "no_issue"
#: The fallback label, used only when no specific category fits.
OTHER_ISSUE = "other_issue"

SEVERITY_ORDER = ("low", "medium", "high")


class TaxonomyError(ValueError):
    """The taxonomy file is malformed."""


class LabelError(ValueError):
    """A label record violates the taxonomy's rules."""


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    definition: str
    includes: tuple[str, ...]
    excludes: tuple[str, ...]
    examples: tuple[dict[str, Any], ...]
    severity_guidance: dict[str, Any]
    exclusive: bool = False


@dataclass(frozen=True)
class Taxonomy:
    version: int
    description: str
    categories: tuple[Category, ...]
    severity_levels: tuple[str, ...]
    severity: dict[str, Any]
    labeling_rules: dict[str, str]
    boundaries: dict[str, Any]
    flags: dict[str, Any]
    cited_review_ids: tuple[str, ...]

    @property
    def category_ids(self) -> tuple[str, ...]:
        return tuple(category.id for category in self.categories)

    @property
    def issue_category_ids(self) -> tuple[str, ...]:
        """Every category that represents an actual issue (i.e. not `no_issue`)."""
        return tuple(c.id for c in self.categories if not c.exclusive)

    def get(self, category_id: str) -> Category:
        for category in self.categories:
            if category.id == category_id:
                return category
        raise KeyError(category_id)

    def example_review_ids(self) -> list[str]:
        """Every review id cited anywhere in the taxonomy. Used by the leakage test."""
        return list(self.cited_review_ids)


def _collect_review_ids(node: Any) -> list[str]:
    """Walk the parsed YAML and return every `review_id` value found.

    Deliberately recursive rather than reading known locations: examples are
    cited in category examples, in the per-category severity guidance, and in the
    boundary cases, and a new section must not silently escape the leakage test.
    """
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "review_id" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_collect_review_ids(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_collect_review_ids(item))
    return found


def load_taxonomy(path=None) -> Taxonomy:
    """Parse and validate the taxonomy file."""
    path = path or paths.TAXONOMY_FILE
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise TaxonomyError("taxonomy file must contain a mapping")

    for key in ("version", "categories", "severity"):
        if key not in raw:
            raise TaxonomyError(f"taxonomy is missing required key: {key}")

    categories: list[Category] = []
    seen: set[str] = set()
    for entry in raw["categories"]:
        for key in ("id", "name", "definition"):
            if key not in entry:
                raise TaxonomyError(f"category is missing '{key}': {entry!r}")
        if entry["id"] in seen:
            raise TaxonomyError(f"duplicate category id: {entry['id']}")
        seen.add(entry["id"])
        categories.append(
            Category(
                id=entry["id"],
                name=entry["name"],
                definition=entry["definition"].strip(),
                includes=tuple(entry.get("includes", ())),
                excludes=tuple(entry.get("excludes", ())),
                examples=tuple(entry.get("examples", ())),
                severity_guidance=entry.get("severity_guidance", {}),
                exclusive=bool(entry.get("exclusive", False)),
            )
        )

    if NO_ISSUE not in seen:
        raise TaxonomyError(f"taxonomy must define '{NO_ISSUE}'")
    if OTHER_ISSUE not in seen:
        raise TaxonomyError(f"taxonomy must define '{OTHER_ISSUE}'")

    exclusive = [c.id for c in categories if c.exclusive]
    if exclusive != [NO_ISSUE]:
        raise TaxonomyError(
            f"exactly one category must be exclusive and it must be '{NO_ISSUE}', got {exclusive}"
        )

    severity_levels = tuple(level["id"] for level in raw["severity"]["levels"])
    if set(severity_levels) != set(SEVERITY_ORDER):
        raise TaxonomyError(
            f"severity levels must be {set(SEVERITY_ORDER)}, got {set(severity_levels)}"
        )

    for category in categories:
        if not category.severity_guidance:
            raise TaxonomyError(f"category '{category.id}' has no severity_guidance")

    return Taxonomy(
        version=int(raw["version"]),
        description=raw.get("description", "").strip(),
        categories=tuple(categories),
        severity_levels=severity_levels,
        severity=raw["severity"],
        labeling_rules=raw.get("labeling_rules", {}),
        boundaries=raw.get("boundaries", {}),
        flags=raw.get("flags", {}),
        cited_review_ids=tuple(_collect_review_ids(raw)),
    )


@lru_cache(maxsize=1)
def get_taxonomy() -> Taxonomy:
    """Cached taxonomy, for callers that read it on every request."""
    return load_taxonomy()


def validate_labels(
    categories: Iterable[str],
    severity: str | None,
    taxonomy: Taxonomy | None = None,
) -> None:
    """Raise LabelError unless this label set obeys the taxonomy's rules.

    The rules enforced here are the ones that make the metrics meaningful:
    `no_issue` is exclusive, `other_issue` is a fallback rather than an extra
    tag, and severity is present exactly when there is an issue to rate.
    """
    taxonomy = taxonomy or get_taxonomy()
    selected = list(categories)

    if not selected:
        raise LabelError("at least one category is required")

    unknown = [c for c in selected if c not in taxonomy.category_ids]
    if unknown:
        raise LabelError(f"unknown categories: {unknown}")

    if len(set(selected)) != len(selected):
        raise LabelError(f"duplicate categories: {selected}")

    if NO_ISSUE in selected and len(selected) > 1:
        raise LabelError(f"'{NO_ISSUE}' cannot be combined with other labels: {selected}")

    if OTHER_ISSUE in selected and len(selected) > 1:
        raise LabelError(
            f"'{OTHER_ISSUE}' is a fallback and cannot be combined with a category "
            f"that already fits: {selected}"
        )

    if NO_ISSUE in selected:
        if severity:
            raise LabelError(f"severity must be empty for '{NO_ISSUE}', got {severity!r}")
    else:
        if not severity:
            raise LabelError("severity is required when an issue category is selected")
        if severity not in taxonomy.severity_levels:
            raise LabelError(
                f"unknown severity {severity!r}, expected one of {taxonomy.severity_levels}"
            )


def validate_label_record(record: dict[str, Any], taxonomy: Taxonomy | None = None) -> None:
    """Validate one row of the golden set.

    A record flagged `unclear` is allowed to carry no categories at all: the
    annotator is saying the text cannot be labeled, and forcing a guess there
    would put noise into the answer key. Such rows are excluded from the primary
    metrics and counted separately.
    """
    taxonomy = taxonomy or get_taxonomy()

    for key in ("reviewId", "categories", "has_jargon"):
        if key not in record:
            raise LabelError(f"label record is missing '{key}': {record!r}")

    if not isinstance(record["categories"], list):
        raise LabelError("'categories' must be a list")
    if not isinstance(record["has_jargon"], bool):
        raise LabelError("'has_jargon' must be a boolean")
    if not isinstance(record.get("unclear", False), bool):
        raise LabelError("'unclear' must be a boolean")
    if not isinstance(record.get("note", ""), str):
        raise LabelError("'note' must be a string")

    if record.get("unclear") and not record["categories"]:
        return

    validate_labels(record["categories"], record.get("severity") or None, taxonomy)
