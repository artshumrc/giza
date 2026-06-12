from __future__ import annotations

import html
import json
from typing import Any

from .django_templates import render_item_main_content
from .layout import page_header, render_page
from .media import cache_harvard_image_url, looks_like_image, primary_display
from .models import ItemSummary
from .text import plain_text, truncate_text
from .urls import (
    item_manifest_id,
    item_title,
    item_url,
    manifest_url,
    search_category_label,
    type_label,
)


def make_summary(
    item_type: str, item_id: str, source: dict[str, Any], manifest_ids: set[str]
) -> ItemSummary:
    primary = primary_display(source)
    manifest_id = item_manifest_id(item_type, item_id)
    has_manifest = bool(primary.get("has_manifest")) or manifest_id in manifest_ids
    thumbnail = cache_harvard_image_url(
        plain_text(primary.get("thumbnail")) or plain_text(source.get("thumbnail"))
    )
    main = plain_text(primary.get("main"))
    has_image = bool(thumbnail or (main and looks_like_image(main)))
    search_identifier = (
        plain_text(
            source.get("sitename") if item_type == "sites" else source.get("number")
        )
        or item_id
    )
    return ItemSummary(
        type=item_type,
        id=item_id,
        title=item_title(item_type, item_id, source),
        url=item_url(item_type, item_id),
        thumbnail=thumbnail,
        description=plain_text(
            source.get("description") or source.get("notes") or source.get("remarks")
        ),
        department=plain_text(source.get("department")),
        classification=plain_text(
            source.get("classificationtext") or source.get("classification")
        ),
        material=plain_text(source.get("medium")),
        period=plain_text(source.get("period")),
        site_name=plain_text(source.get("sitename")),
        search_identifier=search_identifier,
        has_image=has_image,
        has_manifest=has_manifest,
        has_pdf=bool(plain_text(source.get("pdf"))),
    )


def get_doc_id(doc: dict[str, Any]) -> str:
    return plain_text(doc.get("_id") or (doc.get("_source") or {}).get("id"))


def render_item_page(
    item_type: str,
    item_id: str,
    source: dict[str, Any],
    summary: ItemSummary,
    manifest_ids: set[str],
    lookup: dict[tuple[str, str], ItemSummary],
) -> str:
    title = summary.title
    manifest_id = item_manifest_id(item_type, item_id)
    has_manifest = summary.has_manifest
    main_content = render_item_main_content(
        item_type, item_id, source, has_manifest=has_manifest
    )
    body = "\n".join(
        [
            page_header(title, source.get("sitename"), bg="1", pagefind_body=True),
            render_pagefind_filters(summary),
            main_content,
        ]
    )
    extra_scripts = (
        render_mirador_script(manifest_url(manifest_id)) if has_manifest else ""
    )
    return render_page(
        title,
        body,
        description=truncate_text(summary.description or title, 160),
        body_class="section-explore-body header-full mode-full",
        extra_head=render_pagefind_meta(summary),
        extra_scripts=extra_scripts,
        index_body=None,
    )


def render_summary_card(summary: ItemSummary) -> str:
    thumb_url = cache_harvard_image_url(summary.thumbnail)
    thumb = (
        f'<div class="thumbnail"><a href="{summary.url}"><img src="{html.escape(thumb_url, quote=True)}" alt=""></a></div>'
        if thumb_url
        else ""
    )
    meta = []
    if summary.department:
        meta.append(summary.department)
    if summary.period:
        meta.append(summary.period)
    meta_text = " | ".join(html.escape(value) for value in meta)
    return (
        '<li><div class="media-object list-item list-item-thumbnail">'
        f'<div class="media-object-section">{thumb}</div>'
        '<div class="media-object-section">'
        f'<p class="media-object-title"><a href="{summary.url}">{html.escape(summary.title)}</a></p>'
        f'<p class="static-site-meta">{html.escape(type_label(summary.type))}{(" - " + meta_text) if meta_text else ""}</p>'
        "</div></div></li>"
    )


def render_pagefind_meta(summary: ItemSummary) -> str:
    thumbnail = cache_harvard_image_url(summary.thumbnail)
    result_image = thumbnail or "/static/images/object1.png"
    values = {
        "title": summary.title,
        "type": type_label(summary.type),
        "category": search_category_label(summary.type),
        "catalog_id": summary.search_identifier,
        "image": result_image,
        "image_alt": summary.title if result_image else "",
        "thumbnail": thumbnail,
    }
    tags = [
        f'<meta data-pagefind-meta="{html.escape(key)}[content]" content="{html.escape(value, quote=True)}">'
        for key, value in values.items()
        if value
    ]
    if summary.title:
        tags.append(
            f'<meta data-pagefind-sort="title[content]" content="{html.escape(summary.title, quote=True)}">'
        )
    return "\n".join(tags)


def render_pagefind_filters(summary: ItemSummary) -> str:
    filters = [
        ("category", search_category_label(summary.type)),
        ("search_scope", "catalog"),
    ]
    spans = [
        f'<span data-pagefind-filter="{html.escape(name)}">{html.escape(value)}</span>'
        for name, value in filters
        if value
    ]
    return (
        '<div class="static-site-pagefind-filters" aria-hidden="true">'
        + "".join(spans)
        + "</div>"
    )


def render_mirador_script(manifest_path: str) -> str:
    manifest_json = json.dumps(manifest_path)
    return f"""
<script src="/static/js/mirador.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {{
  var target = document.getElementById('mirador');
  if (!target || !window.Mirador) return;
  var manifest = target.getAttribute('data-manifest') || {manifest_json};
  window.Mirador.viewer({{
    id: 'mirador',
    windows: [{{
      imageToolsEnabled: true,
      loadedManifest: manifest,
      manifestId: manifest,
      thumbnailNavigationPosition: 'far-right'
    }}]
  }});
}});
</script>
""".strip()
