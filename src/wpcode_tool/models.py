from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Snippet:
    """Normalized representation of a WPCode snippet."""

    identifier: str
    title: str
    code: str
    language: str
    active: bool
    location: Optional[str]
    priority: int
    tags: List[str]
    notes: Optional[str] = None


@dataclass
class HookPlan:
    """Information about how a snippet should be executed inside a plugin."""

    status: str  # "auto" or "manual"
    render_mode: str  # php_include, html, style_block, script_block
    hook_type: Optional[str] = None  # action, filter, shortcode
    hook: Optional[str] = None
    priority: int = 10
    placement: Optional[str] = None  # before/after for filters
    reason: Optional[str] = None


@dataclass
class PlannedSnippet:
    snippet: Snippet
    plan: HookPlan

    def is_manual(self) -> bool:
        return self.plan.status != "auto"
