from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from .constants import SEARCH_CATEGORY_LABELS, TYPE_LABELS
from .text import first_text, plain_text


def item_title(item_type: str, item_id: str, source: dict[str, Any]) -> str:
    title = first_text(
        source, "displaytext", "title", "displayname", "sitename", "number"
    )
    return title or f"{type_label(item_type)} {item_id}"


def item_url(item_type: str, item_id: str) -> str:
    return f"/{item_type}/{item_id}/full/"


def item_manifest_id(item_type: str, item_id: str) -> str:
    return f"{item_type}-{item_id}"


def manifest_url(manifest_id: str) -> str:
    return f"/manifests/{manifest_id}.json"


def collection_slug(collection: dict[str, Any]) -> str:
    return slug_or_fallback(
        collection.get("slug"),
        collection.get("title"),
        f"collection-{collection.get('pk')}",
    )


def lesson_slug(lesson: dict[str, Any]) -> str:
    return slug_or_fallback(
        lesson.get("slug"), lesson.get("title"), f"lesson-{lesson.get('pk')}"
    )


def slug_or_fallback(*values: Any) -> str:
    for value in values:
        text = plain_text(value)
        if text:
            slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            if slug:
                return slug
    return "item"


def type_label(item_type: str) -> str:
    return TYPE_LABELS.get(
        item_type, item_type.replace("_", " ").replace("-", " ").title()
    )


def search_category_label(item_type: str) -> str:
    return SEARCH_CATEGORY_LABELS.get(item_type, type_label(item_type))


def absolute_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def is_safe_url(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    parsed = urlparse(value)
    if parsed.scheme:
        return parsed.scheme in {"http", "https", "mailto"}
    return value.startswith(("/", "#")) or ":" not in value
