from __future__ import annotations

from dataclasses import dataclass


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
    search_identifier: str
    has_image: bool
    has_manifest: bool
    has_pdf: bool


@dataclass(frozen=True)
class StaticTemplatePage:
    slug: str
    template: str
    title: str
    description: str
