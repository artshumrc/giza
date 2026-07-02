#!/usr/bin/env python3
"""Build the temporary static Digital Giza site from exported data.

This intentionally does not import Django, Elasticsearch, or project settings.
It reads the compressed production exports directly and emits static HTML/JSON.
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import shutil
import sys
import tarfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from static_site_builder.constants import (
    EXPECTED_ITEM_COUNT,
    EXPECTED_MANIFEST_COUNT,
    STATIC_TEMPLATE_PAGES,
)
from static_site_builder.django_templates import (
    render_item_allphotos_content,
    warm_engine,
)
from static_site_builder.items import (
    get_doc_id,
    make_summary,
    render_item_page,
    render_summary_card,
)
from static_site_builder.layout import page_header, render_page
from static_site_builder.media import cache_harvard_image_url, primary_display
from static_site_builder.models import ItemSummary
from static_site_builder.templates import render_static_site_template
from static_site_builder.text import (
    escape_text,
    plain_text,
    sanitize_html,
    sanitize_html_field,
    text_to_paragraphs,
    truncate_text,
)
from static_site_builder.urls import (
    absolute_url,
    collection_slug,
    is_safe_url,
    item_manifest_id,
    lesson_slug,
    manifest_url,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the static Digital Giza site.")
    parser.add_argument("--es-archive", required=True, type=Path)
    parser.add_argument("--django-content-dump", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--item-limit",
        type=int,
        default=0,
        help="Optional total item page limit for prototype builds.",
    )
    parser.add_argument(
        "--item-limit-per-type",
        type=int,
        default=0,
        help="Optional per-type item page limit for representative prototype builds.",
    )
    parser.add_argument(
        "--manifest-limit",
        type=int,
        default=0,
        help="Optional manifest limit for prototype builds.",
    )
    parser.add_argument(
        "--generate-item-redirects",
        action="store_true",
        help="Generate intro redirect pages for emitted item pages.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        help="Number of parallel render worker processes (1 disables the pool).",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    base_url = args.base_url.rstrip("/")

    validate_inputs(args.es_archive, args.django_content_dump, repo_root)
    prepare_output(args.output)
    copy_static_assets(repo_root, args.output)
    write_static_helpers(args.output)

    giza_member, iiif_member = discover_es_members(args.es_archive)
    print(f"Using ES members: {giza_member}, {iiif_member}")

    manifest_ids = collect_manifest_ids(args.es_archive, iiif_member)
    print(f"Indexed {len(manifest_ids):,} manifest IDs")

    indexes = build_giza_indexes(args.es_archive, giza_member, manifest_ids)
    content = load_content_dump(args.django_content_dump)

    write_core_static_pages(args.output, repo_root)
    write_search_pages(args.output)
    write_library_page(args.output, indexes["library_sources"], indexes["pubdocs"])
    write_videos_page(args.output, indexes["videos"])
    write_lessons(args.output, content, indexes["lookup"])
    write_collections(args.output, content, indexes["lookup"])
    item_counts, required_manifest_ids, _ = write_item_pages(
        args.output,
        args.es_archive,
        giza_member,
        manifest_ids,
        indexes["lookup"],
        args.item_limit,
        args.item_limit_per_type,
        args.generate_item_redirects,
        base_url,
        args.jobs,
    )
    manifest_count = write_manifests(
        args.output,
        args.es_archive,
        iiif_member,
        base_url,
        args.manifest_limit,
        required_manifest_ids,
        args.jobs,
    )
    write_404(args.output)

    emitted_item_total = sum(item_counts.values())
    print("Generated item pages:")
    for item_type, count in sorted(item_counts.items()):
        print(f"  {item_type}: {count:,}")
    print(f"Generated {emitted_item_total:,} total item pages")
    print(f"Generated {manifest_count:,} manifests")

    if (
        not args.item_limit
        and not args.item_limit_per_type
        and emitted_item_total != EXPECTED_ITEM_COUNT
    ):
        print(
            f"WARNING: expected {EXPECTED_ITEM_COUNT:,} item pages, generated {emitted_item_total:,}",
            file=sys.stderr,
        )
    if not args.manifest_limit and manifest_count != EXPECTED_MANIFEST_COUNT:
        print(
            f"WARNING: expected {EXPECTED_MANIFEST_COUNT:,} manifests, generated {manifest_count:,}",
            file=sys.stderr,
        )
    print(
        "Run `uv run poe static-dredge` after this build to install the Dredge "
        "search library and compile the search index."
    )
    return 0


def validate_inputs(es_archive: Path, content_dump: Path, repo_root: Path) -> None:
    missing = [
        path
        for path in [es_archive, content_dump, repo_root / "static"]
        if not path.exists()
    ]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise SystemExit(f"Missing required input: {missing_text}")


def prepare_output(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)


def copy_static_assets(repo_root: Path, output: Path) -> None:
    source = repo_root / "static"
    target = output / "static"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def write_static_helpers(output: Path) -> None:
    helper_dir = output / "static" / "static-site"
    missing = [
        path
        for path in [helper_dir / "static-site.css", helper_dir / "static-site.js"]
        if not path.exists()
    ]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise SystemExit(f"Missing copied static-site helper asset: {missing_text}")


def discover_es_members(es_archive: Path) -> tuple[str, str]:
    with tarfile.open(es_archive, "r:gz") as archive:
        names = archive.getnames()
    giza_member = next(
        (name for name in names if name.endswith("/giza.ndjson.gz")), None
    )
    iiif_member = next(
        (name for name in names if name.endswith("/iiif.ndjson.gz")), None
    )
    if not giza_member or not iiif_member:
        raise SystemExit("ES archive must contain giza.ndjson.gz and iiif.ndjson.gz")
    return giza_member, iiif_member


def iter_es_docs(es_archive: Path, member_name: str) -> Iterable[dict[str, Any]]:
    with tarfile.open(es_archive, "r:gz") as archive:
        member = archive.extractfile(member_name)
        if member is None:
            raise SystemExit(f"Archive member not found: {member_name}")
        with gzip.GzipFile(fileobj=member) as gz:
            for line_number, line in enumerate(gz, start=1):
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SystemExit(
                        f"Invalid JSON in {member_name} line {line_number}: {exc}"
                    ) from exc


def collect_manifest_ids(es_archive: Path, iiif_member: str) -> set[str]:
    ids: set[str] = set()
    for doc in iter_es_docs(es_archive, iiif_member):
        manifest_id = str(
            doc.get("_id") or (doc.get("_source") or {}).get("id") or ""
        ).strip()
        if manifest_id:
            ids.add(manifest_id)
    return ids


def build_giza_indexes(
    es_archive: Path,
    giza_member: str,
    manifest_ids: set[str],
) -> dict[str, Any]:
    lookup: dict[tuple[str, str], ItemSummary] = {}
    library_sources: list[dict[str, Any]] = []
    pubdocs: list[tuple[ItemSummary, dict[str, Any]]] = []
    videos: list[tuple[ItemSummary, dict[str, Any]]] = []
    counts: Counter[str] = Counter()

    for doc in iter_es_docs(es_archive, giza_member):
        item_type = str(doc.get("_type") or "")
        source = doc.get("_source") or {}
        counts[item_type] += 1
        if item_type == "library":
            library_sources.append(source)
            continue

        item_id = get_doc_id(doc)
        if not item_id:
            continue
        summary = make_summary(item_type, item_id, source, manifest_ids)
        lookup[(item_type, item_id)] = summary
        if item_type == "pubdocs":
            pubdocs.append((summary, source))
        elif item_type == "videos":
            videos.append((summary, source))

    print("Indexed giza documents:")
    for item_type, count in sorted(counts.items()):
        print(f"  {item_type}: {count:,}")
    return {
        "lookup": lookup,
        "library_sources": library_sources,
        "pubdocs": pubdocs,
        "videos": videos,
    }


def load_content_dump(content_dump: Path) -> dict[str, Any]:
    with gzip.open(content_dump, "rt", encoding="utf-8") as handle:
        data = json.load(handle)

    topics: dict[int, dict[str, Any]] = {}
    lessons: list[dict[str, Any]] = []
    public_collections: dict[int, dict[str, Any]] = {}
    collection_items: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)

    for obj in data:
        model = obj.get("model")
        pk = obj.get("pk")
        fields = obj.get("fields") or {}
        if model == "giza.topic" and isinstance(pk, int):
            topics[pk] = {"pk": pk, **fields}
        elif model == "giza.lesson":
            lessons.append({"pk": pk, **fields})
        elif model == "giza.collection" and isinstance(pk, int):
            if fields.get("public") is True:
                public_collections[pk] = {"pk": pk, **fields}

    for obj in data:
        if obj.get("model") != "giza.elasticsearchitem":
            continue
        fields = obj.get("fields") or {}
        collection_pk = fields.get("collection")
        if collection_pk in public_collections:
            collection_items[collection_pk].append(fields)

    lessons.sort(
        key=lambda lesson: (
            plain_text(lesson.get("title")).lower(),
            lesson.get("pk") or 0,
        )
    )
    print(
        f"Loaded {len(lessons):,} lessons and {len(public_collections):,} public collections"
    )
    return {
        "topics": topics,
        "lessons": lessons,
        "public_collections": public_collections,
        "collection_items": collection_items,
    }


def write_core_static_pages(output: Path, repo_root: Path) -> None:
    pages = {
        "": (
            "Home",
            home_body(),
            "The Digital Giza public catalog, library, lessons, videos, and IIIF viewers.",
        ),
    }

    for page in STATIC_TEMPLATE_PAGES:
        pages[page.slug] = (
            page.title,
            render_static_template_page(repo_root, page.template),
            page.description,
        )

    for slug, (title, body, description) in pages.items():
        path = output / slug / "index.html" if slug else output / "index.html"
        write_text(path, render_page(title, body, description=description))

    write_redirect_page(output / "gizaschool" / "index.html", "/gizaatschool/")


def home_body() -> str:
    return render_static_site_template("home.html").strip()


def content_page_body(title: str, lead: str, paragraphs: list[str]) -> str:
    body = [page_header(title, bg="6")]
    body.append('<div class="row"><section class="large-8 columns">')
    body.append(f'<p class="lead text-alt">{sanitize_html(lead)}</p>')
    for paragraph in paragraphs:
        body.append(f"<p>{sanitize_html(paragraph)}</p>")
    body.append(
        '</section><aside class="large-4 columns"><div class="feature-block secondary"><h5>Explore</h5><ul class="menu vertical"><li><a href="/search/">Search</a></li><li><a href="/library/">Library</a></li><li><a href="/videos/">Videos</a></li><li><a href="/lessons/">Lessons</a></li></ul></div></aside></div>'
    )
    return "\n".join(body)


def render_static_template_page(repo_root: Path, template_name: str) -> str:
    if template_name == "giza3d.html":
        return render_giza3d_static_page(repo_root)

    template_path = repo_root / "templates" / "pages" / template_name
    source = template_path.read_text(encoding="utf-8")
    context = parse_template_context(source)
    blocks = extract_template_blocks(source)

    body_parts = []
    page_headers = blocks.get("page_headers")
    if page_headers:
        body_parts.append(
            render_static_template_fragment(repo_root, page_headers, context)
        )

    content = blocks.get("main_content") or blocks.get("content")
    if content:
        body_parts.append(render_static_template_fragment(repo_root, content, context))

    rendered = "\n".join(part.strip() for part in body_parts if part.strip()).strip()
    rendered = normalize_static_template_links(rendered)
    ensure_no_unhandled_template_syntax(template_name, rendered)
    return rendered


def parse_template_context(source: str) -> dict[str, str]:
    context: dict[str, str] = {}
    set_match = re.search(r"{%\s*set\s*(.*?)%}", source, re.DOTALL)
    if not set_match:
        return context
    for key, value in re.findall(r"(\w+)\s*:\s*\"([^\"]*)\"", set_match.group(1)):
        context[key] = value
    return context


def extract_template_blocks(source: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    pattern = re.compile(
        r"{%\s*block\s+'?([\w_]+)'?\s*%}(.*?){%\s*endblock\s*%}", re.DOTALL
    )
    for match in pattern.finditer(source):
        blocks[match.group(1)] = match.group(2)
    return blocks


def render_static_template_fragment(
    repo_root: Path, source: str, context: dict[str, str] | None = None
) -> str:
    context = context or {}
    rendered = source
    rendered = re.sub(r"{%\s*(?:extends|load)\b.*?%}", "", rendered, flags=re.DOTALL)

    include_pattern = re.compile(
        r"{%\s*include\s+'([^']+)'\s*(?:with\s+(.*?))?\s*%}", re.DOTALL
    )
    while True:
        rendered, count = include_pattern.subn(
            lambda match: render_static_include(
                repo_root,
                match.group(1),
                parse_template_kwargs(match.group(2)),
                context,
            ),
            rendered,
        )
        if count == 0:
            break

    rendered = re.sub(
        r"{%\s*static\s+['\"]([^'\"]+)['\"]\s*%}", r"/static/\1", rendered
    )
    rendered = re.sub(r"{%\s*url\s+(.+?)\s*%}", render_static_url_tag, rendered)
    return rendered


def parse_template_kwargs(source: str | None) -> dict[str, Any]:
    if not source:
        return {}
    kwargs: dict[str, Any] = {}
    pattern = re.compile(
        r"([\w-]+)\s*=\s*(\"[^\"]*\"|'[^']*'|True|False|true|false|[^\s]+)"
    )
    for key, raw_value in pattern.findall(source):
        value: Any = raw_value
        if (raw_value.startswith('"') and raw_value.endswith('"')) or (
            raw_value.startswith("'") and raw_value.endswith("'")
        ):
            value = raw_value[1:-1]
        elif raw_value in {"True", "true"}:
            value = True
        elif raw_value in {"False", "false"}:
            value = False
        kwargs[key] = value
    return kwargs


def render_static_include(
    repo_root: Path, include_name: str, kwargs: dict[str, Any], context: dict[str, str]
) -> str:
    if include_name == "partials/page-header.html":
        return page_header(
            kwargs.get("title") or context.get("title") or "",
            bg=str(kwargs.get("bg") or "1"),
        )
    if include_name == "partials/page-subheader.html":
        return render_page_subheader(
            backlink_url=plain_text(kwargs.get("backlink_url")),
            backlink_text=plain_text(kwargs.get("backlink_text") or "Back"),
            content=f'<h2 class="text-medium">{html.escape(context.get("subtitle") or "")}</h2>',
        )
    if include_name == "partials/page-subheader--gizaatschool.html":
        content = extract_template_blocks(
            (repo_root / "templates" / include_name).read_text(encoding="utf-8")
        ).get("subheader_content", "")
        return render_page_subheader(
            content=render_static_template_fragment(repo_root, content, context)
        )
    if include_name.startswith("partials/school-hilite-item--"):
        return render_school_hilite(repo_root, include_name, kwargs, context)
    if include_name == "partials/feature-block-start.html":
        return render_feature_block_start(kwargs)
    if include_name == "partials/feature-block-end.html":
        return "</div></section>"
    if include_name == "partials/list-item-resourcelink-start.html":
        return render_resource_link_start(kwargs)
    if include_name == "partials/list-item-resourcelink-end.html":
        return "</p>\n</div>"
    if include_name == "partials/3d-tours-list.html":
        return render_static_template_fragment(
            repo_root,
            (repo_root / "templates" / include_name).read_text(encoding="utf-8"),
            context,
        )
    raise SystemExit(f"Unhandled static template include: {include_name}")


def render_page_subheader(
    *, content: str, backlink_url: str = "", backlink_text: str = "Back"
) -> str:
    backlink = ""
    if backlink_url:
        backlink = (
            '<div class="text-smaller m-x-negqt m-t-neg1 p-y-half">'
            f'<a class="pointer-back" href="{html.escape(backlink_url, quote=True)}">{html.escape(backlink_text)}</a>'
            "</div>"
        )
    return f"""
<div class="page-subheader ">
  <div class="row p-t-1">
    <div class="large-12 columns">
      {backlink}
      <div class="text-heading">
        {content.strip()}
      </div>
    </div>
  </div>
</div>
""".strip()


def render_school_hilite(
    repo_root: Path,
    include_name: str,
    kwargs: dict[str, Any],
    context: dict[str, str],
) -> str:
    source = (repo_root / "templates" / include_name).read_text(encoding="utf-8")
    content = extract_template_blocks(source).get("hilite_content", "")
    content = render_static_template_fragment(repo_root, content, context)
    primary = bool(kwargs.get("primary"))
    link = plain_text(kwargs.get("hilite_link"))
    title = html.escape(plain_text(kwargs.get("hilite_title")))
    image_class = html.escape(plain_text(kwargs.get("hilite_img")), quote=True)
    title_html = (
        f'<a class="heading-link" href="{html.escape(link, quote=True)}">{title}</a>'
        if link
        else title
    )
    footer = ""
    if link:
        button_class = "button" if primary else "button secondary"
        footer = (
            '<div class="content-hilite-footer">'
            f'<a class="{button_class}" href="{html.escape(link, quote=True)}">'
            f'{html.escape(plain_text(kwargs.get("hilite_link_text")))} <i class="icon-angle-right"></i>'
            "</a></div>"
        )
    primary_class = " content-hilite-primary" if primary else ""
    return f"""
<div class="content-hilite{primary_class}">
  <div class="content-hilite-content">
    <div class="content-hilite-header"><h2 class="text-bold">{title_html}</h2></div>
    <div class="content-hilite-body">{content.strip()}</div>
    {footer}
  </div>
  <div class="content-hilite-image img-{image_class}"></div>
</div>
""".strip()


def render_feature_block_start(kwargs: dict[str, Any]) -> str:
    anchor = html.escape(plain_text(kwargs.get("feature_anchor")), quote=True)
    block_class = html.escape(plain_text(kwargs.get("feature_block_class")), quote=True)
    title = plain_text(kwargs.get("feature_title"))
    heading_class = html.escape(plain_text(kwargs.get("heading_class")), quote=True)
    header = ""
    if title:
        icon = html.escape(plain_text(kwargs.get("feature_icon")), quote=True)
        counter = plain_text(kwargs.get("feature_counter"))
        counter_html = (
            f'<span class="badge">{html.escape(counter)}</span>' if counter else ""
        )
        header = f"""
  <div class="feature-block__header">
    <h3 class="feature-block__title {heading_class}">
      <i class="icon-{icon} icon-padded"></i> {html.escape(title)}
      <a name="{anchor}"></a>
      {counter_html}
    </h3>
    <button class="toggler" data-toggle="featureBlock_{anchor}"><span class="sr-only">Collapse or Expand</span></button>
  </div>
""".rstrip()
    return f"""
<section id="featureBlock_{anchor}" class="feature-block {block_class}" data-toggler=".is-collapsed">
{header}
  <div class="feature-block__body">
""".rstrip()


def render_resource_link_start(kwargs: dict[str, Any]) -> str:
    title = html.escape(plain_text(kwargs.get("resource_title")))
    url = plain_text(kwargs.get("resource_url"))
    slug = plain_text(kwargs.get("resource_slug"))
    href = url + (f"/{slug}" if slug else "")
    if kwargs.get("internal") and not href.startswith("/"):
        href = f"/{href}"
    target = "" if kwargs.get("internal") else ' target="_blank"'
    return f"""
<div class="media-object list-item list-item-resourcelink">
  <h4 class="text-medium"><a{target} href="{html.escape(href, quote=True)}">{title}</a></h4>
  <p>
""".rstrip()


def render_static_url_tag(match: re.Match[str]) -> str:
    expression = match.group(1).strip()
    name_match = re.match(r"['\"]([^'\"]+)['\"]", expression)
    if not name_match:
        raise SystemExit(f"Unhandled static URL tag: {match.group(0)}")
    name = name_match.group(1)
    rest = expression[name_match.end() :]
    if name == "explore":
        slug_match = re.search(r"['\"]([^'\"]+)['\"]", rest)
        if slug_match:
            return f"/{slug_match.group(1).strip('/')}/"
    if name == "get_type_html":
        kwargs = parse_template_kwargs(rest)
        item_type = plain_text(kwargs.get("type"))
        item_id = plain_text(kwargs.get("id"))
        view = plain_text(kwargs.get("view") or "full")
        if item_type and item_id:
            return f"/{item_type}/{item_id}/{view}/"
    route_map = {
        "index": "/",
        "results": "/search-results/",
        "search": "/search/",
        "lessons": "/lessons/",
        "library": "/library/",
        "videos": "/videos/",
    }
    if name in route_map:
        return route_map[name]
    raise SystemExit(f"Unhandled static URL tag: {match.group(0)}")


def normalize_static_template_links(rendered: str) -> str:
    replacements = {
        'href="donate.html"': 'href="/donate/"',
        'href="sampleblogpost.html"': 'href="/sampleblog/"',
        'href="/sampleblogpost/"': 'href="/sampleblog/"',
        'href="/giza3d"': 'href="/giza3d/"',
    }
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    return rendered


def ensure_no_unhandled_template_syntax(template_name: str, rendered: str) -> None:
    marker_match = re.search(r"{%|{{", rendered)
    if marker_match:
        start = max(marker_match.start() - 40, 0)
        end = min(marker_match.end() + 80, len(rendered))
        raise SystemExit(
            f"Unhandled template syntax in {template_name}: {rendered[start:end]!r}"
        )


def render_giza3d_static_page(repo_root: Path) -> str:
    tours = render_static_template_fragment(
        repo_root,
        (repo_root / "templates" / "partials" / "3d-tours-list.html").read_text(
            encoding="utf-8"
        ),
        {},
    )
    body = f"""
{page_header("Giza 3D", bg="1")}
<div class="row">
  <div class="large-12 columns">
    <iframe class="viewerEmbed giza3dEmbed" data-giza3d-iframe src="https://gizamedia.rc.fas.harvard.edu/images/3D/unity/?mode=FreeExplore" frameborder="0" allowfullscreen allow="vr" style="display: none;"></iframe>
    <div class="viewerEmbed giza3dEmbedToggle" data-giza3d-toggle>
      <div class="gizaViewer">
        <div class="viewerCover"></div>
        <div class="viewerCoverGradient"></div>
        <button class="viewerStartButton">Start Tour</button>
      </div>
    </div>
    <br>
    <p>Explore the models and tours; you will find links to other models throughout. Or choose from individual tours below. You may also use the arrow keys and WASD to navigate.</p>
    <br>
  </div>
</div>
{tours}
<script>
(function () {{
  var params = new URLSearchParams(window.location.search);
  var iframe = document.querySelector('[data-giza3d-iframe]');
  var toggle = document.querySelector('[data-giza3d-toggle]');
  if (!iframe) return;

  if (params.get('mode') === 'matterport' && params.get('m')) {{
    iframe.className = 'viewerEmbed matterportEmbed';
    iframe.src = 'https://my.matterport.com/show/?m=' + encodeURIComponent(params.get('m'));
    iframe.style.display = '';
    if (toggle) toggle.style.display = 'none';
    return;
  }}

  if (params.get('mode') === 'sketchfab' && params.get('id')) {{
    iframe.className = 'viewerEmbed sketchfabEmbed';
    iframe.src = 'https://sketchfab.com/models/' + encodeURIComponent(params.get('id')) + '/embed?preload=1&ui_controls=1&ui_infos=1&ui_inspector=1&ui_stop=1&ui_watermark=1&ui_watermark_link=1';
    iframe.style.display = '';
    if (toggle) toggle.style.display = 'none';
    return;
  }}

  var unityUrl = new URL('https://gizamedia.rc.fas.harvard.edu/images/3D/unity/');
  unityUrl.searchParams.set('mode', params.get('mode') || 'FreeExplore');
  ['guidedTourId', 'itemID'].forEach(function (key) {{
    if (params.get(key)) unityUrl.searchParams.set(key, params.get(key));
  }});
  iframe.src = unityUrl.toString();
}}());
</script>
""".strip()
    ensure_no_unhandled_template_syntax("giza3d.html", body)
    return body


def write_search_pages(output: Path) -> None:
    advanced_search_body = render_static_site_template("search.html").strip()
    results_body = render_static_site_template("search-results.html").strip()
    extra_head = ""
    extra_scripts = "<script>GizaStaticSite.initStaticSearch();</script>"
    search_html = render_page(
        "Search the Archives",
        advanced_search_body,
        description="Search the Digital Giza archives.",
        extra_head=extra_head,
        extra_scripts=extra_scripts,
        index_body=False,
    )
    results_html = render_page(
        "Search Results",
        results_body,
        description="Search the Digital Giza archives.",
        extra_head=extra_head,
        extra_scripts=extra_scripts,
        index_body=False,
    )
    write_text(output / "search" / "index.html", search_html)
    write_text(output / "search-results" / "index.html", results_html)


def write_library_page(
    output: Path,
    library_sources: list[dict[str, Any]],
    pubdocs: list[tuple[ItemSummary, dict[str, Any]]],
) -> None:
    body = [page_header("Digital Giza Library", bg="8")]
    body.append('<div class="row"><section class="large-9 columns">')
    body.append(
        '<p class="lead text-alt">A public list of downloadable Giza publications and catalog publication records.</p>'
    )

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in library_sources:
        name = plain_text(source.get("name")) or "Unknown"
        letter = (plain_text(source.get("sortname")) or name).strip()[:1].upper() or "#"
        grouped[letter].append(source)

    if grouped:
        for letter in sorted(grouped):
            body.append(
                f'<h3 id="alpha-{html.escape(letter.lower())}">{html.escape(letter)}</h3>'
            )
            for source in sorted(
                grouped[letter],
                key=lambda value: plain_text(
                    value.get("sortname") or value.get("name")
                ).lower(),
            ):
                body.append(
                    f'<h5 class="heading-alt">{escape_text(source.get("name"))}</h5>'
                )
                body.append('<ul class="static-site-list">')
                for doc in source.get("docs") or []:
                    text = sanitize_html(plain_text(doc.get("displaytext")))
                    url = plain_text(doc.get("url"))
                    fmt = escape_text(doc.get("format"))
                    link_start = (
                        f'<a href="{html.escape(url, quote=True)}">'
                        if url and is_safe_url(url)
                        else ""
                    )
                    link_end = "</a>" if link_start else ""
                    body.append(
                        f'<li>{link_start}{text}{link_end}<div class="static-site-meta">{fmt}</div></li>'
                    )
                body.append("</ul>")

    if pubdocs:
        body.append('<h2 class="m-t-2">Publication Records</h2>')
        body.append('<ul class="static-site-list">')
        for summary, source in sorted(pubdocs, key=lambda item: item[0].title.lower()):
            pdf = plain_text(source.get("pdf"))
            pdf_link = (
                f' <a href="{html.escape(pdf, quote=True)}">PDF</a>'
                if pdf and is_safe_url(pdf)
                else ""
            )
            body.append(
                f'<li><a href="{summary.url}">{html.escape(summary.title)}</a>{pdf_link}'
                f'<div class="static-site-meta">{escape_text(source.get("format"))} {escape_text(source.get("yearpublished"))}</div></li>'
            )
        body.append("</ul>")

    body.append(
        '</section><aside class="large-3 columns"><div class="feature-block secondary"><h5>Library Search</h5><p>Use site search to find authors, titles, and subjects.</p><p><a class="button" href="/search/">Search</a></p></div></aside></div>'
    )
    write_text(
        output / "library" / "index.html",
        render_page("Digital Giza Library", "\n".join(body)),
    )


def write_videos_page(
    output: Path, videos: list[tuple[ItemSummary, dict[str, Any]]]
) -> None:
    body = [page_header("Video Library", bg="9")]
    body.append('<div class="row"><section class="large-12 columns">')
    body.append(
        '<p class="lead text-alt">Public video records from the Digital Giza catalog.</p>'
    )
    for summary, source in sorted(videos, key=lambda item: item[0].title.lower()):
        primary = primary_display(source)
        main = plain_text(primary.get("main"))
        thumb = cache_harvard_image_url(plain_text(primary.get("thumbnail")))
        body.append('<article class="m-b-2">')
        body.append(
            f'<h3><a href="{summary.url}">{html.escape(summary.title)}</a></h3>'
        )
        body.append('<div class="row">')
        body.append('<div class="medium-6 columns">')
        if main:
            poster = f' poster="{html.escape(thumb, quote=True)}"' if thumb else ""
            body.append(
                f'<video width="100%" controls{poster}><source src="{html.escape(main, quote=True)}">Your browser does not support the video tag.</video>'
            )
            body.append(
                f'<p><a href="{html.escape(main, quote=True)}">Open video source</a></p>'
            )
        elif thumb:
            body.append(
                f'<a href="{summary.url}"><img class="thumbnail" src="{html.escape(thumb, quote=True)}" alt=""></a>'
            )
        body.append("</div>")
        body.append(
            f'<div class="medium-6 columns">{text_to_paragraphs(source.get("description"))}</div>'
        )
        body.append("</div></article>")
    body.append("</section></div>")
    write_text(
        output / "videos" / "index.html", render_page("Video Library", "\n".join(body))
    )


def write_lessons(
    output: Path, content: dict[str, Any], lookup: dict[tuple[str, str], ItemSummary]
) -> None:
    lessons = content["lessons"]
    public_collections = content["public_collections"]

    body = [page_header("Giza @ School", bg="9")]
    body.append(
        '<div class="row"><aside class="large-4 large-push-8 columns"><div class="feature-block secondary"><h5>Lesson Topics</h5><ul class="menu vertical">'
    )
    for lesson in lessons:
        slug = lesson_slug(lesson)
        body.append(
            f'<li><a href="/lessons/{slug}/">{escape_text(lesson.get("title"))}</a></li>'
        )
    body.append('</ul></div></aside><section class="large-8 large-pull-4 columns">')
    for lesson in lessons:
        slug = lesson_slug(lesson)
        summary = plain_text(lesson.get("summary")) or truncate_text(
            plain_text(lesson.get("content")), 240
        )
        body.append(
            f'<article class="static-site-card"><h3><a href="/lessons/{slug}/">{escape_text(lesson.get("title"))}</a></h3><p>{html.escape(summary)}</p></article>'
        )
    body.append("</section></div>")
    write_text(
        output / "lessons" / "index.html", render_page("Giza @ School", "\n".join(body))
    )

    for lesson in lessons:
        slug = lesson_slug(lesson)
        title = plain_text(lesson.get("title")) or "Lesson"
        detail = [page_header(title, bg="9")]
        detail.append('<div class="row"><section class="large-8 columns">')
        detail.append(sanitize_html_field(lesson.get("content")))
        collection_links = []
        for collection_pk in lesson.get("collections") or []:
            collection = public_collections.get(collection_pk)
            if collection:
                collection_links.append(
                    f'<li><a href="/collections/{collection_slug(collection)}/">{escape_text(collection.get("title"))}</a></li>'
                )
        if collection_links:
            detail.append(
                '<section class="feature-block"><div class="feature-block__header"><h3 class="feature-block__title">Collections</h3></div><div class="feature-block__body"><ul>'
            )
            detail.extend(collection_links)
            detail.append("</ul></div></section>")
        detail.append(
            '</section><aside class="large-4 columns"><div class="feature-block secondary"><h5>More Lessons</h5><ul class="menu vertical">'
        )
        for other in lessons:
            if other is lesson:
                continue
            detail.append(
                f'<li><a href="/lessons/{lesson_slug(other)}/">{escape_text(other.get("title"))}</a></li>'
            )
        detail.append("</ul></div></aside></div>")
        write_text(
            output / "lessons" / slug / "index.html",
            render_page(
                title,
                "\n".join(detail),
                description=truncate_text(plain_text(lesson.get("content")), 160),
            ),
        )


def write_collections(
    output: Path, content: dict[str, Any], lookup: dict[tuple[str, str], ItemSummary]
) -> None:
    public_collections = list(content["public_collections"].values())
    collection_items = content["collection_items"]

    body = [page_header("Collections", bg="6")]
    body.append(
        '<div class="row"><section class="large-8 columns"><p class="lead text-alt">Public Digital Giza collections.</p>'
    )
    if not public_collections:
        body.append("<p>No public collections are available.</p>")
    for collection in sorted(
        public_collections, key=lambda value: plain_text(value.get("title")).lower()
    ):
        slug = collection_slug(collection)
        refs = collection_items.get(collection["pk"], [])
        body.append(
            f'<article class="static-site-card"><h3><a href="/collections/{slug}/">{escape_text(collection.get("title"))}</a></h3><p>{len(refs):,} catalog items</p></article>'
        )
    body.append("</section></div>")
    write_text(
        output / "collections" / "index.html",
        render_page("Collections", "\n".join(body)),
    )

    for collection in public_collections:
        slug = collection_slug(collection)
        title = plain_text(collection.get("title")) or "Collection"
        refs = collection_items.get(collection["pk"], [])
        detail = [page_header(title, bg="6")]
        detail.append('<div class="row"><section class="large-10 columns">')
        detail.append(
            f'<p class="lead text-alt">{len(refs):,} public catalog items.</p>'
        )
        detail.append(
            '<ul class="feature-block__list multicol-2 thumbsize-sm thumbs-square static-site-related">'
        )
        for ref in refs:
            item_type = plain_text(ref.get("type"))
            item_id = plain_text(ref.get("es_id"))
            summary = lookup.get((item_type, item_id))
            if summary:
                detail.append(render_summary_card(summary))
            else:
                detail.append(
                    f"<li>{escape_text(item_type)} {escape_text(item_id)}</li>"
                )
        detail.append("</ul></section></div>")
        write_text(
            output / "collections" / slug / "index.html",
            render_page(title, "\n".join(detail)),
        )


_WORKER_OUTPUT: Path | None = None
_WORKER_REDIRECTS = False
_WORKER_BASE_URL = ""


def _init_render_worker(output: Path, generate_redirects: bool, base_url: str) -> None:
    global _WORKER_OUTPUT, _WORKER_REDIRECTS, _WORKER_BASE_URL
    _WORKER_OUTPUT = output
    _WORKER_REDIRECTS = generate_redirects
    _WORKER_BASE_URL = base_url
    warm_engine()


def _render_item_job(job: tuple[str, str, dict[str, Any], ItemSummary]) -> None:
    item_type, item_id, source, summary = job
    assert _WORKER_OUTPUT is not None
    html_text = render_item_page(
        item_type, item_id, source, summary, base_url=_WORKER_BASE_URL
    )
    base = _WORKER_OUTPUT / item_type / item_id
    write_text(base / "full" / "index.html", html_text)
    if has_related_photos(source):
        allphotos = render_item_allphotos_content(
            item_type, item_id, source, base_url=_WORKER_BASE_URL
        )
        write_text(
            base / "allphotos" / "index.html",
            render_page(
                f"All Photos | {summary.title}",
                allphotos.body,
                description=truncate_text(
                    f"All related photos for {summary.title}", 160
                ),
                body_class="section-explore-body header-full mode-intro",
                extra_head=allphotos.extra_head,
                extra_scripts=allphotos.extra_scripts,
                index_body=False,
            ),
        )
    if _WORKER_REDIRECTS:
        write_redirect_page(base / "intro" / "index.html", summary.url)


def has_related_photos(source: dict[str, Any]) -> bool:
    related = source.get("relateditems")
    if not isinstance(related, dict):
        return False
    return bool(related.get("photos"))


def related_photo_manifest_ids(source: dict[str, Any]) -> list[str]:
    related = source.get("relateditems")
    if not isinstance(related, dict):
        return []
    photos = related.get("photos")
    if not isinstance(photos, list):
        return []
    manifest_ids: list[str] = []
    for photo in photos:
        if not isinstance(photo, dict):
            continue
        drs_id = plain_text(photo.get("drs_id")).strip()
        if drs_id:
            manifest_ids.append(drs_id)
    return manifest_ids


def write_item_pages(
    output: Path,
    es_archive: Path,
    giza_member: str,
    manifest_ids: set[str],
    lookup: dict[tuple[str, str], ItemSummary],
    item_limit: int,
    item_limit_per_type: int,
    generate_redirects: bool,
    base_url: str,
    jobs: int,
) -> tuple[Counter[str], set[str], list[ItemSummary]]:
    counts: Counter[str] = Counter()
    required_manifest_ids: set[str] = set()
    emitted_summaries: list[ItemSummary] = []
    total = 0

    def select() -> Iterable[tuple[str, str, dict[str, Any], ItemSummary]]:
        nonlocal total
        for doc in iter_es_docs(es_archive, giza_member):
            item_type = str(doc.get("_type") or "")
            if item_type == "library":
                continue
            if item_limit and total >= item_limit:
                break
            if item_limit_per_type and counts[item_type] >= item_limit_per_type:
                continue

            source = doc.get("_source") or {}
            item_id = get_doc_id(doc)
            if not item_id:
                continue
            summary = lookup.get((item_type, item_id)) or make_summary(
                item_type, item_id, source, manifest_ids
            )
            if summary.has_manifest:
                required_manifest_ids.add(item_manifest_id(item_type, item_id))
            if has_related_photos(source):
                required_manifest_ids.update(related_photo_manifest_ids(source))
            emitted_summaries.append(summary)
            counts[item_type] += 1
            total += 1
            yield item_type, item_id, source, summary

    if jobs <= 1:
        _init_render_worker(output, generate_redirects, base_url)
        for job in select():
            _render_item_job(job)
        return counts, required_manifest_ids, emitted_summaries

    # Rendering each page is CPU-bound and independent, so fan the work out to a
    # pool of worker processes that also write their own files. A fork context
    # lets workers inherit the already-loaded indexes and compiled templates.
    # Work is submitted in bounded batches so the source documents for the whole
    # archive are never materialised in memory at once.
    batch_size = max(jobs * 128, 256)
    batch: list[tuple[str, str, dict[str, Any], ItemSummary]] = []
    with ProcessPoolExecutor(
        max_workers=jobs,
        mp_context=get_context("fork"),
        initializer=_init_render_worker,
        initargs=(output, generate_redirects, base_url),
    ) as executor:
        for job in select():
            batch.append(job)
            if len(batch) >= batch_size:
                list(executor.map(_render_item_job, batch, chunksize=16))
                batch.clear()
        if batch:
            list(executor.map(_render_item_job, batch, chunksize=16))
    return counts, required_manifest_ids, emitted_summaries


_MANIFEST_OUTPUT_DIR: Path | None = None
_MANIFEST_BASE_URL = ""


def _init_manifest_worker(manifest_dir: Path, base_url: str) -> None:
    global _MANIFEST_OUTPUT_DIR, _MANIFEST_BASE_URL
    _MANIFEST_OUTPUT_DIR = manifest_dir
    _MANIFEST_BASE_URL = base_url


def _write_manifest_job(job: tuple[str, dict[str, Any]]) -> None:
    manifest_id, manifest = job
    assert _MANIFEST_OUTPUT_DIR is not None
    # ``manifest`` is this process's own (unpickled or streamed-once) copy, so it
    # can be rewritten in place without a defensive deepcopy.
    rewritten = rewrite_manifest(manifest, manifest_id, _MANIFEST_BASE_URL)
    write_text(
        _MANIFEST_OUTPUT_DIR / f"{manifest_id}.json",
        json.dumps(rewritten, ensure_ascii=False, indent=2),
    )


def write_manifests(
    output: Path,
    es_archive: Path,
    iiif_member: str,
    base_url: str,
    manifest_limit: int,
    required_manifest_ids: set[str],
    jobs: int,
) -> int:
    manifest_dir = output / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    sample_count = 0
    pending_required = set(required_manifest_ids)

    def select() -> Iterable[tuple[str, dict[str, Any]]]:
        nonlocal count, sample_count
        for doc in iter_es_docs(es_archive, iiif_member):
            manifest_id = str(
                doc.get("_id") or (doc.get("_source") or {}).get("id") or ""
            ).strip()
            manifest = (doc.get("_source") or {}).get("manifest")
            if not manifest_id or not isinstance(manifest, dict):
                continue
            sample_slot = not manifest_limit or sample_count < manifest_limit
            required = manifest_id in pending_required
            if not sample_slot and not required:
                continue
            count += 1
            if sample_slot and manifest_limit:
                sample_count += 1
            pending_required.discard(manifest_id)
            yield manifest_id, manifest
            if (
                manifest_limit
                and sample_count >= manifest_limit
                and not pending_required
            ):
                break

    if jobs <= 1:
        _init_manifest_worker(manifest_dir, base_url)
        for job in select():
            _write_manifest_job(job)
    else:
        batch_size = max(jobs * 64, 256)
        batch: list[tuple[str, dict[str, Any]]] = []
        with ProcessPoolExecutor(
            max_workers=jobs,
            mp_context=get_context("fork"),
            initializer=_init_manifest_worker,
            initargs=(manifest_dir, base_url),
        ) as executor:
            for job in select():
                batch.append(job)
                if len(batch) >= batch_size:
                    list(executor.map(_write_manifest_job, batch, chunksize=16))
                    batch.clear()
            if batch:
                list(executor.map(_write_manifest_job, batch, chunksize=16))

    if pending_required:
        missing = ", ".join(sorted(pending_required)[:10])
        extra = "..." if len(pending_required) > 10 else ""
        print(
            f"WARNING: {len(pending_required):,} required manifests were not found: {missing}{extra}",
            file=sys.stderr,
        )
    return count


def write_404(output: Path) -> None:
    body = content_page_body(
        "Page Not Found",
        "The requested page is not available on the static Digital Giza site.",
        [
            'Try <a href="/search/">searching the public catalog</a> or returning to the <a href="/">home page</a>.'
        ],
    )
    write_text(
        output / "404.html",
        render_page("Page Not Found", body, index_body=False, include_umami=False),
    )


def rewrite_manifest(
    manifest: dict[str, Any], manifest_id: str, base_url: str
) -> dict[str, Any]:
    manifest["@id"] = absolute_url(base_url, manifest_url(manifest_id))
    rewrite_iiif_refs(manifest, manifest_id, base_url)
    manifest["@id"] = absolute_url(base_url, manifest_url(manifest_id))
    return manifest


def rewrite_iiif_refs(value: Any, manifest_id: str, base_url: str) -> Any:
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if key in {"@id", "on", "startCanvas"} and isinstance(child, str):
                value[key] = cache_harvard_image_url(
                    rewrite_iiif_ref(child, manifest_id, base_url, is_top_id=False)
                )
            else:
                value[key] = rewrite_iiif_refs(child, manifest_id, base_url)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            value[index] = rewrite_iiif_refs(child, manifest_id, base_url)
    elif isinstance(value, str):
        return cache_harvard_image_url(value)
    return value


def rewrite_iiif_ref(
    ref: str, manifest_id: str, base_url: str, *, is_top_id: bool
) -> str:
    if not ref:
        return ref
    parsed = urlparse(ref)
    if parsed.scheme in {"http", "https", "data", "urn"}:
        return ref
    if is_top_id or ref == manifest_id:
        return absolute_url(base_url, manifest_url(manifest_id))
    if ref.startswith(f"{manifest_id}/"):
        return absolute_url(base_url, f"/manifests/{ref}")
    if ref.startswith("/"):
        return absolute_url(base_url, ref)
    return ref


def write_redirect_page(path: Path, target: str) -> None:
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={html.escape(target, quote=True)}"><link rel="canonical" href="{html.escape(target, quote=True)}"><title>Redirecting</title></head>
<body><p>Redirecting to <a href="{html.escape(target, quote=True)}">{html.escape(target)}</a>.</p><script>window.location.replace({json.dumps(target)});</script></body></html>
"""
    write_text(path, body)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
