"""Build-time Django template tags.

These shim the project's runtime URL/static tags so the production
``templates/`` and ``tms/templates/`` can be rendered by a standalone Django
template engine that has no urlconf, no app registry, and no staticfiles
backend. They emit the same static paths the generator uses elsewhere.
"""

from __future__ import annotations

from django import template

from .media import cache_manifest_url
from .urls import absolute_url, manifest_url

register = template.Library()

_STATIC_BASE_URL: str | None = None


def set_static_base_url(base_url: str | None) -> None:
    global _STATIC_BASE_URL
    _STATIC_BASE_URL = base_url.rstrip("/") if base_url else None


@register.simple_tag
def static(path: object) -> str:
    return "/static/" + str(path or "").lstrip("/")


@register.simple_tag(name="url")
def url(name: object, *args: object) -> str:
    route = str(name or "")
    if route in {"get_type_html", "get_type_html_legacy"} and len(args) >= 3:
        item_type, item_id, view = args[0], args[1], args[2]
        return f"/{item_type}/{item_id}/{view}/"
    if route in {"iiif-manifest", "get_manifest"} and args:
        local_url = manifest_url(str(args[0]))
        if _STATIC_BASE_URL:
            return cache_manifest_url(absolute_url(_STATIC_BASE_URL, local_url))
        return local_url
    return "#"
