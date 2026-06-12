"""Build-time Django template tags.

These shim the project's runtime URL/static tags so the production
``templates/`` and ``tms/templates/`` can be rendered by a standalone Django
template engine that has no urlconf, no app registry, and no staticfiles
backend. They emit the same static paths the generator uses elsewhere.
"""

from __future__ import annotations

from django import template

register = template.Library()


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
        return f"/manifests/{args[0]}.json"
    return "#"
