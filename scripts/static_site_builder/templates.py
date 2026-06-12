from __future__ import annotations

import html
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


class StaticTemplateHTML(str):
    """Already-rendered HTML that can be inserted into generator templates."""


def static_template_html(value: Any) -> StaticTemplateHTML:
    return StaticTemplateHTML(str(value or ""))


@lru_cache(maxsize=None)
def read_static_site_template(template_name: str) -> str:
    template_path = (
        Path(__file__).resolve().parents[2]
        / "templates"
        / "static-site"
        / template_name
    )
    return template_path.read_text(encoding="utf-8")


def render_static_site_template(
    template_name: str, context: dict[str, Any] | None = None
) -> str:
    context = context or {}
    template = read_static_site_template(template_name)

    def replace_placeholder(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise SystemExit(
                f"Missing static-site template value {key!r} in {template_name}"
            )
        value = context[key]
        if isinstance(value, StaticTemplateHTML):
            return str(value)
        return html.escape(str(value or ""), quote=True)

    rendered = re.sub(
        r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}", replace_placeholder, template
    )
    ensure_no_unhandled_template_syntax(template_name, rendered)
    return rendered


def ensure_no_unhandled_template_syntax(template_name: str, rendered: str) -> None:
    marker_match = re.search(r"{%|{{", rendered)
    if marker_match:
        start = max(marker_match.start() - 40, 0)
        end = min(marker_match.end() + 80, len(rendered))
        raise SystemExit(
            f"Unhandled template syntax in {template_name}: {rendered[start:end]!r}"
        )
