from __future__ import annotations

from pathlib import Path

from wpcode_tool.builder import build_plugin

FIXTURE = Path(__file__).parent / "fixtures" / "wpcode_export.json"


def test_build_plugin_creates_wordpress_plugin(tmp_path: Path):
    plugin_path = build_plugin(FIXTURE, tmp_path, plugin_slug="generated-snippets")

    main_file = plugin_path / "generated-snippets.php"
    metadata_file = plugin_path / "includes" / "snippet-data.php"
    loader_file = plugin_path / "includes" / "loader.php"
    admin_file = plugin_path / "includes" / "admin-page.php"
    php_snippet = plugin_path / "snippets" / "php" / "snippet-101.php"
    html_snippet = plugin_path / "snippets" / "html" / "snippet-102.html"

    assert main_file.exists()
    assert metadata_file.exists()
    assert loader_file.exists()
    assert admin_file.exists()
    assert php_snippet.exists()
    assert html_snippet.exists()

    metadata = metadata_file.read_text(encoding="utf-8")
    assert "'title' => 'Add Custom Body Class'" in metadata
    assert "'hook' => 'init'" in metadata
    assert "'status' => 'manual'" in metadata
    assert "'path' => 'snippets/php/snippet-101.php'" in metadata

    php_code = php_snippet.read_text(encoding="utf-8")
    assert "add_filter('body_class'" in php_code

    admin_page = admin_file.read_text(encoding="utf-8")
    assert "Generated Snippets" in admin_page
    assert "wpcode-generated__card--manual" in admin_page


def test_subsequent_runs_overwrite_existing_output(tmp_path: Path):
    build_plugin(FIXTURE, tmp_path, plugin_slug="generated-snippets")
    first_files = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())

    build_plugin(FIXTURE, tmp_path, plugin_slug="generated-snippets")
    second_files = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())

    assert first_files == second_files


def test_build_plugin_verbose_emits_messages(tmp_path: Path):
    messages: list[str] = []

    build_plugin(
        FIXTURE,
        tmp_path,
        plugin_slug="generated-snippets",
        verbose=True,
        log=messages.append,
    )

    assert any("Building plugin" in message for message in messages)
    assert any("Wrote" in message for message in messages)
