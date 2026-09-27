"""JSONL helpers with explicit UTF-8 everywhere.

The dataset is full of emoji and non-Latin text, and the development machine's
console codepage is cp1254. Every read and write in this project therefore names
its encoding explicitly instead of relying on the platform default.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a whole JSONL file. Blank lines are skipped."""
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Stream a JSONL file one record at a time."""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    """Write records as JSONL, returning how many were written.

    Uses "\\n" newlines and ensure_ascii=False so the files are identical on
    Windows and POSIX, which matters because determinism is asserted in tests.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
            count += 1
    return count


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append a single record, flushing so progress survives a crash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        handle.write("\n")
        handle.flush()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
