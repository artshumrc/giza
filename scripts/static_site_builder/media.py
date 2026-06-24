from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlparse

from .constants import IIIF_CACHE_HOST, IIIF_CACHE_MANIFEST_URL, IIIF_CACHE_THUMB_URL
from .text import plain_text


def primary_display(source: dict[str, Any]) -> dict[str, Any]:
    value = source.get("primarydisplay")
    return value if isinstance(value, dict) else {}


def looks_like_image(url: str) -> bool:
    clean = url.split("?", 1)[0].lower()
    return (
        clean.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"))
        or "nrs.harvard.edu/urn" in clean
    )


def cache_harvard_image_url(url: str) -> str:
    value = plain_text(url)
    if not value:
        return ""
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host == IIIF_CACHE_HOST:
        return value
    if not (host == "harvard.edu" or host.endswith(".harvard.edu")):
        return value
    if not looks_like_image(value):
        return value
    return IIIF_CACHE_THUMB_URL + quote(value, safe=":/%")


def cache_manifest_url(manifest_origin_url: str) -> str:
    value = plain_text(manifest_origin_url)
    if not value:
        return ""
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if host == IIIF_CACHE_HOST:
        return value
    return IIIF_CACHE_MANIFEST_URL + quote(value, safe=":/%")
