"""Deterministic synthetic static-site generator for Dredge stress testing.

Produces a large, realistic static site plus a matching ``dredge.config.json`` so
the compiler and browser runtime can be exercised against a full-size database.

The generator is fully deterministic for a given ``(count, seed)`` pair so stress
runs and known-answer correctness checks are reproducible.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from html import escape
from pathlib import Path

# Vocabulary chosen to produce a mix of common and rare terms. The first few
# tokens recur frequently; later tokens appear rarely, which exposes skewed FTS
# postings lists and bad query plans during stress testing.
COMMON_TERMS = (
    "ancient",
    "object",
    "collection",
    "record",
    "image",
    "site",
    "catalog",
    "history",
    "stone",
    "temple",
)
RARE_TERMS = (
    "sarcophagus",
    "hieroglyph",
    "obelisk",
    "cartouche",
    "amphora",
    "ostracon",
    "stela",
    "faience",
    "scarab",
    "papyrus",
    "alabaster",
    "limestone",
    "granite",
    "basalt",
    "diorite",
)
TITLE_NOUNS = (
    "Tomb",
    "Temple",
    "Statue",
    "Relief",
    "Stela",
    "Vessel",
    "Coffin",
    "Mask",
    "Amulet",
    "Tablet",
)
TITLE_ADJECTIVES = (
    "Golden",
    "Ancient",
    "Royal",
    "Sacred",
    "Lost",
    "Hidden",
    "Great",
    "Carved",
    "Painted",
    "Broken",
)

CATEGORIES = ("object", "site", "media", "publication", "constituent")
TAG_POOL = (
    "burial",
    "ritual",
    "royal",
    "domestic",
    "funerary",
    "religious",
    "military",
    "trade",
    "art",
    "architecture",
    "inscription",
    "pottery",
    "jewelry",
    "tooling",
)
MIN_YEAR = 1900
MAX_YEAR = 2024

# Controllable-selectivity token buckets injected into every document body so
# benchmarks can measure realistic query selectivity instead of only broad
# (near-100%) term matches. For a corpus of ``count`` documents:
#   uid<id>          -> exactly 1 matching document (point lookup)
#   grp<id%GROUPS>   -> ~count / GROUP_BUCKETS matching documents (selective)
#   cohort<id%COHS>  -> ~count / COHORT_BUCKETS matching documents (moderate)
GROUP_BUCKETS = 1_000
COHORT_BUCKETS = 50


@dataclass(frozen=True)
class GeneratedSite:
    source_dir: Path
    output_dir: Path
    config_path: Path
    page_count: int
    seed: int


def _title(rng: random.Random, doc_id: int) -> str:
    adjective = rng.choice(TITLE_ADJECTIVES)
    noun = rng.choice(TITLE_NOUNS)
    return f"{adjective} {noun} {doc_id}"


def _body(rng: random.Random, doc_id: int) -> str:
    sentences: list[str] = []
    sentence_count = rng.randint(4, 9)
    for _ in range(sentence_count):
        # Skew toward common terms; occasionally sprinkle a rare term.
        word_count = rng.randint(8, 18)
        words: list[str] = []
        for _ in range(word_count):
            if rng.random() < 0.15:
                words.append(rng.choice(RARE_TERMS))
            else:
                words.append(rng.choice(COMMON_TERMS))
        sentence = " ".join(words).capitalize() + "."
        sentences.append(sentence)
    # Deterministic selectivity tokens (see GROUP_BUCKETS / COHORT_BUCKETS).
    selectivity = (
        f"uid{doc_id} grp{doc_id % GROUP_BUCKETS} cohort{doc_id % COHORT_BUCKETS}."
    )
    sentences.append(selectivity)
    return " ".join(sentences)


def _category(rng: random.Random) -> str:
    # Low-cardinality, skewed distribution: "object" dominates.
    weights = (0.55, 0.2, 0.15, 0.06, 0.04)
    return rng.choices(CATEGORIES, weights=weights, k=1)[0]


def _tags(rng: random.Random) -> tuple[str, ...]:
    count = rng.randint(0, 4)
    if count == 0:
        return ()
    return tuple(sorted(set(rng.sample(TAG_POOL, count))))


def _year(rng: random.Random) -> int:
    # Skew recent years more heavily.
    span = MAX_YEAR - MIN_YEAR
    offset = int((rng.random() ** 2) * span)
    return MAX_YEAR - offset


def _render_page(
    *,
    doc_id: int,
    title: str,
    description: str,
    body: str,
    category: str,
    year: int,
    rating: float,
    featured: bool,
    published: str,
    tags: tuple[str, ...],
) -> str:
    tag_meta = "\n    ".join(
        f'<meta property="article:tag" content="{escape(tag, quote=True)}">'
        for tag in tags
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description, quote=True)}">
    {tag_meta}
  </head>
  <body>
    <main
      data-dredge-category="{escape(category, quote=True)}"
      data-dredge-year="{year}"
      data-dredge-rating="{rating:.2f}"
      data-dredge-featured="{"true" if featured else "false"}"
      data-dredge-published="{published}"
    >
      <h1>{escape(title)}</h1>
      <p>{escape(body)}</p>
    </main>
  </body>
</html>
"""


def _config(source_dir: Path, output_dir: Path) -> dict[str, object]:
    return {
        "source_dir": source_dir.name,
        "output_dir": output_dir.name,
        "base_url": "/",
        "include": ["**/*.html"],
        "exclude": [],
        "selectors": {
            "title": "title, h1",
            "body": "main",
            "description": "meta[name='description']@content",
        },
        "facets": {
            "category": {
                "type": "string",
                "source": "data-dredge-category",
                "required": True,
            },
            "year": {"type": "integer", "source": "data-dredge-year"},
            "rating": {"type": "number", "source": "data-dredge-rating"},
            "featured": {"type": "boolean", "source": "data-dredge-featured"},
            "published": {"type": "date", "source": "data-dredge-published"},
            "tags": {
                "type": "string_array",
                "source": "meta[property='article:tag']@content",
            },
        },
        "result_fields": ["title", "url", "description", "category", "year", "rating"],
        "composite_indices": [["category", "year"]],
    }


def generate_site(
    root: Path,
    *,
    count: int,
    seed: int = 1,
    shard_size: int = 1_000,
) -> GeneratedSite:
    """Generate a deterministic synthetic site under ``root``.

    Files are sharded into subdirectories (``pages/<shard>/page-<id>.html``) so a
    single directory never holds an unreasonable number of entries at large
    ``count`` values.
    """

    if count < 1:
        raise ValueError("count must be >= 1")

    source_dir = root / "site"
    output_dir = root / "search"
    source_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    for doc_id in range(1, count + 1):
        shard = (doc_id - 1) // shard_size
        page_dir = source_dir / "pages" / f"{shard:05d}"
        page_dir.mkdir(parents=True, exist_ok=True)

        title = _title(rng, doc_id)
        category = _category(rng)
        year = _year(rng)
        rating = round(rng.uniform(0.0, 5.0), 2)
        featured = rng.random() < 0.2
        published_year = rng.randint(MIN_YEAR, MAX_YEAR)
        published_month = rng.randint(1, 12)
        published_day = rng.randint(1, 28)
        published = f"{published_year:04d}-{published_month:02d}-{published_day:02d}"
        tags = _tags(rng)
        description = f"{title}: a {category} from {year}."
        body = _body(rng, doc_id)

        html = _render_page(
            doc_id=doc_id,
            title=title,
            description=description,
            body=body,
            category=category,
            year=year,
            rating=rating,
            featured=featured,
            published=published,
            tags=tags,
        )
        (page_dir / f"page-{doc_id:07d}.html").write_text(html, encoding="utf-8")

    config_path = root / "dredge.config.json"
    config_path.write_text(
        json.dumps(_config(source_dir, output_dir), indent=2) + "\n", encoding="utf-8"
    )

    return GeneratedSite(
        source_dir=source_dir,
        output_dir=output_dir,
        config_path=config_path,
        page_count=count,
        seed=seed,
    )
