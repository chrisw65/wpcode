from __future__ import annotations

import json
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


def test_load_snippets_honors_legacy_auto_insert(tmp_path):
    export = [
        {
            "id": 1,
            "title": "Active legacy snippet",
            "code": "<?php echo 'active'; ?>",
            "code_type": "php",
            "auto_insert": 1,
        },
        {
            "id": 2,
            "title": "Inactive legacy snippet",
            "code": "<?php echo 'inactive'; ?>",
            "code_type": "php",
            "auto_insert": 0,
        },
    ]
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(export), encoding="utf-8")

    snippets = load_snippets(path)

    assert [snippet.identifier for snippet in snippets] == ["1"]


def test_load_snippets_reports_languages_and_counts(tmp_path):
    export = {
        "snippets": [
            {
                "id": "php",
                "title": "PHP Snippet",
                "code": "<?php echo 'php'; ?>",
                "code_type": "php",
                "active": True,
            },
            {
                "id": "css",
                "title": "CSS Snippet",
                "code": ".example { color: red; }",
                "code_type": "css",
                "active": True,
            },
            {
                "id": "js",
                "title": "JS Snippet",
                "code": "console.log('js');",
                "code_type": "js",
                "active": True,
            },
        ]
    }
    path = tmp_path / "languages.json"

    path.write_text(json.dumps(export), encoding="utf-8")

    snippets = load_snippets(path)

    languages = sorted(snippet.language for snippet in snippets)

    assert len(snippets) == 3
    assert languages == ["css", "javascript", "php"]


def test_load_snippets_verbose_logging(tmp_path, capsys):
    export = [
        {
            "id": "active",
            "title": "Active snippet",
            "code": "<?php echo 'active'; ?>",
            "code_type": "php",
            "auto_insert": 1,
        },
        {
            "id": "inactive",
            "title": "Inactive snippet",
            "code": "<?php echo 'inactive'; ?>",
            "code_type": "php",
            "auto_insert": 0,
        },
    ]
    path = tmp_path / "verbose.json"
    path.write_text(json.dumps(export), encoding="utf-8")

    snippets = load_snippets(path, verbose=True)

    out = capsys.readouterr().out

    assert len(snippets) == 1
    assert "Found 2 snippet entries" in out
    assert "Skipping inactive snippet 'inactive'" in out
    assert "Loaded snippet 'active'" in out
