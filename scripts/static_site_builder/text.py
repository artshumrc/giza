from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any


class SafeHTML(HTMLParser):
    """Very small sanitizer for known public content fields."""

    allowed_tags = {
        "a",
        "abbr",
        "b",
        "blockquote",
        "br",
        "cite",
        "code",
        "div",
        "em",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "img",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "sub",
        "sup",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "u",
        "ul",
    }
    allowed_attrs = {
        "a": {"href", "title"},
        "img": {"alt", "height", "src", "title", "width"},
        "td": {"colspan", "rowspan"},
        "th": {"colspan", "rowspan"},
    }
    void_tags = {"br", "hr", "img"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        from .media import cache_harvard_image_url, media_url
        from .urls import is_safe_url

        tag = tag.lower()
        if tag not in self.allowed_tags:
            return
        rendered_attrs = []
        for name, value in attrs:
            name = name.lower()
            if name not in self.allowed_attrs.get(tag, set()) or value is None:
                continue
            if name in {"href", "src"} and not is_safe_url(value):
                continue
            if name == "src":
                value = cache_harvard_image_url(value)
            elif name == "href":
                value = media_url(value)
            rendered_attrs.append(f'{name}="{html.escape(value, quote=True)}"')
        attr_text = " " + " ".join(rendered_attrs) if rendered_attrs else ""
        self.parts.append(f"<{tag}{attr_text}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.allowed_tags and tag not in self.void_tags:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data))

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def rendered(self) -> str:
        return "".join(self.parts)


def has_value(value: Any) -> bool:
    return bool(plain_text(value))


def first_text(mapping: dict[str, Any], *keys: str) -> str:
    for key in keys:
        text = plain_text(mapping.get(key))
        if text:
            return text
    return ""


def plain_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, dict):
        for key in (
            "displaytext",
            "name",
            "title",
            "sitetype",
            "altnum",
            "description",
            "value",
            "label",
        ):
            text = plain_text(value.get(key))
            if text:
                return text
        parts = [
            f"{key}: {plain_text(child)}"
            for key, child in value.items()
            if plain_text(child)
        ]
        return "; ".join(parts)
    if isinstance(value, list):
        seen = set()
        parts = []
        for child in value:
            text = plain_text(child)
            if text and text not in seen:
                parts.append(text)
                seen.add(text)
        return "; ".join(parts)
    return str(value).strip()


def escape_text(value: Any) -> str:
    return html.escape(plain_text(value))


def text_to_inline_html(value: Any) -> str:
    text = plain_text(value)
    if not text:
        return ""
    return html.escape(text).replace("\n", "<br>")


def text_to_paragraphs(value: Any) -> str:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return ""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", raw) if part.strip()]
    if not paragraphs:
        paragraphs = [raw]
    return "".join(
        f"<p>{html.escape(part).replace(chr(10), '<br>')}</p>" for part in paragraphs
    )


def sanitize_html(value: Any) -> str:
    parser = SafeHTML()
    parser.feed(str(value or ""))
    parser.close()
    return parser.rendered()


def sanitize_html_field(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if "<" not in raw and ">" not in raw:
        return text_to_paragraphs(raw)
    return sanitize_html(raw)


def truncate_text(value: str, limit: int) -> str:
    text = plain_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."
