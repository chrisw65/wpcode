from __future__ import annotations

import shutil
import textwrap
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .mapper import plan_snippet
from .models import PlannedSnippet, Snippet


def _sanitize_slug(value: str) -> str:
    sanitized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value.lower())
    sanitized = "-".join(filter(None, sanitized.split("-")))
    return sanitized or "snippet"


def _unique_slug(base: str, existing: Dict[str, int]) -> str:
    count = existing.get(base, 0)
    if count == 0 and base not in existing:
        existing[base] = 1
        return base
    count += 1
    existing[base] = count
    return f"{base}-{count}"


def _language_path(language: str) -> Tuple[str, str]:
    mapping = {
        "php": ("php", "php"),
        "html": ("html", "html"),
        "javascript": ("js", "js"),
        "css": ("css", "css"),
    }
    return mapping.get(language, (language, language or "txt"))


def _php_repr(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_php_repr(item) for item in value) + "]"
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            parts.append(f"'{key}' => {_php_repr(item)}")
        return "[" + ", ".join(parts) + "]"
    # strings
    string = str(value)
    string = string.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{string}'"


def _write_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def _normalize_php_code(code: str) -> str:
    stripped = code.lstrip()
    if stripped.startswith("<?php"):
        stripped = stripped[5:]
        if stripped.startswith("php"):
            stripped = stripped[3:]
    return stripped.lstrip()


def _snippet_file_contents(snippet: Snippet, plan: PlannedSnippet) -> str:
    if snippet.language == "php":
        return "<?php\n" + _normalize_php_code(snippet.code).rstrip() + "\n"
    return snippet.code.rstrip() + "\n"


def _render_metadata(snippets: Iterable[PlannedSnippet], plugin_dir: Path) -> str:
    entries: List[str] = []
    for planned in snippets:
        snippet = planned.snippet
        plan = planned.plan
        entry: Dict[str, object] = {
            "id": snippet.identifier,
            "title": snippet.title,
            "status": plan.status,
            "render_mode": plan.render_mode,
            "priority": plan.priority,
            "tags": snippet.tags,
        }
        if plan.reason:
            entry["reason"] = plan.reason
        if plan.hook:
            entry["hook"] = plan.hook
        if plan.hook_type:
            entry["hook_type"] = plan.hook_type
        if plan.placement:
            entry["placement"] = plan.placement

        snippet_dir, extension = _language_path(snippet.language)
        entry["path"] = "/".join(
            [
                "snippets",
                snippet_dir,
                f"snippet-{snippet.identifier}.{extension}",
            ]
        )
        if snippet.notes:
            entry["notes"] = snippet.notes
        entries.append(_php_repr(entry))

    body = ",\n    ".join(entries)
    return "<?php\n" \
        + "$wpcode_generated_snippets = [\n    " \
        + body \
        + "\n];\n"


def _render_loader_php() -> str:
    return textwrap.dedent(
        """<?php
        if (!defined('ABSPATH')) {
            exit;
        }

        require_once __DIR__ . '/snippet-data.php';

        function wpcode_generated_normalize_handle($value)
        {
            $value = strtolower((string) $value);
            $value = preg_replace('/[^a-z0-9_-]+/', '-', $value);
            return trim($value, '-');
        }

        function wpcode_generated_get_snippet_file_path($snippet)
        {
            if (empty($snippet['path'])) {
                return '';
            }

            $base = dirname(__DIR__);
            $path = ltrim($snippet['path'], '/');

            return $base . '/' . $path;
        }

        function wpcode_generated_execute_snippet($snippet)
        {
            $file = wpcode_generated_get_snippet_file_path($snippet);
            if (empty($file) || !file_exists($file)) {
                return '';
            }

            switch ($snippet['render_mode']) {
                case 'php_include':
                    include $file;
                    return '';
                case 'style_block':
                    $handle = wpcode_generated_normalize_handle($snippet['id']);
                    $content = file_get_contents($file);

                    return '<style id="wpcode-snippet-' . esc_attr($handle) . '">' . $content . '</style>';
                case 'script_block':
                    $handle = wpcode_generated_normalize_handle($snippet['id']);
                    $content = file_get_contents($file);

                    return '<script id="wpcode-snippet-' . esc_attr($handle) . '">' . $content . '</script>';
                default:
                    return file_get_contents($file);
            }
        }

        add_action('plugins_loaded', function () use (&$wpcode_generated_snippets) {
            foreach ($wpcode_generated_snippets as $snippet) {
                if ($snippet['status'] !== 'auto') {
                    continue;
                }

                if ($snippet['hook_type'] === 'action') {
                    add_action($snippet['hook'], function () use ($snippet) {
                        $output = wpcode_generated_execute_snippet($snippet);

                        if ($snippet['render_mode'] !== 'php_include' && $output !== '') {
                            echo $output;
                        }
                    }, $snippet['priority']);
                } elseif ($snippet['hook_type'] === 'filter') {
                    add_filter($snippet['hook'], function ($content) use ($snippet) {
                        $output = wpcode_generated_execute_snippet($snippet);

                        if ($snippet['placement'] === 'before') {
                            return $output . $content;
                        }

                        return $content . $output;
                    }, $snippet['priority']);
                } elseif ($snippet['hook_type'] === 'shortcode') {
                    add_shortcode($snippet['hook'], function ($atts = [], $content = '') use ($snippet) {
                        return wpcode_generated_execute_snippet($snippet);
                    });
                }
            }
        });
        """
    )

def _render_admin_page() -> str:
    return textwrap.dedent(
        '<?php\n    if (!defined(\'ABSPATH\')) {\n        exit;\n    }\n\n    require_once __DIR__ . \'/snippet-data.php\';\n\n    function wpcode_generated_register_admin_assets()\n    {\n        wp_register_style(\n            \'wpcode-generated-admin\',\n            plugins_url(\'../assets/admin.css\', __FILE__),\n            [],\n            \'1.0.0\'\n        );\n    }\n\n    add_action(\'admin_init\', \'wpcode_generated_register_admin_assets\');\n\n    add_action(\'admin_enqueue_scripts\', function ($hook) {\n        if ($hook !== \'toplevel_page_wpcode-generated-snippets\') {\n            return;\n        }\n\n        wp_enqueue_style(\'wpcode-generated-admin\');\n    });\n\n    add_action(\'admin_menu\', function () {\n        add_menu_page(\n            \'Generated Snippets\',\n            \'Generated Snippets\',\n            \'manage_options\',\n            \'wpcode-generated-snippets\',\n            \'wpcode_generated_render_admin_page\',\n            \'dashicons-editor-code\',\n            81\n        );\n    });\n\n    function wpcode_generated_render_admin_page()\n    {\n        global $wpcode_generated_snippets;\n\n        echo \'<div class="wrap wpcode-generated">\';\n        echo \'<h1>Generated Snippets</h1>\';\n        if (empty($wpcode_generated_snippets)) {\n            echo \'<p>No snippets were imported.</p>\';\n            echo \'</div>\';\n            return;\n        }\n\n        echo \'<div class="wpcode-generated__grid">\';\n        foreach ($wpcode_generated_snippets as $snippet) {\n            $classes = \'wpcode-generated__card\';\n\n            if ($snippet[\'status\'] !== \'auto\') {\n                $classes .= \' wpcode-generated__card--manual\';\n            }\n\n            echo \'<section class="\' . esc_attr($classes) . \'">\';\n            echo \'<header>\';\n            echo \'<h2>\' . esc_html($snippet[\'title\']) . \'</h2>\';\n            if (!empty($snippet[\'tags\'])) {\n                echo \'<p class="wpcode-generated__tags">\';\n\n                foreach ($snippet[\'tags\'] as $tag) {\n                    echo \'<span class="wpcode-generated__tag">\' . esc_html($tag) . \'</span>\';\n                }\n\n                echo \'</p>\';\n            }\n\n            echo \'</header>\';\n            echo \'<dl class="wpcode-generated__meta">\';\n            echo \'<dt>Status</dt><dd>\' . esc_html($snippet[\'status\']) . \'</dd>\';\n\n            if (!empty($snippet[\'hook\'])) {\n                echo \'<dt>Hook</dt><dd>\' . esc_html($snippet[\'hook\']) . \'</dd>\';\n            }\n\n            if (!empty($snippet[\'hook_type\'])) {\n                echo \'<dt>Hook Type</dt><dd>\' . esc_html($snippet[\'hook_type\']) . \'</dd>\';\n            }\n\n            echo \'<dt>Priority</dt><dd>\' . intval($snippet[\'priority\']) . \'</dd>\';\n\n            if (!empty($snippet[\'placement\'])) {\n                echo \'<dt>Placement</dt><dd>\' . esc_html($snippet[\'placement\']) . \'</dd>\';\n            }\n\n            if (!empty($snippet[\'reason\'])) {\n                echo \'<dt>Notes</dt><dd>\' . esc_html($snippet[\'reason\']) . \'</dd>\';\n            } elseif (!empty($snippet[\'notes\'])) {\n                echo \'<dt>Notes</dt><dd>\' . esc_html($snippet[\'notes\']) . \'</dd>\';\n            }\n\n            echo \'</dl>\';\n            $file_path = wpcode_generated_get_snippet_file_path($snippet);\n\n            if ($file_path && file_exists($file_path)) {\n                $code = esc_html(file_get_contents($file_path));\n                echo \'<pre class="wpcode-generated__code"><code>\' . $code . \'</code></pre>\';\n            }\n\n            echo \'</section>\';\n        }\n\n        echo \'</div>\';\n        echo \'</div>\';\n    }\n'
    )

def _render_admin_css() -> str:
    return ".wpcode-generated__grid {\n" \
        "    display: grid;\n" \
        "    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));\n" \
        "    gap: 1.5rem;\n" \
        "}\n" \
        ".wpcode-generated__card {\n" \
        "    background: #fff;\n" \
        "    border: 1px solid #ccd0d4;\n" \
        "    border-radius: 6px;\n" \
        "    padding: 1rem;\n" \
        "    box-shadow: 0 1px 2px rgba(30, 41, 59, 0.06);\n" \
        "}\n" \
        ".wpcode-generated__card--manual {\n" \
        "    border-color: #d63638;\n" \
        "    box-shadow: 0 0 0 2px rgba(214, 54, 56, 0.15);\n" \
        "}\n" \
        ".wpcode-generated__meta {\n" \
        "    display: grid;\n" \
        "    grid-template-columns: auto 1fr;\n" \
        "    gap: 0.25rem 1rem;\n" \
        "    font-size: 0.875rem;\n" \
        "    margin-bottom: 1rem;\n" \
        "}\n" \
        ".wpcode-generated__meta dt {\n" \
        "    font-weight: 600;\n" \
        "    color: #1d2327;\n" \
        "}\n" \
        ".wpcode-generated__meta dd {\n" \
        "    margin: 0;\n" \
        "    color: #50575e;\n" \
        "}\n" \
        ".wpcode-generated__code {\n" \
        "    background: #f6f7f7;\n" \
        "    border-radius: 4px;\n" \
        "    padding: 1rem;\n" \
        "    overflow-x: auto;\n" \
        "}\n" \
        ".wpcode-generated__tag {\n" \
        "    display: inline-block;\n" \
        "    background: #f0f6ff;\n" \
        "    color: #1d4ed8;\n" \
        "    padding: 0.2rem 0.5rem;\n" \
        "    border-radius: 999px;\n" \
        "    font-size: 0.75rem;\n" \
        "    margin-right: 0.25rem;\n" \
        "}\n"


def build_plugin(
    export_path: str | Path,
    output_directory: str | Path,
    plugin_slug: str = "wpcode-generated-snippets",
    plugin_name: str = "WPCode Generated Snippets",
) -> Path:
    export_path = Path(export_path)
    output_directory = Path(output_directory)
    planned_snippets = [plan_snippet(snippet) for snippet in _load_snippets(export_path)]

    plugin_dir = output_directory / plugin_slug
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)
    plugin_dir.mkdir(parents=True)

    slug_registry: Dict[str, int] = {}
    for planned in planned_snippets:
        snippet = planned.snippet
        base_slug = _sanitize_slug(snippet.identifier)
        slug = _unique_slug(base_slug, slug_registry)
        snippet.identifier = slug

        snippet_dir_name, extension = _language_path(snippet.language)
        file_path = plugin_dir / "snippets" / snippet_dir_name / f"snippet-{slug}.{extension}"
        _write_file(file_path, _snippet_file_contents(snippet, planned))

    metadata = _render_metadata(planned_snippets, plugin_dir)
    _write_file(plugin_dir / "includes" / "snippet-data.php", metadata)
    _write_file(plugin_dir / "includes" / "loader.php", _render_loader_php())
    _write_file(plugin_dir / "includes" / "admin-page.php", _render_admin_page())
    _write_file(plugin_dir / "assets" / "admin.css", _render_admin_css())

    main_php = "<?php\n" \
        + "/**\n" \
        + f" * Plugin Name: {plugin_name}\n" \
        + " * Description: Generated from a WPCode export.\n" \
        + " * Version: 1.0.0\n" \
        + " * Author: WPCode Conversion Tool\n" \
        + " */\n\n" \
        + "if (!defined('ABSPATH')) {\n" \
        + "    exit;\n" \
        + "}\n\n" \
        + "require_once __DIR__ . '/includes/loader.php';\n" \
        + "require_once __DIR__ . '/includes/admin-page.php';\n"

    _write_file(plugin_dir / f"{plugin_slug}.php", main_php)

    return plugin_dir


def _load_snippets(path: Path) -> List[Snippet]:
    from .parser import load_snippets

    return load_snippets(path)
