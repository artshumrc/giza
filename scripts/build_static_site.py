#!/usr/bin/env python3
"""Build the temporary static Digital Giza site from exported data.

This intentionally does not import Django, Elasticsearch, or project settings.
It reads the compressed production exports directly and emits static HTML/JSON.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import html
import json
import re
import shutil
import sys
import tarfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


EXPECTED_ITEM_COUNT = 158_968
EXPECTED_MANIFEST_COUNT = 134_580

TYPE_LABELS = {
    "3dmodels": "3D Models",
    "ancientpeople": "Ancient People",
    "animals": "Animals",
    "diarypages": "Diary Pages",
    "drawings": "Drawings",
    "groups": "Groups",
    "institutions": "Institutions",
    "mapsandplans": "Maps and Plans",
    "modernpeople": "Modern People",
    "objects": "Objects",
    "photos": "Photos",
    "pubdocs": "Published Documents",
    "sites": "Sites",
    "unpubdocs": "Unpublished Documents",
    "videos": "Videos",
}

RELATED_TYPE_ALIASES = {
    "giza3d": "3dmodels",
    "models": "3dmodels",
    "plansanddrawings": "drawings",
}

RELATED_SECTION_LABELS = {
    "3dmodels": "3D Models",
    "ancientpeople": "Ancient People",
    "animals": "Animals",
    "audio": "Audio",
    "diarypages": "Excavation Diary Pages",
    "drawings": "Drawings",
    "groups": "Groups",
    "institutions": "Institutions",
    "mapsandplans": "Maps and Plans",
    "modernpeople": "Modern People",
    "objects": "Finds",
    "photos": "Photos",
    "pubdocs": "Published Documents",
    "sites": "Tombs and Monuments",
    "unpubdocs": "Unpublished Documents",
    "videos": "Videos",
}

RELATED_ORDER = [
    "sites",
    "objects",
    "diarypages",
    "mapsandplans",
    "drawings",
    "photos",
    "3dmodels",
    "giza3d",
    "videos",
    "audio",
    "ancientpeople",
    "modernpeople",
    "institutions",
    "groups",
    "animals",
    "pubdocs",
    "unpubdocs",
]

DETAIL_FIELDS = [
    ("ID", "number", "text"),
    ("Alternate IDs", "allnumbers", "text"),
    ("Site Name", "sitename", "text"),
    ("Site Type", "sitetype", "text"),
    ("Site Dates", "sitedates", "text"),
    ("Tomb Owner", "tombowner", "text"),
    ("Department", "department", "text"),
    ("Classification", "classificationtext", "text"),
    ("Period", "period", "text"),
    ("Date", "date", "text"),
    ("Entry Date", "entrydate", "text"),
    ("Title", "title", "text"),
    ("Medium", "medium", "text"),
    ("Dimensions", "dimensions", "text"),
    ("Credit Line", "creditline", "text"),
    ("Provenance", "provenance", "text"),
    ("Authors", "authors", "text"),
    ("Year Published", "yearpublished", "text"),
    ("Format", "format", "text"),
    ("Language", "language", "text"),
    ("Pages", "numofpages", "text"),
    ("Journal", "journal", "text"),
    ("Series", "series", "text"),
    ("Subjects", "subjects", "text"),
    ("Media View", "mediaview", "text"),
    ("Nationality", "nationality", "text"),
    ("Display Date", "displaydate", "text"),
    ("Institution", "institution", "text"),
    ("Gender", "gender", "text"),
    ("Citation", "boilertext", "safe_html"),
    ("Bibliography", "bibreferences", "text"),
    ("Notes", "notes", "text"),
    ("Remarks", "remarks", "text"),
    ("Research Activity", "researchactivity", "text"),
    ("Researcher Comments", "researchercomments", "text"),
    ("Condition", "condition", "text"),
    ("Location Notes", "locationnotes", "text"),
    ("Problems/Questions", "problemsquestions", "text"),
]

STATIC_SITE_CSS = """
.static-site-pagefind-filters {
  height: 0;
  overflow: hidden;
  position: absolute;
  width: 0;
}
.static-site-grid {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  margin: 1.5rem 0;
}
.static-site-card {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 3px;
  padding: 1rem;
}
.static-site-card img,
.static-site-thumb {
  height: auto;
  max-width: 100%;
}
.static-site-home-video {
  background: transparent url('/static/video/home/GizaHome_web.jpg') center center / cover no-repeat;
  bottom: 0;
  left: 0;
  overflow: hidden;
  position: absolute;
  right: 0;
  top: 0;
  z-index: -1;
}
.static-site-home-video video {
  height: 100%;
  left: 0;
  object-fit: cover;
  position: absolute;
  top: 0;
  width: 100%;
}
.static-site-hero-search.input-group {
  margin-bottom: 0.1rem;
}
.static-site-hero-search .input-group-field {
  height: 2.5rem;
  margin: 0;
}
.static-site-hero-search .button.icon-search {
  height: 2.5rem;
  margin: 0;
  min-width: 3.75rem;
  padding: 0.72em 1em;
}
.static-site-home-features {
  margin-top: 0.5rem;
}
.static-site-home-features .border-left-dark {
  min-height: 100%;
}
.static-site-home-features img {
  width: 100%;
}
.static-site-list {
  list-style: none;
  margin-left: 0;
}
.static-site-list > li {
  border-bottom: 1px solid #e5e5e5;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
}
.static-site-meta {
  color: #666;
  font-size: 0.875rem;
}
.static-site-media-link {
  display: inline-block;
  margin-top: 0.5rem;
}
.static-site-search {
  margin: 2rem 0;
}
.static-site-related .media-object-section:first-child {
  width: 90px;
}
.static-site-related img {
  max-height: 80px;
  object-fit: cover;
}
.static-site-footer-note {
  margin-top: 1rem;
}
@media (max-width: 640px) {
  .top-bar-left.hide-for-small-only {
    display: none !important;
  }
  .static-site-related .media-object {
    display: block;
  }
  .static-site-related .media-object-section:first-child {
    width: auto;
  }
}
""".strip()

STATIC_SITE_JS = """
(function () {
  function seedSearchBox(term) {
    if (!term) return;
    var attempts = 0;
    var timer = window.setInterval(function () {
      attempts += 1;
      var input = document.querySelector('#search input[type="search"], #search input[type="text"]');
      if (input) {
        input.value = term;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        window.clearInterval(timer);
      } else if (attempts > 40) {
        window.clearInterval(timer);
      }
    }, 100);
  }

  window.GizaStaticSite = {
    initPagefind: function () {
      var target = document.querySelector('#search');
      if (!target || !window.PagefindUI) return;
      new window.PagefindUI({
        element: '#search',
        resetStyles: false,
        showImages: true,
        showSubResults: true
      });
      var params = new URLSearchParams(window.location.search);
      seedSearchBox(params.get('q') || params.get('query') || '');
    }
  };
}());
""".strip()


@dataclass(frozen=True)
class ItemSummary:
    type: str
    id: str
    title: str
    url: str
    thumbnail: str
    description: str
    department: str
    classification: str
    material: str
    period: str
    site_name: str
    has_image: bool
    has_manifest: bool
    has_pdf: bool


class SafeHTML(HTMLParser):
    """Very small sanitizer for known public content fields."""

    allowed_tags = {
        "a",
        "abbr",
        "b",
        "blockquote",
        "br",
        "cite",
        "code",
        "div",
        "em",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "img",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "sub",
        "sup",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "u",
        "ul",
    }
    allowed_attrs = {
        "a": {"href", "title"},
        "img": {"alt", "height", "src", "title", "width"},
        "td": {"colspan", "rowspan"},
        "th": {"colspan", "rowspan"},
    }
    void_tags = {"br", "hr", "img"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in self.allowed_tags:
            return
        rendered_attrs = []
        for name, value in attrs:
            name = name.lower()
            if name not in self.allowed_attrs.get(tag, set()) or value is None:
                continue
            if name in {"href", "src"} and not is_safe_url(value):
                continue
            rendered_attrs.append(f'{name}="{html.escape(value, quote=True)}"')
        attr_text = " " + " ".join(rendered_attrs) if rendered_attrs else ""
        self.parts.append(f"<{tag}{attr_text}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.allowed_tags and tag not in self.void_tags:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data))

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def rendered(self) -> str:
        return "".join(self.parts)


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
        help="Generate intro/allphotos redirect pages for emitted item pages.",
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

    write_core_static_pages(args.output)
    write_search_pages(args.output)
    write_library_page(args.output, indexes["library_sources"], indexes["pubdocs"])
    write_videos_page(args.output, indexes["videos"])
    write_lessons(args.output, content, indexes["lookup"])
    write_collections(args.output, content, indexes["lookup"])
    item_counts, required_manifest_ids = write_item_pages(
        args.output,
        args.es_archive,
        giza_member,
        manifest_ids,
        indexes["lookup"],
        args.item_limit,
        args.item_limit_per_type,
        args.generate_item_redirects,
    )
    manifest_count = write_manifests(
        args.output,
        args.es_archive,
        iiif_member,
        base_url,
        args.manifest_limit,
        required_manifest_ids,
    )
    write_404(args.output)

    emitted_item_total = sum(item_counts.values())
    print("Generated item pages:")
    for item_type, count in sorted(item_counts.items()):
        print(f"  {item_type}: {count:,}")
    print(f"Generated {emitted_item_total:,} total item pages")
    print(f"Generated {manifest_count:,} manifests")

    if not args.item_limit and not args.item_limit_per_type and emitted_item_total != EXPECTED_ITEM_COUNT:
        print(
            f"WARNING: expected {EXPECTED_ITEM_COUNT:,} item pages, generated {emitted_item_total:,}",
            file=sys.stderr,
        )
    if not args.manifest_limit and manifest_count != EXPECTED_MANIFEST_COUNT:
        print(
            f"WARNING: expected {EXPECTED_MANIFEST_COUNT:,} manifests, generated {manifest_count:,}",
            file=sys.stderr,
        )
    print("Run `npx -y pagefind --site <output>` after this build to create the search index.")
    return 0


def validate_inputs(es_archive: Path, content_dump: Path, repo_root: Path) -> None:
    missing = [path for path in [es_archive, content_dump, repo_root / "static"] if not path.exists()]
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
    helper_dir.mkdir(parents=True, exist_ok=True)
    write_text(helper_dir / "static-site.css", STATIC_SITE_CSS)
    write_text(helper_dir / "static-site.js", STATIC_SITE_JS)


def discover_es_members(es_archive: Path) -> tuple[str, str]:
    with tarfile.open(es_archive, "r:gz") as archive:
        names = archive.getnames()
    giza_member = next((name for name in names if name.endswith("/giza.ndjson.gz")), None)
    iiif_member = next((name for name in names if name.endswith("/iiif.ndjson.gz")), None)
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
                    raise SystemExit(f"Invalid JSON in {member_name} line {line_number}: {exc}") from exc


def collect_manifest_ids(es_archive: Path, iiif_member: str) -> set[str]:
    ids: set[str] = set()
    for doc in iter_es_docs(es_archive, iiif_member):
        manifest_id = str(doc.get("_id") or (doc.get("_source") or {}).get("id") or "").strip()
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

    lessons.sort(key=lambda lesson: (plain_text(lesson.get("title")).lower(), lesson.get("pk") or 0))
    print(f"Loaded {len(lessons):,} lessons and {len(public_collections):,} public collections")
    return {
        "topics": topics,
        "lessons": lessons,
        "public_collections": public_collections,
        "collection_items": collection_items,
    }


def write_core_static_pages(output: Path) -> None:
    pages = {
        "": (
            "Home",
            home_body(),
            "The Digital Giza public catalog, library, lessons, videos, and IIIF viewers.",
        ),
        "about": (
            "About the Giza Project",
            content_page_body(
                "About the Giza Project",
                "The Giza Project is an international initiative based at Harvard University that assembles, curates, and presents archaeological records about the Giza Plateau.",
                [
                    "Digital Giza brings together archival holdings from museums, universities, and expedition records so that researchers, teachers, students, and the public can explore Giza documentation in one place.",
                    "The project includes excavation photographs, maps and plans, published and unpublished documents, objects, people, places, videos, and 3D resources.",
                ],
            ),
            "About the Giza Project at Harvard University.",
        ),
        "contact": (
            "Contact",
            content_page_body(
                "Contact",
                "For questions about Digital Giza, contact the Giza Project at Harvard University.",
                [
                    'Project information is available from the <a href="https://giza.fas.harvard.edu/">Giza Project</a> and Harvard Arts and Humanities Research Computing.',
                    'Authors with Giza-related publications available as PDFs are encouraged to contact project staff about the <a href="/library/">Digital Giza Library</a>.',
                ],
            ),
            "Contact information for Digital Giza.",
        ),
        "gizacard": (
            "The GizaCARD",
            content_page_body(
                "The GizaCARD",
                "The Giza Consolidated Archaeological Reference Database organizes Digital Giza records and their relationships.",
                [
                    "The database connects monuments, artifacts, documents, photographs, people, institutions, and publications so public pages can expose related materials together.",
                    'Use <a href="/search/">search</a> or browse item pages to explore the public catalog.',
                ],
            ),
            "The data model behind Digital Giza.",
        ),
        "news": (
            "News",
            content_page_body(
                "News",
                "News and updates from the Giza Project.",
                [
                    "For current Harvard project news, consult official Harvard and Giza Project channels.",
                    'Explore public resources through the <a href="/search/">catalog search</a>, <a href="/library/">library</a>, <a href="/lessons/">lessons</a>, and <a href="/videos/">videos</a>.',
                ],
            ),
            "Digital Giza news.",
        ),
        "resources": (
            "Educational Resources",
            content_page_body(
                "Educational Resources",
                "Digital Giza includes public teaching resources and catalog materials for learning about ancient Giza.",
                [
                    'Start with <a href="/gizaatschool/">Giza @ School</a>, <a href="/lessons/">lesson topics</a>, <a href="/videos/">videos</a>, and the <a href="/library/">Digital Giza Library</a>.',
                ],
            ),
            "Educational resources from Digital Giza.",
        ),
        "blog": (
            "Blog",
            content_page_body(
                "Blog",
                "Explore Digital Giza public resources and project materials.",
                [
                    'Explore public resources through the <a href="/search/">catalog search</a>, <a href="/library/">library</a>, and <a href="/lessons/">lessons</a>.',
                ],
            ),
            "Digital Giza blog.",
        ),
        "donate": (
            "Donate",
            content_page_body(
                "Donate",
                "Support the Giza Project through Harvard giving.",
                [
                    '<a class="button" href="https://community.alumni.harvard.edu/give/34086571">Donate through Harvard</a>',
                ],
            ),
            "Support the Giza Project.",
        ),
        "gizaintro": (
            "Introduction to Giza",
            content_page_body(
                "Introduction to Giza",
                "The Giza Plateau, southwest of modern Cairo, is home to the pyramids of Khufu, Khafre, and Menkaure, the Great Sphinx, and extensive cemeteries and settlements.",
                [
                    'Explore the <a href="/sites/1782/full/">Great Pyramid</a>, <a href="/sites/2080/full/">Sphinx</a>, people, monuments, photographs, maps, and documents through the public catalog.',
                    'Teaching introductions are available in <a href="/lessons/">lesson topics</a> and <a href="/commontopics/">common topics</a>.',
                ],
            ),
            "Introduction to the Giza Plateau.",
        ),
        "archaeology": (
            "Archaeology at Giza",
            content_page_body(
                "Archaeology at Giza",
                "More than a century of archaeological work at Giza produced the photographs, maps, diaries, object records, publications, and research materials preserved in Digital Giza.",
                [
                    'Search for archaeologists such as <a href="/search/?q=Reisner">George Andrew Reisner</a>, monuments, expedition records, and excavation media.',
                    'Browse related <a href="/photos/49329/full/">photographs</a>, <a href="/mapsandplans/5590/full/">maps and plans</a>, and <a href="/diarypages/2448/full/">diary pages</a>.',
                ],
            ),
            "Archaeology and excavation history at Giza.",
        ),
        "commontopics": (
            "Common Topics",
            content_page_body(
                "Common Topics",
                "Common topics provide entry points into major themes for studying Giza.",
                [
                    'Continue to <a href="/lessons/">lesson topics</a> for focused introductions, or search the catalog for pyramids, tombs, mastabas, false doors, burial shafts, and daily life.',
                ],
            ),
            "Common topics about Giza.",
        ),
        "faq": (
            "Glossary and FAQs",
            content_page_body(
                "Glossary and FAQs",
                "Digital Giza records use archaeological, historical, and museum terminology.",
                [
                    "Use catalog search to locate examples of specific terms, people, monuments, artifacts, or publications.",
                    'For teaching-oriented explanations, visit <a href="/lessons/">lesson topics</a>.',
                ],
            ),
            "Glossary and frequently asked questions.",
        ),
        "gizaatschool": (
            "Giza @ School",
            giza_at_school_body(),
            "Teaching resources for Giza.",
        ),
        "giza3d": (
            "Giza 3D",
            giza3d_body(),
            "Giza 3D resources and model links.",
        ),
    }

    for slug, (title, body, description) in pages.items():
        path = output / slug / "index.html" if slug else output / "index.html"
        write_text(path, render_page(title, body, description=description))


def home_body() -> str:
    return """
<section class="home-hero-container">
  <div class="row row-padded">
    <div class="video-bg-home">
      <div class="static-site-home-video">
        <video autoplay loop muted playsinline poster="/static/video/home/GizaHome_web.jpg">
          <source src="/static/video/home/GizaHome_web.mp4" type="video/mp4">
          <source src="/static/video/home/GizaHome_web.webm" type="video/webm">
          <source src="/static/video/home/GizaHome_web.ogv" type="video/ogg">
        </video>
      </div>
      <div class="home-hero-title"><h1><span class="title-text-alt">Welcome to the</span> Giza Plateau</h1></div>
      <div class="home-hero-content">
        <div class="medium-8 columns">
          <p class="lead text-alt" style="line-height:1.4">The Giza Project gives you access to the largest collection of information, media, and research materials ever assembled about the Pyramids and related sites on Egypt&rsquo;s Giza Plateau.</p>
        </div>
        <div class="medium-4 columns">
          <form action="/search-results/">
            <p class="text-alt" style="color:#fff; margin-bottom:0.1rem;"><em>Search the archives:</em></p>
            <div class="input-group static-site-hero-search">
              <input class="input-group-field" type="text" name="q" placeholder="Search">
              <div class="input-group-button"><button type="submit" class="button icon-search"><span class="show-for-sr">Search</span></button></div>
            </div>
          </form>
          <small>or go to <a class="link-lighter" href="/search/">Advanced Search</a></small>
        </div>
      </div>
      <div class="home-hero-overlay"></div>
    </div>
  </div>
</section>
<div class="row p-r-1 static-site-home-features" data-equalizer data-equalize-on="medium">
  <section class="medium-6 large-3 columns">
    <div class="d-flex flex-v border-left-dark p-l-1 m-r-neg1 m-b-2" data-equalizer-watch>
      <div class="flex-header"><h2 class="h2-minor text-medium m-b-1"><a class="heading-link" href="/giza3d/">Explore Giza 3D</a></h2></div>
      <div class="flex-body text-smaller"><p><a href="/giza3d/"><img class="img-fluid img-fluid-mw325 border-dark" src="/static/images/home-feature-giza3d.png" alt="Digital rendering of the Giza Plateau as seen from the air"></a></p><p>Immerse yourself in <strong>realistic 3D reconstructions</strong> of the Giza plateau.</p></div>
      <div class="flex-footer"><div class="row"><div class="columns small-12 md-phone-6 medium-12 lg-tablet-8 large-12"><a href="/giza3d/" class="button primary expanded m-b-0">Jump In <i class="icon-angle-right"></i></a></div></div></div>
    </div>
  </section>
  <section class="medium-6 large-3 columns">
    <div class="d-flex flex-v border-left-dark p-l-1 m-r-neg1 m-b-2" data-equalizer-watch>
      <div class="flex-header"><h2 class="h2-minor text-medium m-b-1"><a class="heading-link" href="/gizaatschool/">Giza @ School</a></h2></div>
      <div class="flex-body text-smaller"><p><a href="/gizaatschool/"><img class="img-fluid img-fluid-mw325 border-dark" src="/static/images/home-feature-school.png" alt="Digital rendering of a figure from Giza's past standing in front of a tomb entrance"></a></p><p>Resources designed especially for <strong>teachers and students</strong>.</p></div>
      <div class="flex-footer"><div class="row"><div class="columns small-12 md-phone-6 medium-12 lg-tablet-8 large-12"><a href="/gizaatschool/" class="button primary expanded m-b-0">View Resources <i class="icon-angle-right"></i></a></div></div></div>
    </div>
  </section>
  <section class="medium-6 large-3 columns">
    <div class="d-flex flex-v border-left-dark p-l-1 m-r-neg1 m-b-2" data-equalizer-watch>
      <div class="flex-header"><h2 class="h2-minor text-medium m-b-1"><a class="heading-link" href="/collections/">Make it Yours</a></h2></div>
      <div class="flex-body text-smaller"><p><a href="/collections/"><img class="img-fluid img-fluid-mw325 border-dark" src="/static/images/home-feature-mygiza.png" alt="Digital rendering of painted wall decoration"></a></p><p>Browse public collections of related Digital Giza records.</p></div>
      <div class="flex-footer"><div class="row"><div class="columns small-12 md-phone-6 medium-12 lg-tablet-8 large-12"><a href="/collections/" class="button primary expanded m-b-0">Browse Collections <i class="icon-angle-right"></i></a></div></div></div>
    </div>
  </section>
  <section class="medium-6 large-3 columns">
    <div class="d-flex flex-v border-left-dark p-l-1 m-r-neg1 m-b-2" data-equalizer-watch>
      <div class="flex-header"><h2 class="h2-minor text-medium m-b-1"><a class="heading-link" href="https://community.alumni.harvard.edu/give/34086571">Support the Project</a></h2></div>
      <div class="flex-body text-smaller"><p>The Giza Project, an international collaboration based at Harvard University, aims to <strong>assemble and provide access to all archaeological records</strong> about the most famous site in the world: the Pyramids, surrounding cemeteries and settlements of Giza, Egypt.</p></div>
      <div class="flex-footer"><div class="row"><div class="columns small-12 md-phone-6 medium-12 lg-tablet-8 large-12"><a href="https://community.alumni.harvard.edu/give/34086571" class="button primary expanded m-b-0">Donate Now <i class="icon-angle-right"></i></a></div></div></div>
    </div>
  </section>
</div>
""".strip()


def content_page_body(title: str, lead: str, paragraphs: list[str]) -> str:
    body = [page_header(title, bg="6")]
    body.append('<div class="row"><section class="large-8 columns">')
    body.append(f'<p class="lead text-alt">{sanitize_html(lead)}</p>')
    for paragraph in paragraphs:
        body.append(f"<p>{sanitize_html(paragraph)}</p>")
    body.append('</section><aside class="large-4 columns"><div class="feature-block secondary"><h5>Explore</h5><ul class="menu vertical"><li><a href="/search/">Search</a></li><li><a href="/library/">Library</a></li><li><a href="/videos/">Videos</a></li><li><a href="/lessons/">Lessons</a></li></ul></div></aside></div>')
    return "\n".join(body)


def giza_at_school_body() -> str:
    return """
<div class="page-header header-bg-9"><div class="row title"><header class="large-12 columns"><h1>Giza @ School</h1></header></div></div>
<div class="row"><section class="large-8 columns">
  <p class="lead text-alt">Teaching resources for learning about ancient Giza and the archaeological record.</p>
  <div class="static-site-grid">
    <article class="static-site-card"><h3>Lesson Topics</h3><p>Read public lesson topics from the Digital Giza content dump.</p><p><a class="button" href="/lessons/">View Lessons</a></p></article>
    <article class="static-site-card"><h3>Video Library</h3><p>Watch public video records from the catalog export.</p><p><a class="button" href="/videos/">View Videos</a></p></article>
    <article class="static-site-card"><h3>Common Topics</h3><p>Start with common terms and themes.</p><p><a class="button" href="/commontopics/">Common Topics</a></p></article>
  </div>
</section></div>
""".strip()


def giza3d_body() -> str:
    links = [
        ("Giza Plateau", "/3dmodels/71017/full/"),
        ("Khafre Pyramid", "/3dmodels/71018/full/"),
        ("Khafre Pyramid Temple", "/3dmodels/71019/full/"),
        ("Khafre Valley Temple", "/3dmodels/71020/full/"),
        ("Sphinx", "/3dmodels/71021/full/"),
        ("Sphinx Temple", "/3dmodels/71023/full/"),
    ]
    items = "".join(f'<li><a href="{href}">{html.escape(label)}</a></li>' for label, href in links)
    return f"""
<div class="page-header header-bg-6"><div class="row title"><header class="large-12 columns"><h1>Giza 3D</h1></header></div></div>
<div class="row"><section class="large-8 columns">
  <p class="lead text-alt">Explore 3D model records and external 3D media connected to the Giza Project.</p>
  <ul class="static-site-list">{items}</ul>
</section></div>
""".strip()


def write_search_pages(output: Path) -> None:
    body = """
<div class="page-header header-bg-6"><div class="row title"><header class="large-12 columns"><h1>Search Digital Giza</h1></header></div></div>
<div class="row"><section class="large-12 columns">
  <p class="lead text-alt">Search public catalog records, static pages, lessons, videos, library entries, and public collection pages.</p>
  <div id="search" class="static-site-search"></div>
</section></div>
""".strip()
    extra_head = '<link href="/pagefind/pagefind-ui.css" rel="stylesheet">'
    extra_scripts = '<script src="/pagefind/pagefind-ui.js"></script><script>GizaStaticSite.initPagefind();</script>'
    html_text = render_page(
        "Search Digital Giza",
        body,
        description="Search Digital Giza public records.",
        extra_head=extra_head,
        extra_scripts=extra_scripts,
        index_body=False,
    )
    write_text(output / "search" / "index.html", html_text)
    write_text(output / "search-results" / "index.html", html_text)


def write_library_page(
    output: Path,
    library_sources: list[dict[str, Any]],
    pubdocs: list[tuple[ItemSummary, dict[str, Any]]],
) -> None:
    body = [page_header("Digital Giza Library", bg="8")]
    body.append('<div class="row"><section class="large-9 columns">')
    body.append('<p class="lead text-alt">A public list of downloadable Giza publications and catalog publication records.</p>')

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in library_sources:
        name = plain_text(source.get("name")) or "Unknown"
        letter = (plain_text(source.get("sortname")) or name).strip()[:1].upper() or "#"
        grouped[letter].append(source)

    if grouped:
        for letter in sorted(grouped):
            body.append(f'<h3 id="alpha-{html.escape(letter.lower())}">{html.escape(letter)}</h3>')
            for source in sorted(grouped[letter], key=lambda value: plain_text(value.get("sortname") or value.get("name")).lower()):
                body.append(f'<h5 class="heading-alt">{escape_text(source.get("name"))}</h5>')
                body.append('<ul class="static-site-list">')
                for doc in source.get("docs") or []:
                    text = sanitize_html(plain_text(doc.get("displaytext")))
                    url = plain_text(doc.get("url"))
                    fmt = escape_text(doc.get("format"))
                    link_start = f'<a href="{html.escape(url, quote=True)}">' if url and is_safe_url(url) else ""
                    link_end = "</a>" if link_start else ""
                    body.append(f'<li>{link_start}{text}{link_end}<div class="static-site-meta">{fmt}</div></li>')
                body.append("</ul>")

    if pubdocs:
        body.append('<h2 class="m-t-2">Publication Records</h2>')
        body.append('<ul class="static-site-list">')
        for summary, source in sorted(pubdocs, key=lambda item: item[0].title.lower()):
            pdf = plain_text(source.get("pdf"))
            pdf_link = f' <a href="{html.escape(pdf, quote=True)}">PDF</a>' if pdf and is_safe_url(pdf) else ""
            body.append(
                f'<li><a href="{summary.url}">{html.escape(summary.title)}</a>{pdf_link}'
                f'<div class="static-site-meta">{escape_text(source.get("format"))} {escape_text(source.get("yearpublished"))}</div></li>'
            )
        body.append("</ul>")

    body.append('</section><aside class="large-3 columns"><div class="feature-block secondary"><h5>Library Search</h5><p>Use site search to find authors, titles, and subjects.</p><p><a class="button" href="/search/">Search</a></p></div></aside></div>')
    write_text(output / "library" / "index.html", render_page("Digital Giza Library", "\n".join(body)))


def write_videos_page(output: Path, videos: list[tuple[ItemSummary, dict[str, Any]]]) -> None:
    body = [page_header("Video Library", bg="9")]
    body.append('<div class="row"><section class="large-12 columns">')
    body.append('<p class="lead text-alt">Public video records from the Digital Giza catalog.</p>')
    for summary, source in sorted(videos, key=lambda item: item[0].title.lower()):
        primary = source.get("primarydisplay") if isinstance(source.get("primarydisplay"), dict) else {}
        main = plain_text(primary.get("main"))
        thumb = plain_text(primary.get("thumbnail"))
        body.append("<article class=\"m-b-2\">")
        body.append(f'<h3><a href="{summary.url}">{html.escape(summary.title)}</a></h3>')
        body.append('<div class="row">')
        body.append('<div class="medium-6 columns">')
        if main:
            poster = f' poster="{html.escape(thumb, quote=True)}"' if thumb else ""
            body.append(f'<video width="100%" controls{poster}><source src="{html.escape(main, quote=True)}">Your browser does not support the video tag.</video>')
            body.append(f'<p><a href="{html.escape(main, quote=True)}">Open video source</a></p>')
        elif thumb:
            body.append(f'<a href="{summary.url}"><img class="thumbnail" src="{html.escape(thumb, quote=True)}" alt=""></a>')
        body.append("</div>")
        body.append(f'<div class="medium-6 columns">{text_to_paragraphs(source.get("description"))}</div>')
        body.append("</div></article>")
    body.append("</section></div>")
    write_text(output / "videos" / "index.html", render_page("Video Library", "\n".join(body)))


def write_lessons(output: Path, content: dict[str, Any], lookup: dict[tuple[str, str], ItemSummary]) -> None:
    lessons = content["lessons"]
    public_collections = content["public_collections"]

    body = [page_header("Giza @ School", bg="9")]
    body.append('<div class="row"><aside class="large-4 large-push-8 columns"><div class="feature-block secondary"><h5>Lesson Topics</h5><ul class="menu vertical">')
    for lesson in lessons:
        slug = lesson_slug(lesson)
        body.append(f'<li><a href="/lessons/{slug}/">{escape_text(lesson.get("title"))}</a></li>')
    body.append('</ul></div></aside><section class="large-8 large-pull-4 columns">')
    for lesson in lessons:
        slug = lesson_slug(lesson)
        summary = plain_text(lesson.get("summary")) or truncate_text(plain_text(lesson.get("content")), 240)
        body.append(f'<article class="static-site-card"><h3><a href="/lessons/{slug}/">{escape_text(lesson.get("title"))}</a></h3><p>{html.escape(summary)}</p></article>')
    body.append("</section></div>")
    write_text(output / "lessons" / "index.html", render_page("Giza @ School", "\n".join(body)))

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
                collection_links.append(f'<li><a href="/collections/{collection_slug(collection)}/">{escape_text(collection.get("title"))}</a></li>')
        if collection_links:
            detail.append('<section class="feature-block"><div class="feature-block__header"><h3 class="feature-block__title">Collections</h3></div><div class="feature-block__body"><ul>')
            detail.extend(collection_links)
            detail.append("</ul></div></section>")
        detail.append('</section><aside class="large-4 columns"><div class="feature-block secondary"><h5>More Lessons</h5><ul class="menu vertical">')
        for other in lessons:
            if other is lesson:
                continue
            detail.append(f'<li><a href="/lessons/{lesson_slug(other)}/">{escape_text(other.get("title"))}</a></li>')
        detail.append('</ul></div></aside></div>')
        write_text(
            output / "lessons" / slug / "index.html",
            render_page(title, "\n".join(detail), description=truncate_text(plain_text(lesson.get("content")), 160)),
        )


def write_collections(output: Path, content: dict[str, Any], lookup: dict[tuple[str, str], ItemSummary]) -> None:
    public_collections = list(content["public_collections"].values())
    collection_items = content["collection_items"]

    body = [page_header("Collections", bg="6")]
    body.append('<div class="row"><section class="large-8 columns"><p class="lead text-alt">Public Digital Giza collections.</p>')
    if not public_collections:
        body.append("<p>No public collections are available.</p>")
    for collection in sorted(public_collections, key=lambda value: plain_text(value.get("title")).lower()):
        slug = collection_slug(collection)
        refs = collection_items.get(collection["pk"], [])
        body.append(f'<article class="static-site-card"><h3><a href="/collections/{slug}/">{escape_text(collection.get("title"))}</a></h3><p>{len(refs):,} catalog items</p></article>')
    body.append("</section></div>")
    write_text(output / "collections" / "index.html", render_page("Collections", "\n".join(body)))

    for collection in public_collections:
        slug = collection_slug(collection)
        title = plain_text(collection.get("title")) or "Collection"
        refs = collection_items.get(collection["pk"], [])
        detail = [page_header(title, bg="6")]
        detail.append('<div class="row"><section class="large-10 columns">')
        detail.append(f'<p class="lead text-alt">{len(refs):,} public catalog items.</p>')
        detail.append('<ul class="feature-block__list multicol-2 thumbsize-sm thumbs-square static-site-related">')
        for ref in refs:
            item_type = plain_text(ref.get("type"))
            item_id = plain_text(ref.get("es_id"))
            summary = lookup.get((item_type, item_id))
            if summary:
                detail.append(render_summary_card(summary))
            else:
                detail.append(f'<li>{escape_text(item_type)} {escape_text(item_id)}</li>')
        detail.append("</ul></section></div>")
        write_text(output / "collections" / slug / "index.html", render_page(title, "\n".join(detail)))


def write_item_pages(
    output: Path,
    es_archive: Path,
    giza_member: str,
    manifest_ids: set[str],
    lookup: dict[tuple[str, str], ItemSummary],
    item_limit: int,
    item_limit_per_type: int,
    generate_redirects: bool,
) -> tuple[Counter[str], set[str]]:
    counts: Counter[str] = Counter()
    required_manifest_ids: set[str] = set()
    total = 0
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
        summary = lookup.get((item_type, item_id)) or make_summary(item_type, item_id, source, manifest_ids)
        if summary.has_manifest:
            required_manifest_ids.add(item_manifest_id(item_type, item_id))
        html_text = render_item_page(item_type, item_id, source, summary, manifest_ids, lookup)
        item_dir = output / item_type / item_id / "full"
        write_text(item_dir / "index.html", html_text)
        if generate_redirects:
            write_redirect_page(output / item_type / item_id / "intro" / "index.html", summary.url)
            write_redirect_page(output / item_type / item_id / "allphotos" / "index.html", summary.url)
        counts[item_type] += 1
        total += 1
    return counts, required_manifest_ids


def write_manifests(
    output: Path,
    es_archive: Path,
    iiif_member: str,
    base_url: str,
    manifest_limit: int,
    required_manifest_ids: set[str],
) -> int:
    manifest_dir = output / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    sample_count = 0
    pending_required = set(required_manifest_ids)
    for doc in iter_es_docs(es_archive, iiif_member):
        manifest_id = str(doc.get("_id") or (doc.get("_source") or {}).get("id") or "").strip()
        manifest = ((doc.get("_source") or {}).get("manifest"))
        if not manifest_id or not isinstance(manifest, dict):
            continue
        sample_slot = not manifest_limit or sample_count < manifest_limit
        required = manifest_id in pending_required
        if not sample_slot and not required:
            continue
        rewritten = rewrite_manifest(copy.deepcopy(manifest), manifest_id, base_url)
        write_text(manifest_dir / f"{manifest_id}.json", json.dumps(rewritten, ensure_ascii=False, indent=2))
        count += 1
        if sample_slot and manifest_limit:
            sample_count += 1
        pending_required.discard(manifest_id)
        if manifest_limit and sample_count >= manifest_limit and not pending_required:
            break
    if pending_required:
        missing = ", ".join(sorted(pending_required)[:10])
        extra = "..." if len(pending_required) > 10 else ""
        print(f"WARNING: {len(pending_required):,} required manifests were not found: {missing}{extra}", file=sys.stderr)
    return count


def write_404(output: Path) -> None:
    body = content_page_body(
        "Page Not Found",
        "The requested page is not available on the static Digital Giza site.",
        ['Try <a href="/search/">searching the public catalog</a> or returning to the <a href="/">home page</a>.'],
    )
    write_text(output / "404.html", render_page("Page Not Found", body, index_body=False))


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
    description_html = render_description(source)
    details_html = render_details(source)
    related_html = render_related_items(source.get("relateditems"), lookup)
    filters_html = render_pagefind_filters(summary)
    extra_head = render_pagefind_meta(summary)
    extra_scripts = ""
    if has_manifest:
        extra_scripts = render_mirador_script(manifest_url(manifest_id))

    body = [page_header(title, source.get("sitename"), bg="1")]
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
    body.append("</section>")
    body.append('<aside class="large-4 columns content-col-secondary">')
    body.append('<div class="feature-block secondary"><h5>Catalog Record</h5><dl class="dl-slim">')
    body.append(f'<dt>Type</dt><dd>{html.escape(type_label(item_type))}</dd>')
    body.append(f'<dt>ID</dt><dd>{html.escape(item_id)}</dd>')
    if source.get("number"):
        body.append(f'<dt>Number</dt><dd>{escape_text(source.get("number"))}</dd>')
    if has_manifest:
        body.append(f'<dt>IIIF</dt><dd><a href="{manifest_url(manifest_id)}">Manifest JSON</a></dd>')
    if summary.has_pdf and source.get("pdf"):
        body.append(f'<dt>PDF</dt><dd><a href="{html.escape(plain_text(source.get("pdf")), quote=True)}">Download PDF</a></dd>')
    body.append('</dl><p><a href="/search/">Search the catalog</a></p></div>')
    body.append("</aside></div>")

    return render_page(
        title,
        "\n".join(body),
        description=truncate_text(summary.description or title, 160),
        body_class="section-explore-body header-full mode-full",
        extra_head=extra_head,
        extra_scripts=extra_scripts,
    )


def render_primary_media(item_type: str, item_id: str, source: dict[str, Any], has_manifest: bool) -> str:
    primary = source.get("primarydisplay") if isinstance(source.get("primarydisplay"), dict) else {}
    main = plain_text(primary.get("main"))
    thumb = plain_text(primary.get("thumbnail"))
    caption = plain_text(primary.get("displaytext"))
    pdf = plain_text(source.get("pdf"))
    manifest_id = item_manifest_id(item_type, item_id)
    parts = ['<div class="item__featured-image">']

    if item_type == "3dmodels" and main:
        parts.append(f'<iframe allowfullscreen height="500" width="100%" src="{html.escape(main, quote=True)}"></iframe>')
    elif item_type == "videos" and main:
        poster = f' poster="{html.escape(thumb, quote=True)}"' if thumb else ""
        parts.append(f'<video width="100%" controls{poster}><source src="{html.escape(main, quote=True)}">Your browser does not support the video tag.</video>')
        parts.append(f'<p><a href="{html.escape(main, quote=True)}">Open video source</a></p>')
    elif item_type == "pubdocs" and pdf:
        if main:
            parts.append(f'<a href="{html.escape(pdf, quote=True)}"><img src="{html.escape(main, quote=True)}" alt=""></a>')
        parts.append(f'<p><a class="button" href="{html.escape(pdf, quote=True)}">Download PDF</a></p>')
    elif has_manifest:
        parts.append(f'<div style="height:500px;width:100%;"><div id="mirador" data-manifest="{html.escape(manifest_url(manifest_id), quote=True)}"></div></div>')
        parts.append(f'<p><a href="{manifest_url(manifest_id)}">Open IIIF manifest</a></p>')
    elif main:
        if looks_like_image(main):
            parts.append(f'<img src="{html.escape(main, quote=True)}" alt="">')
        else:
            label = "Open media"
            parts.append(f'<p><a class="button" href="{html.escape(main, quote=True)}">{label}</a></p>')
    elif pdf:
        parts.append(f'<p><a class="button" href="{html.escape(pdf, quote=True)}">Download PDF</a></p>')
    elif thumb:
        parts.append(f'<img src="{html.escape(thumb, quote=True)}" alt="">')
    else:
        return ""

    if caption:
        parts.append(f'<p class="item__featured-image__caption">{html.escape(caption)}</p>')
    parts.append("</div>")
    return "\n".join(parts)


def render_description(source: dict[str, Any]) -> str:
    diary = source.get("diarytranscription")
    if has_value(diary):
        return f'<div class="item__overview text-alt"><h5>Diary Transcription:</h5>{text_to_paragraphs(diary)}</div>'
    description = source.get("description")
    if has_value(description):
        return f'<div class="item__overview"><div class="lead text-alt">{text_to_paragraphs(description)}</div></div>'
    return ""


def render_details(source: dict[str, Any]) -> str:
    rows = []
    for label, key, mode in DETAIL_FIELDS:
        if not has_value(source.get(key)):
            continue
        if mode == "safe_html":
            value = sanitize_html_field(source.get(key))
        else:
            value = text_to_inline_html(source.get(key))
        if value:
            rows.append(f"<dt>{html.escape(label)}</dt><dd>{value}</dd>")
    if not rows:
        return "<p>No additional details available.</p>"
    return '<div class="feature-block__body"><dl class="dl-slim">' + "\n".join(rows) + "</dl></div>"


def render_related_items(related: Any, lookup: dict[tuple[str, str], ItemSummary]) -> str:
    if not isinstance(related, dict):
        return ""
    sections = []
    keys = sorted(related.keys(), key=lambda key: RELATED_ORDER.index(key) if key in RELATED_ORDER else len(RELATED_ORDER))
    for key in keys:
        items = related.get(key)
        if not isinstance(items, list) or not items:
            continue
        related_type = RELATED_TYPE_ALIASES.get(key, key)
        label = RELATED_SECTION_LABELS.get(related_type, RELATED_SECTION_LABELS.get(key, type_label(key)))
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
        body = '<div class="feature-block__body" data-pagefind-ignore><ul class="feature-block__list multicol-2 thumbsize-sm thumbs-square static-site-related">' + "\n".join(cards) + "</ul></div>"
        sections.append(feature_block(f"{label} <span class=\"badge\">{len(cards):,}</span>", body, icon="list"))
    return "\n".join(sections)


def render_summary_card(summary: ItemSummary) -> str:
    thumb = f'<div class="thumbnail"><a href="{summary.url}"><img src="{html.escape(summary.thumbnail, quote=True)}" alt=""></a></div>' if summary.thumbnail else ""
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
        '</div></div></li>'
    )


def render_related_card(item: dict[str, Any], item_type: str) -> str:
    item_id = plain_text(item.get("id"))
    title = first_text(item, "displaytext", "title", "displayname", "name", "number") or f"{type_label(item_type)} {item_id}"
    thumb = plain_text(item.get("thumbnail"))
    url = item_url(item_type, item_id) if item_type in TYPE_LABELS and item_id else ""
    linked_title = f'<a href="{url}">{html.escape(title)}</a>' if url else html.escape(title)
    thumb_html = f'<div class="thumbnail"><a href="{url}"><img src="{html.escape(thumb, quote=True)}" alt=""></a></div>' if thumb and url else ""
    meta = first_text(item, "sitename", "number", "displaydate", "role")
    return (
        '<li><div class="media-object list-item list-item-thumbnail">'
        f'<div class="media-object-section">{thumb_html}</div>'
        f'<div class="media-object-section"><p class="media-object-title">{linked_title}</p><p class="static-site-meta">{html.escape(meta)}</p></div>'
        '</div></li>'
    )


def render_pagefind_meta(summary: ItemSummary) -> str:
    values = {
        "title": summary.title,
        "type": type_label(summary.type),
        "thumbnail": summary.thumbnail,
    }
    return "\n".join(
        f'<meta data-pagefind-meta="{html.escape(key)}" content="{html.escape(value, quote=True)}">'
        for key, value in values.items()
        if value
    )


def render_pagefind_filters(summary: ItemSummary) -> str:
    filters = [
        ("type", type_label(summary.type)),
        ("department", summary.department),
        ("classification", summary.classification),
        ("material", summary.material),
        ("period", summary.period),
        ("site_name", summary.site_name),
        ("has_image", "Yes" if summary.has_image else "No"),
        ("has_manifest", "Yes" if summary.has_manifest else "No"),
        ("has_pdf", "Yes" if summary.has_pdf else "No"),
    ]
    spans = [
        f'<span data-pagefind-filter="{html.escape(name)}">{html.escape(value)}</span>'
        for name, value in filters
        if value
    ]
    return '<div class="static-site-pagefind-filters" aria-hidden="true">' + "".join(spans) + "</div>"


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


def render_page(
    title: str,
    body: str,
    *,
    description: str = "",
    body_class: str = "",
    extra_head: str = "",
    extra_scripts: str = "",
    index_body: bool = True,
) -> str:
    main_attr = 'data-pagefind-body' if index_body else 'data-pagefind-ignore'
    escaped_title = html.escape(title)
    escaped_description = html.escape(description, quote=True)
    return f"""<!doctype html>
<html class="no-js" lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Digital Giza | {escaped_title}</title>
  <meta name="description" content="{escaped_description}">
  <link rel="shortcut icon" href="/static/images/favicon.ico">
  <link href="https://fonts.googleapis.com/css?family=Montserrat:400,500,600" rel="stylesheet">
  <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.6.3/css/all.css" integrity="sha384-UHRtZLI+pbxtHCWp1t77Bi1L4ZtiqrqD80Kn4Z8NTSRyMA2Fd33n5dQ8lWUE00s/" crossorigin="anonymous">
  <link rel="stylesheet" href="/static/css/app.css">
  <link rel="stylesheet" href="/static/css/project.css">
  <link rel="stylesheet" href="/static/static-site/static-site.css">
  {extra_head}
</head>
<body class="{html.escape(body_class, quote=True)}">
  {site_header()}
  <main id="content" {main_attr}>
{body}
  </main>
  {site_footer()}
  <script src="/static/js/app.js"></script>
  <script src="/static/js/giza.js"></script>
  <script src="/static/static-site/static-site.js"></script>
  {extra_scripts}
</body>
</html>
"""


def site_header() -> str:
    return """
<a id="skippy" class="sr-only sr-only-focusable" href="#content">
  <div class="top-bar-container"><span class="skiplink-text">Skip to main content</span></div>
</a>
<div data-sticky-container>
  <div data-sticky data-options="marginTop:0;" style="width:100%; z-index:1003;">
    <div class="top-bar-container" style="width:100%;">
      <div class="row row-padded">
        <div class="title-bar" data-responsive-toggle="main-menu" data-hide-for="medium">
          <button class="icon-bars icon-padded title-bar-title" type="button" data-toggle>Menu</button>
        </div>
        <div class="top-bar" id="main-menu">
          <div class="top-bar-left hide-for-small-only"><a href="/"><img src="/static/images/navlogo.png" alt="Digital Giza at Harvard University. Click for home."></a></div>
          <div class="top-bar-left nav-menu-primary">
            <ul class="vertical medium-horizontal menu" data-responsive-menu="drilldown medium-dropdown" data-alignment="left">
              <li><a href="/library/">Library</a></li>
              <li><a href="/gizaatschool/">Giza @ School</a></li>
              <li><a href="/giza3d/">Giza 3D</a></li>
              <li><a href="/collections/">My Giza</a>
                <ul class="vertical menu">
                  <li><a href="/collections/">Browse Collections</a></li>
                </ul>
              </li>
              <li><a href="/gizaintro/">About</a>
                <ul class="vertical menu">
                  <li><a href="/gizaintro/">Introduction to Giza</a></li>
                  <li><a href="/about/">What is the Giza Project?</a></li>
                  <li><a href="/archaeology/">Archaeology at Giza</a></li>
                </ul>
              </li>
              <li><a href="https://community.alumni.harvard.edu/give/34086571">Donate</a></li>
              <li><form id="search-form" action="/search-results/"><input type="text" id="inputSimpleSearch" name="q" placeholder="Search"><button class="icon-search button" type="submit"><span class="show-for-sr">Search</span></button></form></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
""".strip()


def site_footer() -> str:
    return """
<nav class="footer">
  <div class="row">
    <section class="large-6 columns">
      <div class="row">
        <div class="medium-4 columns"><h6><a class="heading-link" href="/library/">Library</a></h6></div>
        <div class="medium-4 columns"><h6><a class="heading-link" href="/gizaatschool/">Giza @ School</a></h6><ul class="footer-menu-list"><li><a href="/lessons/">Lesson Topics</a></li><li><a href="/commontopics/">People and Places of Giza</a></li><li><a href="/faq/">Glossary and FAQ</a></li><li><a href="/videos/">Video Library</a></li></ul></div>
        <div class="medium-4 columns"><h6><a class="heading-link" href="/giza3d/">Giza 3D</a></h6><ul class="footer-menu-list vertical menu accordion-slim" data-accordion-menu><li><a href="#0" class="accordion-toggletext" data-closed-text="Show models" data-open-text="Hide models">Show models</a><ul class="no-bullet menu vertical nested"><li><a href="/giza3d/">Giza Plateau</a></li><li><a href="/giza3d/?mode=GuidedTour&amp;guidedTourId=neZZCDSf5">A Walking Tour of the Giza Plateau</a></li><li><a href="/giza3d/?mode=GuidedTour&amp;guidedTourId=neZZCDSf5">Khafre Pyramid and Temples</a></li><li><a href="/giza3d/?mode=GuidedTour&amp;guidedTourId=neZZCDSf5">Khufu Pyramid</a></li><li><a href="/giza3d/?mode=GuidedTour&amp;guidedTourId=neZZCDSf5">Menkaure Pyramid</a></li><li><a href="/giza3d/?mode=GuidedTour&amp;guidedTourId=neZZCDSf5">Great Sphinx</a></li><li><a href="/giza3d/?mode=GuidedTour&amp;guidedTourId=nGQi15GpZ">Great Sphinx Interactive Video</a></li></ul></li></ul></div>
      </div>
    </section>
    <section class="large-6 columns">
      <div class="row">
        <div class="medium-4 columns"><h6><a class="heading-link" href="/collections/">My Giza</a></h6><ul class="footer-menu-list"><li><a href="/collections/">Browse Collections</a></li></ul></div>
        <div class="medium-4 columns"><h6><a class="heading-link" href="/gizaintro/">About the Project</a></h6><ul class="footer-menu-list"><li><a href="/gizaintro/">Introduction to Giza</a></li><li><a href="/about/">What is the Giza Project?</a></li><li><a href="/archaeology/">Archaeology at Giza</a></li></ul></div>
        <div class="medium-4 columns"><h6><a class="heading-link" href="https://community.alumni.harvard.edu/give/34086571">Donate</a></h6><h6><a class="heading-link" href="/search/">Search</a></h6><h6><a class="heading-link" href="/contact/">Contact</a></h6></div>
      </div>
    </section>
  </div>
</nav>
<footer class="legal-social" data-equalizer data-equalize-on="medium">
  <div class="row">
    <div class="large-6 large-push-6 columns text-md-right" data-equalizer-watch>
      <img src="/static/images/footerlogo.png" alt="Giza Project at Harvard University" class="image-spacer" style="max-width:200px;">
      <img src="/static/images/neh_logo_web.svg" alt="National Endowment for the Humanities" class="image-spacer" style="margin-top:-0.2em; max-width:200px;">
      <p class="medium-9 columns text-smaller text-muted text-center">Digital Giza has been made possible in part by the <a href="http://www.neh.gov/">National Endowment for the Humanities</a>: Exploring the human endeavor</p>
    </div>
    <div class="large-6 large-pull-6 columns" data-equalizer-watch><p class="text-smaller text-muted" style="margin-top:0.25em;">&copy; 2026 Giza Project at Harvard University. <br> All rights reserved.</p></div>
  </div>
</footer>
""".strip()


def page_header(title: str, subtitle: Any = "", bg: str = "1") -> str:
    subtitle_text = plain_text(subtitle)
    subtitle_html = f'<h3 class="page-header__meta">{html.escape(subtitle_text)}</h3>' if subtitle_text else ""
    return f'<div class="page-header header-bg-{html.escape(str(bg))}"><div class="row title"><header class="large-12 columns"><h1>{html.escape(plain_text(title))}</h1>{subtitle_html}</header></div></div>'


def feature_block(title: str, content: str, icon: str = "info-circle") -> str:
    return (
        '<section class="feature-block collapsible">'
        '<div class="feature-block__header">'
        f'<h3 class="feature-block__title"><i class="icon-{html.escape(icon)} icon-padded"></i> {title}</h3>'
        '</div>'
        f"{content}"
        "</section>"
    )


def make_summary(item_type: str, item_id: str, source: dict[str, Any], manifest_ids: set[str]) -> ItemSummary:
    primary = source.get("primarydisplay") if isinstance(source.get("primarydisplay"), dict) else {}
    manifest_id = item_manifest_id(item_type, item_id)
    has_manifest = bool(primary.get("has_manifest")) or manifest_id in manifest_ids
    thumbnail = plain_text(primary.get("thumbnail")) or plain_text(source.get("thumbnail"))
    main = plain_text(primary.get("main"))
    has_image = bool(thumbnail or (main and looks_like_image(main)))
    return ItemSummary(
        type=item_type,
        id=item_id,
        title=item_title(item_type, item_id, source),
        url=item_url(item_type, item_id),
        thumbnail=thumbnail,
        description=plain_text(source.get("description") or source.get("notes") or source.get("remarks")),
        department=plain_text(source.get("department")),
        classification=plain_text(source.get("classificationtext") or source.get("classification")),
        material=plain_text(source.get("medium")),
        period=plain_text(source.get("period")),
        site_name=plain_text(source.get("sitename")),
        has_image=has_image,
        has_manifest=has_manifest,
        has_pdf=bool(plain_text(source.get("pdf"))),
    )


def item_title(item_type: str, item_id: str, source: dict[str, Any]) -> str:
    title = first_text(source, "displaytext", "title", "displayname", "sitename", "number")
    return title or f"{type_label(item_type)} {item_id}"


def get_doc_id(doc: dict[str, Any]) -> str:
    return plain_text(doc.get("_id") or (doc.get("_source") or {}).get("id"))


def item_url(item_type: str, item_id: str) -> str:
    return f"/{item_type}/{item_id}/full/"


def item_manifest_id(item_type: str, item_id: str) -> str:
    return f"{item_type}-{item_id}"


def manifest_url(manifest_id: str) -> str:
    return f"/manifests/{manifest_id}.json"


def collection_slug(collection: dict[str, Any]) -> str:
    return slug_or_fallback(collection.get("slug"), collection.get("title"), f"collection-{collection.get('pk')}")


def lesson_slug(lesson: dict[str, Any]) -> str:
    return slug_or_fallback(lesson.get("slug"), lesson.get("title"), f"lesson-{lesson.get('pk')}")


def slug_or_fallback(*values: Any) -> str:
    for value in values:
        text = plain_text(value)
        if text:
            slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            if slug:
                return slug
    return "item"


def type_label(item_type: str) -> str:
    return TYPE_LABELS.get(item_type, item_type.replace("_", " ").replace("-", " ").title())


def rewrite_manifest(manifest: dict[str, Any], manifest_id: str, base_url: str) -> dict[str, Any]:
    manifest["@id"] = absolute_url(base_url, manifest_url(manifest_id))
    rewrite_iiif_refs(manifest, manifest_id, base_url)
    manifest["@id"] = absolute_url(base_url, manifest_url(manifest_id))
    return manifest


def rewrite_iiif_refs(value: Any, manifest_id: str, base_url: str) -> None:
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if key in {"@id", "on", "startCanvas"} and isinstance(child, str):
                value[key] = rewrite_iiif_ref(child, manifest_id, base_url, is_top_id=False)
            else:
                rewrite_iiif_refs(child, manifest_id, base_url)
    elif isinstance(value, list):
        for child in value:
            rewrite_iiif_refs(child, manifest_id, base_url)


def rewrite_iiif_ref(ref: str, manifest_id: str, base_url: str, *, is_top_id: bool) -> str:
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


def absolute_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def write_redirect_page(path: Path, target: str) -> None:
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={html.escape(target, quote=True)}"><link rel="canonical" href="{html.escape(target, quote=True)}"><title>Redirecting</title></head>
<body><p>Redirecting to <a href="{html.escape(target, quote=True)}">{html.escape(target)}</a>.</p><script>window.location.replace({json.dumps(target)});</script></body></html>
"""
    write_text(path, body)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def is_safe_url(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    parsed = urlparse(value)
    if parsed.scheme:
        return parsed.scheme in {"http", "https", "mailto"}
    return value.startswith(("/", "#")) or ":" not in value


def looks_like_image(url: str) -> bool:
    clean = url.split("?", 1)[0].lower()
    return clean.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")) or "nrs.harvard.edu/urn" in clean


def has_value(value: Any) -> bool:
    return bool(plain_text(value))


def first_text(mapping: dict[str, Any], *keys: str) -> str:
    for key in keys:
        text = plain_text(mapping.get(key))
        if text:
            return text
    return ""


def plain_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, dict):
        for key in ("displaytext", "name", "title", "sitetype", "altnum", "description", "value", "label"):
            text = plain_text(value.get(key))
            if text:
                return text
        parts = [f"{key}: {plain_text(child)}" for key, child in value.items() if plain_text(child)]
        return "; ".join(parts)
    if isinstance(value, list):
        seen = set()
        parts = []
        for child in value:
            text = plain_text(child)
            if text and text not in seen:
                parts.append(text)
                seen.add(text)
        return "; ".join(parts)
    return str(value).strip()


def escape_text(value: Any) -> str:
    return html.escape(plain_text(value))


def text_to_inline_html(value: Any) -> str:
    text = plain_text(value)
    if not text:
        return ""
    return html.escape(text).replace("\n", "<br>")


def text_to_paragraphs(value: Any) -> str:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return ""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", raw) if part.strip()]
    if not paragraphs:
        paragraphs = [raw]
    return "".join(f"<p>{html.escape(part).replace(chr(10), '<br>')}</p>" for part in paragraphs)


def sanitize_html(value: Any) -> str:
    parser = SafeHTML()
    parser.feed(str(value or ""))
    parser.close()
    return parser.rendered()


def sanitize_html_field(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if "<" not in raw and ">" not in raw:
        return text_to_paragraphs(raw)
    return sanitize_html(raw)


def truncate_text(value: str, limit: int) -> str:
    text = plain_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
