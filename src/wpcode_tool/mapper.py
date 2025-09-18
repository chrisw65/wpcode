from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict

from .models import HookPlan, PlannedSnippet, Snippet


@dataclass(frozen=True)
class HookMapping:
    hook_type: str
    hook: str
    placement: str | None = None


LOCATION_MAP: Dict[str, HookMapping] = {
    "everywhere": HookMapping("action", "init"),
    "global": HookMapping("action", "init"),
    "frontend": HookMapping("action", "wp"),
    "frontend only": HookMapping("action", "wp"),
    "admin": HookMapping("action", "admin_init"),
    "backend": HookMapping("action", "admin_init"),
    "site-wide header": HookMapping("action", "wp_head"),
    "site wide header": HookMapping("action", "wp_head"),
    "site-wide footer": HookMapping("action", "wp_footer"),
    "site wide footer": HookMapping("action", "wp_footer"),
    "footer": HookMapping("action", "wp_footer"),
    "header": HookMapping("action", "wp_head"),
    "before content": HookMapping("filter", "the_content", placement="before"),
    "after content": HookMapping("filter", "the_content", placement="after"),
    "content": HookMapping("filter", "the_content"),
}

DEFAULT_HOOKS: Dict[str, HookMapping] = {
    "php": HookMapping("action", "init"),
    "html": HookMapping("action", "wp_footer"),
    "javascript": HookMapping("action", "wp_footer"),
    "css": HookMapping("action", "wp_head"),
}


RENDER_MODE_BY_LANGUAGE: Dict[str, str] = {
    "php": "php_include",
    "html": "html",
    "javascript": "script_block",
    "css": "style_block",
}


def _normalize_location(location: str | None) -> str | None:
    if not location:
        return None
    return re.sub(r"\s+", " ", location.strip().lower())


def _plan_known_location(snippet: Snippet, normalized_location: str) -> HookPlan | None:
    mapping = LOCATION_MAP.get(normalized_location)
    if mapping:
        return HookPlan(
            status="auto",
            render_mode=RENDER_MODE_BY_LANGUAGE.get(snippet.language, "html"),
            hook_type=mapping.hook_type,
            hook=mapping.hook,
            placement=mapping.placement,
            priority=snippet.priority,
        )
    return None


def plan_snippet(snippet: Snippet) -> PlannedSnippet:
    normalized_location = _normalize_location(snippet.location)

    render_mode = RENDER_MODE_BY_LANGUAGE.get(snippet.language, "html")

    if normalized_location:
        plan = _plan_known_location(snippet, normalized_location)
        if plan:
            return PlannedSnippet(snippet=snippet, plan=plan)
        if normalized_location in {"manual", "shortcode", "php function"}:
            return PlannedSnippet(
                snippet=snippet,
                plan=HookPlan(
                    status="manual",
                    render_mode=render_mode,
                    reason=f"Manual placement required for location '{snippet.location}'.",
                ),
            )

    default_mapping = DEFAULT_HOOKS.get(snippet.language)
    if default_mapping:
        plan = HookPlan(
            status="auto",
            render_mode=render_mode,
            hook_type=default_mapping.hook_type,
            hook=default_mapping.hook,
            priority=snippet.priority,
        )
        return PlannedSnippet(snippet=snippet, plan=plan)

    return PlannedSnippet(
        snippet=snippet,
        plan=HookPlan(
            status="manual",
            render_mode=render_mode,
            reason="Unable to determine placement for snippet.",
        ),
    )
