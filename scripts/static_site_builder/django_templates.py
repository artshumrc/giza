"""Render production Django templates at build time.

The static runtime ships no Django, but at *build* time we reuse the real
``templates/pages/full.html`` (and the per-type ``tms/templates/tms/*.html``
detail partials it includes) so item detail pages stay faithful to the
production application without re-implementing every type-specific layout.

A standalone ``django.template.Engine`` is configured with no app registry,
no urlconf, and no staticfiles backend. A build-only override of
``layouts/default.html`` makes ``full.html`` emit just its ``main_content``
block (delimited by markers) so the generator can wrap it in the static-site
chrome, search markers, and Mirador bootstrap.
"""

from __future__ import annotations

import copy
import re
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .media import cache_harvard_image_url

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _REPO_ROOT / "templates"
_TMS_TEMPLATES_DIR = _REPO_ROOT / "tms" / "templates"
_OVERRIDES_DIR = _TEMPLATES_DIR / "static-site" / "build-overrides"

_MAIN_CONTENT_RE = re.compile(r"<!--MC_START-->(.*)<!--MC_END-->", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_APP_CSS_LINK_RE = re.compile(r'<link[^>]*?\bhref="[^"]*app\.css"[^>]*>', re.IGNORECASE)
_PHOTOS_JUMP_LINK_RE = re.compile(
    r'<li>\s*<a href="#photos">.*?</a>\s*</li>', re.DOTALL
)
_BLANK_LINES_RE = re.compile(r"(?:[ \t]*\n){3,}")
_IMAGE_FIELDS = ("thumbnail", "main")


def _configure_settings() -> None:
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=False,
            USE_I18N=False,
            USE_TZ=True,
            STATIC_URL="/static/",
            INSTALLED_APPS=[],
            DATABASES={},
            DEFAULT_CHARSET="utf-8",
            TEMPLATES=[],
        )


@lru_cache(maxsize=1)
def _engine():
    _configure_settings()
    from django.template import Engine

    return Engine(
        dirs=[
            str(_OVERRIDES_DIR),
            str(_TEMPLATES_DIR),
            str(_TMS_TEMPLATES_DIR),
        ],
        app_dirs=False,
        libraries={"static": "static_site_builder.buildtemplatetags"},
        builtins=[
            "django.template.defaulttags",
            "django.template.defaultfilters",
            "django.template.loader_tags",
            "static_site_builder.buildtemplatetags",
        ],
        loaders=[
            (
                "django.template.loaders.cached.Loader",
                ["django.template.loaders.filesystem.Loader"],
            )
        ],
    )


def _rewrite_images(value: Any) -> None:
    """Route Harvard image URLs through the IIIF cache, in place."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _IMAGE_FIELDS and isinstance(child, str) and child:
                value[key] = cache_harvard_image_url(child)
            else:
                _rewrite_images(child)
    elif isinstance(value, list):
        for child in value:
            _rewrite_images(child)


def _prepare_object(source: dict[str, Any], has_manifest: bool) -> dict[str, Any]:
    obj = copy.deepcopy(source)
    primary = obj.get("primarydisplay")
    if not isinstance(primary, dict):
        primary = {}
    primary["has_manifest"] = bool(has_manifest)
    obj["primarydisplay"] = primary
    _rewrite_images(obj)
    return obj


def _post_process(content: str) -> str:
    # full.html keeps the Photos section and per-photo gallery modals as HTML
    # comments whose template loops still execute (emitting hundreds of
    # commented-out nodes). Stripping HTML comments hides Photos entirely and
    # removes that bloat. The MC markers were already consumed by extraction.
    content = _HTML_COMMENT_RE.sub("", content)
    # The dangling small-screen jump-menu link to the (now absent) Photos
    # section.
    content = _PHOTOS_JUMP_LINK_RE.sub("", content)
    # The static layout already loads app.css; drop the stray in-body link.
    content = _APP_CSS_LINK_RE.sub("", content)
    # Mark the overview as the Pagefind/Dredge body so search indexes the
    # description (the rest of the page is excluded automatically once any
    # data-pagefind-body element exists).
    content = content.replace(
        'class="item__overview text-alt"',
        'class="item__overview text-alt" data-pagefind-body',
        1,
    )
    content = content.replace(
        'class="item__overview"',
        'class="item__overview" data-pagefind-body',
        1,
    )
    # Collapse the long runs of blank lines left by stripped comments and the
    # many empty template-loop iterations (e.g. the jump menu).
    content = _BLANK_LINES_RE.sub("\n\n", content)
    return content


def render_item_main_content(
    item_type: str,
    item_id: str,
    source: dict[str, Any],
    *,
    has_manifest: bool,
) -> str:
    from django.template import Context

    engine = _engine()
    template = engine.get_template("pages/full.html")
    context = Context(
        {
            "object": _prepare_object(source, has_manifest),
            "type": item_type,
            "user": SimpleNamespace(is_authenticated=False),
            "request": SimpleNamespace(user=SimpleNamespace(is_authenticated=False)),
        }
    )
    rendered = template.render(context)
    match = _MAIN_CONTENT_RE.search(rendered)
    content = match.group(1) if match else rendered
    return _post_process(content).strip()
