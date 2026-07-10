"""Render production Django templates at build time.

The static runtime ships no Django, but at *build* time we reuse the real
``templates/pages/full.html`` (and the per-type ``tms/templates/tms/*.html``
detail partials it includes) so item detail pages stay faithful to the
production application without re-implementing every type-specific layout.

A standalone ``django.template.Engine`` is configured with no app registry,
no urlconf, and no staticfiles backend. A build-only override of
``layouts/default.html`` makes ``full.html`` emit just its ``main_content``
block (delimited by markers) so the generator can wrap it in the static-site
chrome and search markers. A build-only override of ``base.html`` does the same
for ``allphotos.html`` while also exposing its extra CSS and JavaScript blocks.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .media import cache_harvard_image_url
from .buildtemplatetags import set_static_base_url

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _REPO_ROOT / "templates"
_TMS_TEMPLATES_DIR = _REPO_ROOT / "tms" / "templates"
_OVERRIDES_DIR = _TEMPLATES_DIR / "static-site" / "build-overrides"

_MAIN_CONTENT_RE = re.compile(r"<!--MC_START-->(.*)<!--MC_END-->", re.DOTALL)
_CONTENT_RE = re.compile(r"<!--CONTENT_START-->(.*)<!--CONTENT_END-->", re.DOTALL)
_EXTRA_CSS_RE = re.compile(r"<!--EXTRA_CSS_START-->(.*)<!--EXTRA_CSS_END-->", re.DOTALL)
_EXTRA_JS_RE = re.compile(r"<!--EXTRA_JS_START-->(.*)<!--EXTRA_JS_END-->", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_APP_CSS_LINK_RE = re.compile(r'<link[^>]*?\bhref="[^"]*app\.css"[^>]*>', re.IGNORECASE)
_IMAGE_FIELDS = ("thumbnail", "main")


@dataclass(frozen=True)
class RenderedTemplateContent:
    body: str
    extra_head: str = ""
    extra_scripts: str = ""


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


def _collapse_blank_lines(content: str) -> str:
    """Collapse runs of blank lines to a single blank line.

    Rendering full.html leaves long runs of blank lines where ``{% %}`` tags
    and skipped loop iterations stood. A linear pass is dramatically faster
    than a backtracking regex on the large rendered pages.
    """
    out: list[str] = []
    blank = False
    for line in content.split("\n"):
        if line and not line.isspace():
            out.append(line)
            blank = False
        elif not blank:
            out.append("")
            blank = True
    return "\n".join(out)


def _post_process(content: str) -> str:
    # Strip nonfunctional comments left by the runtime template. The MC markers
    # were already consumed by extraction.
    content = _HTML_COMMENT_RE.sub("", content)
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
    content = _collapse_blank_lines(content)
    return content


def _post_process_fragment(content: str) -> str:
    content = _HTML_COMMENT_RE.sub("", content)
    content = _APP_CSS_LINK_RE.sub("", content)
    return _collapse_blank_lines(content).strip()


def _post_process_allphotos_body(content: str) -> str:
    content = _post_process_fragment(content)
    return content.replace(
        'class="page-header header-bg-1" id="content"',
        'class="page-header header-bg-1"',
        1,
    )


def _extract_block(pattern: re.Pattern[str], rendered: str) -> str:
    match = pattern.search(rendered)
    return match.group(1) if match else ""


def render_item_main_content(
    item_type: str,
    item_id: str,
    source: dict[str, Any],
    *,
    base_url: str,
    has_manifest: bool,
) -> str:
    from django.template import Context

    set_static_base_url(base_url)
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


def render_item_allphotos_content(
    item_type: str,
    item_id: str,
    source: dict[str, Any],
    *,
    base_url: str,
) -> RenderedTemplateContent:
    from django.template import Context

    set_static_base_url(base_url)
    engine = _engine()
    template = engine.get_template("pages/allphotos.html")
    context = Context(
        {
            "object": _prepare_object(source, has_manifest=False),
            "type": item_type,
            "user": SimpleNamespace(is_authenticated=False),
            "request": SimpleNamespace(user=SimpleNamespace(is_authenticated=False)),
        }
    )
    rendered = template.render(context)
    body = _extract_block(_CONTENT_RE, rendered) or rendered
    extra_head = _extract_block(_EXTRA_CSS_RE, rendered)
    extra_scripts = _extract_block(_EXTRA_JS_RE, rendered)
    return RenderedTemplateContent(
        body=_post_process_allphotos_body(body),
        extra_head=_post_process_fragment(extra_head),
        extra_scripts=_post_process_fragment(extra_scripts),
    )


def render_library_content(
    *,
    letter_groups: list[dict[str, Any]],
    publication_records: list[dict[str, Any]],
    author_count: int,
) -> str:
    from django.template import Context

    template = _engine().get_template("static-site/library.html")
    rendered = template.render(
        Context(
            {
                "letter_groups": letter_groups,
                "publication_records": publication_records,
                "author_count": author_count,
            }
        )
    )
    return _post_process_fragment(rendered)


def warm_engine() -> None:
    """Pre-compile the item templates.

    Building the engine and compiling ``pages/full.html`` (and the partials it
    includes) plus ``pages/allphotos.html`` is done once here so that, when the
    build forks a pool of render workers, each worker has the compiled templates
    ready instead of compiling them on its first item.
    """
    engine = _engine()
    engine.get_template("pages/full.html")
    engine.get_template("pages/allphotos.html")
    engine.get_template("static-site/library.html")
