from __future__ import annotations

from pathlib import Path

from wpcode_tool.parser import load_snippets


FIXTURE = Path(__file__).parent / "fixtures" / "wpcode_export.json"


def test_load_snippets_filters_inactive_entries():
    snippets = load_snippets(FIXTURE)
    identifiers = {snippet.identifier for snippet in snippets}

    assert identifiers == {"101", "102", "104"}


def test_load_snippets_preserves_metadata():
    snippets = load_snippets(FIXTURE)
    snippet = next(s for s in snippets if s.identifier == "101")

    assert snippet.title == "Add Custom Body Class"
    assert snippet.language == "php"
    assert snippet.priority == 12
    assert snippet.location == "everywhere"
    assert snippet.tags == ["theme", "layout"]
    assert snippet.notes == "Adds a CSS class to the body tag"
