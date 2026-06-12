from __future__ import annotations

import html
import json
from typing import Any

from .constants import (
    DETAIL_FIELDS,
    RELATED_ORDER,
    RELATED_SECTION_ICONS,
    RELATED_SECTION_LABELS,
    RELATED_TYPE_ALIASES,
    TYPE_LABELS,
)
from .layout import feature_block, page_header, render_page
from .media import cache_harvard_image_url, looks_like_image, primary_display
from .models import ItemSummary
from .text import (
    escape_text,
    first_text,
    has_value,
    plain_text,
    sanitize_html_field,
    text_to_inline_html,
    text_to_paragraphs,
    truncate_text,
)
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
    media_html = render_primary_media(item_type, item_id, source, has_manifest)
    description_html = render_description(source, pagefind_body=True)
    details_html = render_details(source)
    related_html = render_related_items(source.get("relateditems"), lookup)
    filters_html = render_pagefind_filters(summary)
    extra_head = render_pagefind_meta(summary)
    extra_scripts = ""
    if has_manifest:
        extra_scripts = render_mirador_script(manifest_url(manifest_id))

    body = [page_header(title, source.get("sitename"), bg="1", pagefind_body=True)]
    body.append(filters_html)
    body.append('<div class="row content-start">')
    body.append('<section class="large-8 columns content-col-primary">')
    if media_html:
        body.append(media_html)
    if description_html:
        body.append(description_html)
    body.append(feature_block("Details", details_html, icon="info-circle"))
    if related_html:
        body.append(related_html)
    bibliography_html = render_bibliography(source)
    if bibliography_html:
        body.append(bibliography_html)
    body.append("</section>")
    body.append('<aside class="large-4 columns content-col-secondary">')
    body.append(
        '<div class="feature-block secondary"><h5>Catalog Record</h5><dl class="dl-slim">'
    )
    body.append(f"<dt>Type</dt><dd>{html.escape(type_label(item_type))}</dd>")
    body.append(f"<dt>ID</dt><dd>{html.escape(item_id)}</dd>")
    if source.get("number"):
        body.append(f"<dt>Number</dt><dd>{escape_text(source.get('number'))}</dd>")
    if has_manifest:
        body.append(
            f'<dt>IIIF</dt><dd><a href="{manifest_url(manifest_id)}">Manifest JSON</a></dd>'
        )
    if summary.has_pdf and source.get("pdf"):
        body.append(
            f'<dt>PDF</dt><dd><a href="{html.escape(plain_text(source.get("pdf")), quote=True)}">Download PDF</a></dd>'
        )
    body.append('</dl><p><a href="/search/">Search the catalog</a></p></div>')
    body.append("</aside></div>")

    return render_page(
        title,
        "\n".join(body),
        description=truncate_text(summary.description or title, 160),
        body_class="section-explore-body header-full mode-full",
        extra_head=extra_head,
        extra_scripts=extra_scripts,
        index_body=None,
    )


def render_primary_media(
    item_type: str, item_id: str, source: dict[str, Any], has_manifest: bool
) -> str:
    primary = primary_display(source)
    main = plain_text(primary.get("main"))
    thumb = cache_harvard_image_url(plain_text(primary.get("thumbnail")))
    caption = plain_text(primary.get("displaytext"))
    pdf = plain_text(source.get("pdf"))
    manifest_id = item_manifest_id(item_type, item_id)
    parts = ['<div class="item__featured-image">']

    if item_type == "3dmodels" and main:
        parts.append(
            f'<iframe allowfullscreen height="500" width="100%" src="{html.escape(main, quote=True)}"></iframe>'
        )
    elif item_type == "videos" and main:
        poster = f' poster="{html.escape(thumb, quote=True)}"' if thumb else ""
        parts.append(
            f'<video width="100%" controls{poster}><source src="{html.escape(main, quote=True)}">Your browser does not support the video tag.</video>'
        )
        parts.append(
            f'<p><a href="{html.escape(main, quote=True)}">Open video source</a></p>'
        )
    elif item_type == "pubdocs" and pdf:
        if main:
            parts.append(
                f'<a href="{html.escape(pdf, quote=True)}"><img src="{html.escape(cache_harvard_image_url(main), quote=True)}" alt=""></a>'
            )
        parts.append(
            f'<p><a class="button" href="{html.escape(pdf, quote=True)}">Download PDF</a></p>'
        )
    elif has_manifest:
        parts.append(
            f'<div style="height:500px;width:100%;"><div id="mirador" data-manifest="{html.escape(manifest_url(manifest_id), quote=True)}"></div></div>'
        )
        parts.append(
            f'<p><a href="{manifest_url(manifest_id)}">Open IIIF manifest</a></p>'
        )
    elif main:
        if looks_like_image(main):
            parts.append(
                f'<img src="{html.escape(cache_harvard_image_url(main), quote=True)}" alt="">'
            )
        else:
            label = "Open media"
            parts.append(
                f'<p><a class="button" href="{html.escape(main, quote=True)}">{label}</a></p>'
            )
    elif pdf:
        parts.append(
            f'<p><a class="button" href="{html.escape(pdf, quote=True)}">Download PDF</a></p>'
        )
    elif thumb:
        parts.append(f'<img src="{html.escape(thumb, quote=True)}" alt="">')
    else:
        return ""

    if caption:
        parts.append(
            f'<p class="item__featured-image__caption">{html.escape(caption)}</p>'
        )
    parts.append("</div>")
    return "\n".join(parts)


def render_description(source: dict[str, Any], *, pagefind_body: bool = False) -> str:
    diary = source.get("diarytranscription")
    if has_value(diary):
        return f'<div class="item__overview text-alt"><h5>Diary Transcription:</h5>{text_to_paragraphs(diary)}</div>'
    description = source.get("description")
    if has_value(description):
        pagefind_attr = " data-pagefind-body" if pagefind_body else ""
        return f'<div class="item__overview"{pagefind_attr}><div class="lead text-alt">{text_to_paragraphs(description)}</div></div>'
    return ""


def render_details(source: dict[str, Any]) -> str:
    rows = []
    for label, key, mode in DETAIL_FIELDS:
        if not has_value(source.get(key)):
            continue
        if mode == "altnames":
            altname_dds = render_altname_values(source.get(key))
            if altname_dds:
                rows.append(f"<dt>{html.escape(label)}</dt>{altname_dds}")
            continue
        if mode == "safe_html":
            value = sanitize_html_field(source.get(key))
        else:
            value = text_to_inline_html(source.get(key))
        if value:
            rows.append(f"<dt>{html.escape(label)}</dt><dd>{value}</dd>")
    if not rows:
        return "<p>No additional details available.</p>"
    return (
        '<div class="feature-block__body"><dl class="dl-slim">'
        + "\n".join(rows)
        + "</dl></div>"
    )


def render_altname_values(value: Any) -> str:
    if not isinstance(value, list):
        text = plain_text(value)
        return f"<dd>{html.escape(text)}</dd>" if text else ""
    dds = []
    for entry in value:
        if isinstance(entry, dict):
            name = plain_text(entry.get("name"))
            name_type = plain_text(entry.get("type"))
            if name and name_type:
                dds.append(f"<dd>{html.escape(name_type)} : {html.escape(name)}</dd>")
            elif name:
                dds.append(f"<dd>{html.escape(name)}</dd>")
        else:
            text = plain_text(entry)
            if text:
                dds.append(f"<dd>{html.escape(text)}</dd>")
    return "".join(dds)


def render_bibliography(source: dict[str, Any]) -> str:
    if not has_value(source.get("bibreferences")):
        return ""
    body = (
        '<div class="feature-block__body"><ul class="feature-block__list">'
        '<li><div class="media-object list-item list-item-textblob">'
        f"{text_to_paragraphs(source.get('bibreferences'))}"
        "</div></li></ul></div>"
    )
    return feature_block("Full Bibliography", body, icon="bookmark")


def render_related_items(
    related: Any, lookup: dict[tuple[str, str], ItemSummary]
) -> str:
    if not isinstance(related, dict):
        return ""
    sections = []
    keys = sorted(
        (plain_text(key) for key in related.keys()),
        key=lambda key: RELATED_ORDER.index(key)
        if key in RELATED_ORDER
        else len(RELATED_ORDER),
    )
    for key in keys:
        items = related.get(key)
        if not isinstance(items, list) or not items:
            continue
        related_type = RELATED_TYPE_ALIASES.get(key, key)
        if related_type == "photos":
            # Photos are surfaced through the Mirador viewer, not a separate
            # related section. Some photos are not IIIF-compliant; hide the
            # section entirely for this static deployment.
            continue
        label = RELATED_SECTION_LABELS.get(
            related_type, RELATED_SECTION_LABELS.get(key, type_label(key))
        )
        cards = []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = plain_text(item.get("id"))
            summary = lookup.get((related_type, item_id)) if item_id else None
            if summary:
                cards.append(render_summary_card(summary))
            else:
                cards.append(render_related_card(item, related_type))
        if not cards:
            continue
        body = (
            '<div class="feature-block__body" data-pagefind-ignore><ul class="feature-block__list multicol-2 thumbsize-sm thumbs-square static-site-related">'
            + "\n".join(cards)
            + "</ul></div>"
        )
        sections.append(
            feature_block(
                f'{label} <span class="badge">{len(cards):,}</span>',
                body,
                icon=RELATED_SECTION_ICONS.get(related_type, "list"),
            )
        )
    return "\n".join(sections)


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


def render_related_card(item: dict[str, Any], item_type: str) -> str:
    item_id = plain_text(item.get("id"))
    title = (
        first_text(item, "displaytext", "title", "displayname", "name", "number")
        or f"{type_label(item_type)} {item_id}"
    )
    thumb = cache_harvard_image_url(plain_text(item.get("thumbnail")))
    url = item_url(item_type, item_id) if item_type in TYPE_LABELS and item_id else ""
    linked_title = (
        f'<a href="{url}">{html.escape(title)}</a>' if url else html.escape(title)
    )
    thumb_html = (
        f'<div class="thumbnail"><a href="{url}"><img src="{html.escape(thumb, quote=True)}" alt=""></a></div>'
        if thumb and url
        else ""
    )
    meta = first_text(item, "sitename", "number", "displaydate", "role")
    return (
        '<li><div class="media-object list-item list-item-thumbnail">'
        f'<div class="media-object-section">{thumb_html}</div>'
        f'<div class="media-object-section"><p class="media-object-title">{linked_title}</p><p class="static-site-meta">{html.escape(meta)}</p></div>'
        "</div></li>"
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
