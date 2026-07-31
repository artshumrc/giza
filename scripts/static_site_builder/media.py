from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from .constants import (
    DEFAULT_MEDIA_BASE_URL,
    IIIF_CACHE_HOST,
    IIIF_CACHE_MANIFEST_URL,
    IIIF_CACHE_THUMB_URL,
    LEGACY_MEDIA_HOSTS,
    MEDIA_MOJIBAKE_REPAIRS,
    MEDIA_PATH_REPAIRS_FILE,
)
from .text import plain_text


def _load_path_repairs() -> dict[str, str]:
    """Read the recorded-path -> real-object map, if it is present.

    Loaded at import so the fork-based render pool inherits it. A missing file
    is not an error: the build still works, it just emits the dead links the
    data records.
    """
    path = Path(__file__).resolve().parents[2] / MEDIA_PATH_REPAIRS_FILE
    repairs: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return repairs
    for line in text.splitlines():
        recorded, _, actual = line.partition("\t")
        if recorded and actual:
            repairs[recorded] = actual
    return repairs


_PATH_REPAIRS = _load_path_repairs()


_MEDIA_BASE_URL = DEFAULT_MEDIA_BASE_URL.rstrip("/")
_MEDIA_HOST = (urlparse(_MEDIA_BASE_URL).hostname or "").lower()

# A legacy media URL: scheme and host (including the protocol-relative
# ``//host/...`` form) followed by the path, up to any query string.
_LEGACY_MEDIA_RE = re.compile(
    r"(?:https?:)?//(?:"
    + "|".join(re.escape(h) for h in LEGACY_MEDIA_HOSTS)
    + r")(?P<path>[^?#]*)",
    re.IGNORECASE,
)

# The paths in the ES export are raw: literal spaces, ``&``, ``+``, and NFC
# accented characters. Apache served those as-is, but an S3 origin behind
# CloudFront resolves an unencoded ``+`` to a space and 403s, so the path is
# percent-encoded on the way out. ``%`` stays safe so a value that is already
# encoded is not encoded twice.
_PATH_SAFE = "/%"


def set_media_base_url(base_url: str | None) -> None:
    """Point every media URL the build emits at ``base_url``.

    Called once from the build entry point before any rendering (and before the
    fork-based render pool starts, so workers inherit it)."""
    global _MEDIA_BASE_URL, _MEDIA_HOST
    _MEDIA_BASE_URL = (base_url or DEFAULT_MEDIA_BASE_URL).rstrip("/")
    _MEDIA_HOST = (urlparse(_MEDIA_BASE_URL).hostname or "").lower()


def media_base_url() -> str:
    return _MEDIA_BASE_URL


def path_repair_count() -> int:
    """How many recorded-path repairs are in force.

    Reported by the build: an absent repairs file is survivable but silently
    reintroduces every dead link it would have fixed, so the count belongs in
    the log rather than only in whoever remembered to commit the file.
    """
    return len(_PATH_REPAIRS)


def media_url(value: Any) -> str:
    """Rewrite any legacy media URL in ``value`` onto the configured base."""
    text = "" if value is None else str(value)
    if not text:
        return ""
    for mangled, correct in MEDIA_MOJIBAKE_REPAIRS:
        if mangled in text:
            text = text.replace(mangled, correct)

    def replace(match: re.Match[str]) -> str:
        path = match.group("path")
        actual = _PATH_REPAIRS.get(path.lstrip("/"))
        if actual:
            path = "/" + actual
        return _MEDIA_BASE_URL + quote(path, safe=_PATH_SAFE)

    return _LEGACY_MEDIA_RE.sub(replace, text)


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
    value = media_url(plain_text(url))
    if not value:
        return ""
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host == IIIF_CACHE_HOST:
        return value
    # Our own media base is already a CDN in front of the giza-media bucket, so
    # proxying it through the IIIF cache would only add a hop. The cache stays
    # in front of the image servers we do not control (ids.lib, nrs).
    if host == _MEDIA_HOST:
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
