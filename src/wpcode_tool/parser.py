from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable, List, Sequence

from .models import Snippet


def _ensure_list(value: object) -> List[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _normalize_language(value: str | None) -> str:
    if not value:
        return "php"
    value = value.strip().lower()
    aliases = {
        "javascript": "javascript",
        "js": "javascript",
        "css": "css",
        "html": "html",
        "php": "php",
        "text": "html",
    }
    return aliases.get(value, value)


def _extract_location(entry: dict) -> str | None:
    auto_insert = entry.get("auto_insert")
    if isinstance(auto_insert, dict):
        location = auto_insert.get("location") or auto_insert.get("locations")
        if isinstance(location, list):
            return str(location[0]).strip() if location else None
        if location:
            return str(location).strip()
        # Some exports store location directly on auto_insert
        if "type" in auto_insert:
            return str(auto_insert["type"]).strip()
    if "location" in entry:
        return str(entry["location"]).strip()
    if "insert_location" in entry:
        return str(entry["insert_location"]).strip()
    return None


def _extract_priority(entry: dict) -> int:
    auto_insert = entry.get("auto_insert")
    if isinstance(auto_insert, dict):
        priority = auto_insert.get("priority") or auto_insert.get("order")
        if priority is not None:
            try:
                return int(priority)
            except (TypeError, ValueError):
                pass
    priority = entry.get("priority")
    if priority is not None:
        try:
            return int(priority)
        except (TypeError, ValueError):
            pass
    return 10


def _extract_tags(entry: dict) -> List[str]:
    tags = _ensure_list(entry.get("tags"))
    return [str(tag).strip() for tag in tags if str(tag).strip()]


def _extract_identifier(entry: dict) -> str:
    for key in ("id", "ID", "snippet_id"):
        if key in entry and entry[key] not in (None, ""):
            return str(entry[key])
    if "title" in entry and entry["title"]:
        return str(entry["title"]).strip().lower().replace(" ", "-")
    if "name" in entry and entry["name"]:
        return str(entry["name"]).strip().lower().replace(" ", "-")
    raise ValueError("Snippet entry is missing an identifier")


def _extract_title(entry: dict) -> str:
    for key in ("title", "name", "label"):
        if key in entry and entry[key]:
            return str(entry[key]).strip()
    return f"Snippet {entry.get('id', '')}".strip()


def _extract_code(entry: dict) -> str:
    for key in ("code", "snippet", "content"):
        if key in entry and entry[key] not in (None, ""):
            return str(entry[key])
    return ""


def _is_active(entry: dict) -> bool:
    for key in ("active", "is_active", "enabled", "status"):
        if key in entry:
            value = entry[key]
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                return value.strip().lower() in {"true", "1", "active", "enabled", "on"}
    auto_insert = entry.get("auto_insert")
    if isinstance(auto_insert, dict):
        return False
    if isinstance(auto_insert, bool):
        return auto_insert
    if isinstance(auto_insert, (int, float)):
        return bool(auto_insert)
    if isinstance(auto_insert, str):
        normalized = auto_insert.strip().lower()
        if normalized in {"true", "1", "yes", "on", "active", "enabled"}:
            return True
        if normalized in {"false", "0", "no", "off", "inactive", "disabled"}:
            return False
        return bool(normalized)
    return False


def _iter_snippet_entries(data: object) -> Iterable[dict]:
    if isinstance(data, dict):
        if "snippets" in data:
            snippets = data["snippets"]
            if isinstance(snippets, dict):
                for entry in snippets.values():
                    if isinstance(entry, dict):
                        yield entry
            elif isinstance(snippets, Sequence):
                for entry in snippets:
                    if isinstance(entry, dict):
                        yield entry
        else:
            # Maybe the dict is already a snippet definition
            if all(key in data for key in ("code", "title")):
                yield data
    elif isinstance(data, Sequence):
        for entry in data:
            if isinstance(entry, dict):
                yield entry


def _entry_label(entry: dict) -> str:
    for key in ("id", "title", "name", "label"):
        if key in entry and entry[key]:
            return str(entry[key])
    return "<unknown>"


def load_snippets(
    path: str | Path,
    *,
    verbose: bool = False,
    log: Callable[[str], None] | None = None,
) -> List[Snippet]:
    """Load and normalize active snippets from a WPCode export."""

    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    logger: Callable[[str], None] | None = log if verbose else None
    if verbose and logger is None:
        logger = print

    entries = list(_iter_snippet_entries(raw))
    if logger:
        logger(f"Found {len(entries)} snippet entr{'y' if len(entries) == 1 else 'ies'} in {path}")

    snippets: List[Snippet] = []
    for entry in entries:
        if not _is_active(entry):
            if logger:
                logger(f"- Skipping inactive snippet {_entry_label(entry)!r}")
            continue

        identifier = _extract_identifier(entry)
        snippet = Snippet(
            identifier=identifier,
            title=_extract_title(entry),
            code=_extract_code(entry),
            language=_normalize_language(entry.get("code_type") or entry.get("type")),
            active=True,
            location=_extract_location(entry),
            priority=_extract_priority(entry),
            tags=_extract_tags(entry),
            notes=str(entry.get("notes")) if entry.get("notes") else None,
        )
        snippets.append(snippet)

        if logger:
            logger(f"- Loaded snippet {identifier!r} ({snippet.language})")

    if logger:
        logger(f"Collected {len(snippets)} active snippet{'s' if len(snippets) != 1 else ''}")

    return snippets
