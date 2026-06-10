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

SEARCH_CATEGORY_ORDER = [
    ("photos", "Photos"),
    ("objects", "Objects"),
    ("unpubdocs", "Unpublished Documents"),
    ("mapsandplans", "Maps and Plans"),
    ("diarypages", "Diary Pages"),
    ("drawings", "Drawings"),
    ("sites", "Tombs and Monuments"),
    ("ancientpeople", "Ancient People"),
    ("videos", "Videos"),
    ("modernpeople", "Modern People"),
    ("pubdocs", "Published Documents"),
    ("institutions", "Institutions"),
    ("3dmodels", "3D Models"),
    ("groups", "Groups"),
    ("animals", "Animals"),
]

SEARCH_CATEGORY_LABELS = dict(SEARCH_CATEGORY_ORDER)

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
:root {
  --pf-text: #4a4a4a;
  --pf-text-secondary: #666;
  --pf-text-muted: #777;
  --pf-background: #fff;
  --pf-border: #c9c1b8;
  --pf-border-focus: #857158;
  --pf-hover: #f4f0eb;
  --pf-mark: #572700;
  --pf-outline-focus: #2d6f96;
  --pf-font: Montserrat, Helvetica, Arial, sans-serif;
  --pf-input-height: 2.5rem;
  --pf-input-font-size: 16px;
  --pf-summary-font-size: 1rem;
  --pf-border-radius: 0;
}
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
.static-site-search-page {
  margin-top: 2.25rem;
}
.static-site-search-controls {
  margin-bottom: 1.25rem;
}
.static-site-search-controls pagefind-input {
  display: block;
  margin-bottom: 0.5rem;
}
.static-site-advanced-search {
  border-top: 1px solid #ded7cf;
  margin-bottom: 1.5rem;
  padding-top: 1rem;
}
.static-site-advanced-search h3 {
  margin-top: 0;
}
.static-site-advanced-search fieldset {
  border: 0;
  margin: 0 0 1rem;
  padding: 0;
}
.static-site-advanced-search legend {
  color: #4a4a4a;
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}
.static-site-advanced-search .feature-block.tertiary {
  padding: 0.75rem 0.85rem;
}
.static-site-advanced-search input[type="text"] {
  margin-bottom: 0.85rem;
}
.static-site-search-results .static-site-search-status {
  margin-bottom: 1.35rem;
}
.static-site-search-results .static-site-search-status h3 {
  color: #650516;
  font-size: 1.45rem;
  font-weight: 700;
  line-height: 1.2;
  margin-top: 0.15rem;
}
.static-site-search-results .media-object-holder {
  display: grid;
  gap: 0;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 0.4rem;
}
.static-site-search-results .search-result {
  border-right: solid 1px #ccc;
  border-top: solid 1px #ccc;
  display: flex;
  gap: 1rem;
  margin-bottom: 0;
  min-height: 164px;
  padding: 1.15rem 1.2rem 1.15rem 1.35rem;
}
.static-site-search-results .search-result:nth-child(3n) {
  border-right: 0;
}
.static-site-search-results .media-object-section:first-child {
  flex: 0 0 80px;
}
.static-site-search-results .media-object-section:last-child {
  flex: 1 1 auto;
  min-width: 0;
}
.static-site-search-results .thumbnail {
  align-items: center;
  background: #f4f0eb;
  border: 1px solid #d8d0c7;
  box-sizing: border-box;
  display: flex;
  height: 80px;
  justify-content: center;
  margin-bottom: 0;
  overflow: hidden;
  padding: 4px;
  width: 80px;
}
.static-site-search-results .thumbnail img {
  height: 100%;
  object-fit: cover;
  width: 100%;
}
.static-site-search-results .thumbnail.no-img img {
  height: 44px;
  object-fit: contain;
  opacity: 0.62;
  width: 44px;
}
.static-site-search-results .media-object-title {
  font-weight: bold;
  line-height: 1.35;
  margin-bottom: 0.2rem;
}
.static-site-search-results .media-object-title a {
  color: #005eb8;
}
.static-site-search-results .media-object-title a:hover,
.static-site-search-results .media-object-title a:focus {
  color: #572700;
}
.static-site-search-results .subheader {
  color: #858585;
  font-size: 1rem;
  line-height: 1.35;
  list-style: none;
  margin: 0;
}
.static-site-search-results .subheader li {
  display: block;
}
.static-site-search-results .pagination {
  margin-top: 1.5rem;
}
.static-site-search-results .pagination a,
.static-site-search-results .pagination .current,
.static-site-search-results .pagination .disabled {
  margin-bottom: 0.25rem;
}
.search-facet-section {
  border-top: solid 1px #ded7cf;
  display: block;
  margin-top: 1.15rem;
  padding-top: 1.15rem;
}
.search-facet-title {
  color: #8a817a;
  font-family: Montserrat, Helvetica, Arial, sans-serif;
  font-size: 1rem;
  font-weight: normal;
  margin-bottom: 0;
  text-transform: none;
}
.search-facet-list {
  list-style: none;
  margin-left: 0;
}
.search-facet-item {
  line-height: 1.35;
  margin-bottom: 0.4rem;
}
.search-facet-item a,
.search-facet-item label {
  color: #005eb8;
}
.static-site-search-page .feature-block.secondary {
  background: #d7d2cb;
  border-radius: 4px;
  padding: 1.55rem 1.6rem;
}
.static-site-search-page .feature-block.secondary h5 {
  color: #650516;
  font-size: 1.35rem;
  font-weight: 700;
  margin-bottom: 1rem;
}
.search-facet-item.is-active a,
.search-facet-item.is-active label,
.search-facet-item input:checked + label {
  color: #857158;
  font-weight: bold;
}
.search-facet-item.is-active a:after {
  color: #7b2d20;
  content: "\\00d7";
  display: inline-block;
  font-size: 110%;
  font-weight: normal;
  margin-left: 0.3em;
  vertical-align: baseline;
}
.search-facet-item.is-active a:hover,
.search-facet-item.is-active a:active,
.search-facet-item.is-active a:focus,
.search-facet-item.is-active a:hover:after,
.search-facet-item.is-active a:active:after,
.search-facet-item.is-active a:focus:after {
  color: #cc4b37;
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
@media (max-width: 1024px) {
  .static-site-search-results .media-object-holder {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .static-site-search-results .search-result:nth-child(3n) {
    border-right: solid 1px #ccc;
  }
  .static-site-search-results .search-result:nth-child(2n) {
    border-right: 0;
  }
}
@media (max-width: 640px) {
  .top-bar-left.hide-for-small-only {
    display: none !important;
  }
  .static-site-search-page {
    margin-top: 1rem;
  }
  .static-site-search-results .media-object-holder {
    grid-template-columns: 1fr;
  }
  .static-site-search-results .search-result {
    border-right: 0;
    gap: 0.75rem;
  }
  .static-site-search-results .search-result:nth-child(2n),
  .static-site-search-results .search-result:nth-child(3n) {
    border-right: 0;
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
  var INSTANCE_NAME = 'giza-search';
  var SEARCH_SCOPE_FILTER = 'search_scope';
  var SEARCH_SCOPE_VALUE = 'catalog';
  var DEFAULT_IMAGE = '/static/images/object1.png';
  var CATEGORY_LABELS = {
    photos: 'Photos',
    objects: 'Objects',
    unpubdocs: 'Unpublished Documents',
    mapsandplans: 'Maps and Plans',
    diarypages: 'Diary Pages',
    drawings: 'Drawings',
    sites: 'Tombs and Monuments',
    ancientpeople: 'Ancient People',
    videos: 'Videos',
    modernpeople: 'Modern People',
    pubdocs: 'Published Documents',
    institutions: 'Institutions',
    '3dmodels': '3D Models',
    groups: 'Groups',
    animals: 'Animals'
  };
  var CATEGORY_ORDER = [
    'Photos',
    'Objects',
    'Unpublished Documents',
    'Maps and Plans',
    'Diary Pages',
    'Drawings',
    'Tombs and Monuments',
    'Ancient People',
    'Videos',
    'Modern People',
    'Published Documents',
    'Institutions',
    '3D Models',
    'Groups',
    'Animals'
  ];
  var ADVANCED_FIELDS = [
    { name: 'objects_title', names: ['objects_title', 'title'], label: 'Object title or name', group: 'objects' },
    { name: 'objects_allnumbers', names: ['objects_allnumbers', 'allnumbers'], label: 'Object or ID number', group: 'objects' },
    { name: 'objects_medium', names: ['objects_medium', 'medium'], label: 'Material', group: 'objects' },
    { name: 'objects_provenance', names: ['objects_provenance', 'provenance'], label: 'Findspot', group: 'objects' },
    { name: 'objects_entrydate', names: ['objects_entrydate', 'entrydate'], label: 'Date of register entry', group: 'objects' },
    { name: 'sites_number', names: ['sites_number', 'number'], label: 'Tomb/Monument number', group: 'sites' },
    { name: 'sites_sitename', names: ['sites_sitename', 'sitename'], label: 'Tomb/Monument name', group: 'sites' },
    { name: 'sites_datevalues', names: ['sites_datevalues', 'datevalues'], label: 'Site Dates', group: 'sites' },
    { name: 'sites_people', names: ['sites_people', 'people'], label: 'People', group: 'sites' }
  ];
  var CATEGORY_LOOKUP = {};
  var CATEGORY_SLUGS_BY_LABEL = {};
  var SearchRuntime = {
    applyingUrlState: false,
    enforcingCatalog: false,
    initStarted: false,
    instance: null,
    suppressNextPageReset: false,
    suppressNextUrlSync: false
  };

  Object.keys(CATEGORY_LABELS).forEach(function (slug) {
    var label = CATEGORY_LABELS[slug];
    CATEGORY_LOOKUP[normalizeCategoryKey(slug)] = label;
    CATEGORY_LOOKUP[normalizeCategoryKey(label)] = label;
    CATEGORY_SLUGS_BY_LABEL[label] = slug;
  });
  CATEGORY_LOOKUP.tombs = CATEGORY_LABELS.sites;
  CATEGORY_LOOKUP.tomb = CATEGORY_LABELS.sites;
  CATEGORY_LOOKUP.tombsandmonuments = CATEGORY_LABELS.sites;

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function escapeAttr(value) {
    return escapeHtml(value);
  }

  function normalizeCategoryKey(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/&/g, 'and')
      .replace(/[^a-z0-9]+/g, '');
  }

  function categoryLabelFromParam(value) {
    return CATEGORY_LOOKUP[normalizeCategoryKey(value)] || '';
  }

  function categorySlugForLabel(label) {
    return CATEGORY_SLUGS_BY_LABEL[label] || '';
  }

  function firstFilledParam(params, names) {
    for (var i = 0; i < names.length; i += 1) {
      var value = params.get(names[i]);
      if (value && value.trim()) {
        return { name: names[i], value: value.trim() };
      }
    }
    return null;
  }

  function advancedRowsFromParams(params) {
    var rows = [];
    ADVANCED_FIELDS.forEach(function (field) {
      var match = firstFilledParam(params, field.names);
      if (match) {
        rows.push({
          key: field.name,
          group: field.group,
          label: field.label,
          value: match.value
        });
      }
    });
    return rows;
  }

  function inferCategoryFromRows(rows) {
    for (var i = 0; i < rows.length; i += 1) {
      if (rows[i].group === 'sites') return CATEGORY_LABELS.sites;
    }
    for (var j = 0; j < rows.length; j += 1) {
      if (rows[j].group === 'objects') return CATEGORY_LABELS.objects;
    }
    return '';
  }

  function stateFromParams(params) {
    var simple = firstFilledParam(params, ['q', 'query']);
    var rows = advancedRowsFromParams(params);
    var parts = [];
    if (simple) parts.push(simple.value);
    rows.forEach(function (row) {
      parts.push(row.value);
    });
    return {
      category: categoryLabelFromParam(params.get('category')) || inferCategoryFromRows(rows),
      rows: rows,
      simple: simple ? simple.value : '',
      term: parts.join(' ').trim()
    };
  }

  function currentParams() {
    return new URLSearchParams(window.location.search);
  }

  function parsePageParam() {
    var value = parseInt(currentParams().get('page') || '1', 10);
    return Number.isFinite(value) && value > 0 ? value : 1;
  }

  function updateUrl(params, path, replace) {
    var query = params.toString();
    var nextPath = path || window.location.pathname || '/search-results/';
    var nextUrl = nextPath + (query ? '?' + query : '');
    if (nextUrl === window.location.pathname + window.location.search) return;
    if (replace) {
      window.history.replaceState(null, '', nextUrl);
    } else {
      window.history.pushState(null, '', nextUrl);
    }
    window.dispatchEvent(new CustomEvent('giza:search-url-change'));
  }

  function urlForParams(params, path) {
    var query = params.toString();
    return (path || window.location.pathname || '/search-results/') + (query ? '?' + query : '');
  }

  function updatePageParam(page, replace) {
    var params = currentParams();
    if (page > 1) {
      params.set('page', String(page));
    } else {
      params.delete('page');
    }
    updateUrl(params, null, replace);
  }

  function cloneFilterValue(value) {
    if (Array.isArray(value)) {
      return value.map(String).filter(Boolean);
    }
    if (value == null || value === '') {
      return [];
    }
    return [String(value)];
  }

  function filtersForCategory(categoryLabel) {
    var filters = {};
    filters[SEARCH_SCOPE_FILTER] = [SEARCH_SCOPE_VALUE];
    if (categoryLabel) {
      filters.category = [categoryLabel];
    }
    return filters;
  }

  function removeAdvancedParams(params) {
    ADVANCED_FIELDS.forEach(function (field) {
      field.names.forEach(function (name) {
        params.delete(name);
      });
    });
  }

  function syncSimpleSearchUrl(term, filters) {
    var params = currentParams();
    var value = String(term || '').trim();
    params.delete('query');
    removeAdvancedParams(params);
    if (value) {
      params.set('q', value);
    } else {
      params.delete('q');
    }
    var category = activeCategoryFromFilters(filters);
    if (category) {
      params.set('category', categorySlugForLabel(category) || category);
    } else {
      params.delete('category');
    }
    params.delete('page');
    updateUrl(params, null, true);
  }

  function withCatalogFilter(filters) {
    var merged = {};
    Object.keys(filters || {}).forEach(function (key) {
      var values = cloneFilterValue(filters[key]);
      if (values.length) merged[key] = values;
    });
    merged[SEARCH_SCOPE_FILTER] = [SEARCH_SCOPE_VALUE];
    return merged;
  }

  function filtersIncludeCatalog(filters) {
    return cloneFilterValue(filters && filters[SEARCH_SCOPE_FILTER]).indexOf(SEARCH_SCOPE_VALUE) !== -1;
  }

  function activeCategoryFromFilters(filters) {
    return cloneFilterValue(filters && filters.category)[0] || '';
  }

  function filterSignature(filters) {
    var normalized = {};
    Object.keys(filters || {}).sort().forEach(function (key) {
      normalized[key] = cloneFilterValue(filters[key]).sort();
    });
    return JSON.stringify(normalized);
  }

  function searchSignature(term, filters) {
    return String(term || '') + '|' + filterSignature(filters || {});
  }

  function waitForPagefindInstance(instanceName) {
    return new Promise(function (resolve, reject) {
      var attempts = 0;
      function check() {
        var components = window.PagefindComponents;
        if (components && typeof components.getInstanceManager === 'function') {
          resolve(components.getInstanceManager().getInstance(instanceName));
          return;
        }
        attempts += 1;
        if (attempts > 120) {
          reject(new Error('Pagefind Component UI did not load.'));
          return;
        }
        window.setTimeout(check, 50);
      }
      check();
    });
  }

  async function directPagefindSearch(term, filters) {
    var pagefind = await import('/pagefind/pagefind.js');
    if (typeof pagefind.init === 'function') {
      await pagefind.init();
    }
    return pagefind.search(term ? term : null, { filters: filters });
  }

  function selectedRowsForSidebar(instance) {
    var params = currentParams();
    var state = stateFromParams(params);
    var rows = [];
    if (state.simple) {
      rows.push({ label: 'Keyword', value: state.simple });
    }
    state.rows.forEach(function (row) {
      rows.push({ label: row.label, value: row.value });
    });
    if (!rows.length && instance && instance.searchTerm) {
      rows.push({ label: 'Keyword', value: instance.searchTerm });
    }
    return rows;
  }

  function applyCategory(instance, categoryLabel) {
    var params = currentParams();
    params.delete('page');
    if (categoryLabel) {
      params.set('category', categorySlugForLabel(categoryLabel) || categoryLabel);
    } else {
      params.delete('category');
    }
    updateUrl(params, null, false);
    if (instance && typeof instance.triggerFilters === 'function') {
      SearchRuntime.applyingUrlState = true;
      SearchRuntime.suppressNextPageReset = true;
      SearchRuntime.suppressNextUrlSync = true;
      instance.triggerFilters(filtersForCategory(categoryLabel));
      window.setTimeout(function () {
        SearchRuntime.applyingUrlState = false;
      }, 0);
    }
  }

  function setupAdvancedForm() {
    var form = document.getElementById('advanced-search-form');
    if (!form) return;

    function setFormFromUrl() {
      var params = currentParams();
      var rows = advancedRowsFromParams(params);
      var category = categoryLabelFromParam(params.get('category')) || inferCategoryFromRows(rows) || CATEGORY_LABELS.objects;
      var slug = categorySlugForLabel(category);
      ADVANCED_FIELDS.forEach(function (field) {
        var input = form.elements[field.name];
        var match = firstFilledParam(params, field.names);
        if (input) input.value = match ? match.value : '';
      });
      Array.prototype.forEach.call(form.querySelectorAll('input[name="category"]'), function (radio) {
        radio.checked = Boolean(slug && radio.value === slug);
      });
      if (!slug) {
        var defaultRadio = form.querySelector('input[name="category"][value="objects"]');
        if (defaultRadio) defaultRadio.checked = true;
      }
      updateAdvancedSections();
    }

    function updateAdvancedSections() {
      var checked = form.querySelector('input[name="category"]:checked');
      var targetId = checked ? checked.getAttribute('data-for-id') : 'section-objects';
      Array.prototype.forEach.call(form.querySelectorAll('.category-section'), function (section) {
        section.style.display = section.id === targetId ? '' : 'none';
      });
    }

    setFormFromUrl();
    form.addEventListener('change', function (event) {
      if (event.target && event.target.name === 'category') {
        updateAdvancedSections();
      }
    });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var params = new URLSearchParams();
      Array.prototype.forEach.call(form.elements, function (field) {
        if (!field.name || field.disabled) return;
        if ((field.type === 'radio' || field.type === 'checkbox') && !field.checked) return;
        var value = String(field.value || '').trim();
        if (value) params.set(field.name, value);
      });
      params.delete('page');
      var action = form.getAttribute('action') || '/search-results/';
      if (!document.querySelector('giza-search-results')) {
        window.location.href = urlForParams(params, action);
        return;
      }
      updateUrl(params, action, false);
      var state = stateFromParams(params);
      if (SearchRuntime.instance && typeof SearchRuntime.instance.triggerSearchWithFilters === 'function') {
        SearchRuntime.applyingUrlState = true;
        SearchRuntime.suppressNextPageReset = true;
        SearchRuntime.suppressNextUrlSync = true;
        SearchRuntime.instance.triggerSearchWithFilters(state.term, filtersForCategory(state.category));
        window.setTimeout(function () {
          SearchRuntime.applyingUrlState = false;
        }, 0);
      }
    });
    window.addEventListener('popstate', setFormFromUrl);
    window.addEventListener('giza:search-url-change', setFormFromUrl);
  }

  function renderPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    var items = [];
    var previousClass = currentPage <= 1 ? ' class="pagination-previous disabled"' : ' class="pagination-previous"';
    var nextClass = currentPage >= totalPages ? ' class="pagination-next disabled"' : ' class="pagination-next"';
    items.push('<li' + previousClass + '>' + (currentPage <= 1 ? 'Previous' : '<a href="#" data-search-page="' + (currentPage - 1) + '" aria-label="Previous page">Previous</a>') + '</li>');

    var lastWasEllipsis = false;
    for (var page = 1; page <= totalPages; page += 1) {
      var visible = page === 1 || page === totalPages || Math.abs(page - currentPage) <= 2;
      if (!visible) {
        if (!lastWasEllipsis) {
          items.push('<li class="ellipsis"></li>');
          lastWasEllipsis = true;
        }
        continue;
      }
      lastWasEllipsis = false;
      if (page === currentPage) {
        items.push('<li class="current"><span class="show-for-sr">You are on page</span> ' + page + '</li>');
      } else {
        items.push('<li><a href="#" data-search-page="' + page + '" aria-label="Page ' + page + '">' + page + '</a></li>');
      }
    }
    items.push('<li' + nextClass + '>' + (currentPage >= totalPages ? 'Next' : '<a href="#" data-search-page="' + (currentPage + 1) + '" aria-label="Next page">Next</a>') + '</li>');
    return '<div class="row"><div class="text-center columns p-t-1"><nav aria-label="Pagination"><ul class="pagination m-l-neghalf">' + items.join('') + '</ul></nav></div></div>';
  }

  function renderResultCard(data) {
    var meta = data.meta || {};
    var url = meta.url || data.url || '#';
    var title = meta.title || data.title || url;
    var catalogId = meta.catalog_id || '';
    var image = meta.thumbnail || meta.image || DEFAULT_IMAGE;
    var thumbClass = meta.thumbnail ? 'thumbnail' : 'thumbnail no-img';
    var subheader = [];
    if (catalogId) subheader.push('<li>' + escapeHtml(catalogId) + '</li>');
    return [
      '<div class="media-object list-item search-result thumbsize-md thumbs-square">',
      '<div class="media-object-section"><div class="' + thumbClass + '"><a href="' + escapeAttr(url) + '"><img src="' + escapeAttr(image) + '" alt=""></a></div></div>',
      '<div class="media-object-section"><p class="media-object-title"><a href="' + escapeAttr(url) + '">' + escapeHtml(title) + '</a></p>',
      '<ul class="subheader">' + subheader.join('') + '</ul></div>',
      '</div>'
    ].join('');
  }

  function defineSearchComponents() {
    if (!window.customElements || customElements.get('giza-search-results')) return;

    class GizaSearchSidebar extends HTMLElement {
      connectedCallback() {
        this.instanceName = this.getAttribute('instance') || INSTANCE_NAME;
        this.categoryCounts = {};
        this.activeCategory = categoryLabelFromParam(currentParams().get('category'));
        this.render();
        this.addEventListener('click', (event) => {
          var link = event.target.closest('[data-search-category]');
          if (!link) return;
          event.preventDefault();
          var label = link.getAttribute('data-search-category') || '';
          applyCategory(this.instance, label === this.activeCategory ? '' : label);
        });
        waitForPagefindInstance(this.instanceName).then((instance) => {
          this.instance = instance;
          this.activeCategory = activeCategoryFromFilters(instance.searchFilters) || this.activeCategory;
          instance.on('search', (term, filters) => {
            this.activeCategory = activeCategoryFromFilters(filters);
            this.render();
          }, this);
          instance.on('filters', (filters) => {
            var available = filters && filters.available ? filters.available : {};
            this.categoryCounts = available.category || (instance.availableFilters && instance.availableFilters.category) || {};
            this.activeCategory = activeCategoryFromFilters(instance.searchFilters);
            this.render();
          }, this);
          instance.on('results', () => {
            this.activeCategory = activeCategoryFromFilters(instance.searchFilters);
            this.render();
          }, this);
          window.addEventListener('giza:direct-search-results', (event) => {
            var detail = event.detail || {};
            var searchResult = detail.searchResult || {};
            this.categoryCounts = searchResult.filters && searchResult.filters.category ? searchResult.filters.category : this.categoryCounts;
            this.activeCategory = activeCategoryFromFilters(detail.filters || {});
            this.render();
          });
          this.render();
        }).catch(() => {
          this.innerHTML = '<div class="feature-block secondary text-smaller"><h5 class="heading-alt">Search Options</h5><p>Search is available after the Pagefind index is built.</p></div>';
        });
      }

      render() {
        var rows = selectedRowsForSidebar(this.instance);
        var counts = this.categoryCounts || {};
        var hasCounts = Object.keys(counts).length > 0;
        var html = ['<div class="feature-block secondary text-smaller"><h5 class="heading-alt">Search Options</h5><p><a href="/search/">Start a new search</a></p>'];
        if (rows.length) {
          html.push('<div class="search-facet-section">');
          rows.forEach(function (row) {
            html.push('<h6 class="search-facet-title">' + escapeHtml(row.label) + ':</h6><ul class="search-facet-list"><li class="is-active">' + escapeHtml(row.value) + '</li></ul>');
          });
          html.push('</div>');
        }
        if (hasCounts || this.activeCategory) {
          html.push('<div class="search-facet-section"><h6 class="search-facet-title">Category:</h6><ul class="search-facet-list">');
          CATEGORY_ORDER.slice().sort(function (a, b) {
            return (counts[b] || 0) - (counts[a] || 0) || CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b);
          }).forEach((label) => {
            var count = counts[label] || 0;
            if (!count && label !== this.activeCategory) return;
            var active = label === this.activeCategory;
            var params = currentParams();
            params.delete('page');
            if (active) {
              params.delete('category');
            } else {
              params.set('category', categorySlugForLabel(label) || label);
            }
            var href = (window.location.pathname || '/search-results/') + (params.toString() ? '?' + params.toString() : '');
            html.push('<li class="search-facet-item' + (active ? ' is-active' : '') + '"><a href="' + escapeAttr(href) + '" data-search-category="' + escapeAttr(label) + '">' + escapeHtml(label) + ' (' + count + ')</a></li>');
          });
          html.push('</ul></div>');
        }
        html.push('</div>');
        this.innerHTML = html.join('');
      }
    }

    class GizaSearchResults extends HTMLElement {
      connectedCallback() {
        this.instanceName = this.getAttribute('instance') || INSTANCE_NAME;
        this.pageSize = parseInt(this.getAttribute('page-size') || '20', 10) || 20;
        this.currentPage = parsePageParam();
        this.renderToken = 0;
        this.seenSearch = false;
        this.signature = '';
        this.fallbackTimer = null;
        this.innerHTML = '<p class="static-site-meta">Loading search results...</p>';
        this.addEventListener('click', (event) => {
          var link = event.target.closest('[data-search-page]');
          if (!link) return;
          event.preventDefault();
          var page = parseInt(link.getAttribute('data-search-page') || '1', 10);
          if (!Number.isFinite(page) || page < 1) return;
          this.currentPage = page;
          updatePageParam(page, false);
          this.renderResults();
          this.scrollIntoView({ block: 'start', behavior: 'smooth' });
        });
        var syncPageFromUrl = () => {
          this.currentPage = parsePageParam();
          if (this.searchResult) this.renderResults();
        };
        window.addEventListener('popstate', syncPageFromUrl);
        window.addEventListener('giza:search-url-change', syncPageFromUrl);
        waitForPagefindInstance(this.instanceName).then((instance) => {
          this.instance = instance;
          instance.on('loading', () => {
            this.renderToken += 1;
            this.searchResult = null;
            this.innerHTML = '<p class="static-site-meta">Searching...</p>';
            this.scheduleDirectFallback();
          }, this);
          instance.on('search', (term, filters) => {
            var nextSignature = searchSignature(term, filters);
            var suppressPageReset = SearchRuntime.applyingUrlState || SearchRuntime.suppressNextPageReset;
            SearchRuntime.suppressNextPageReset = false;
            if (this.seenSearch && nextSignature !== this.signature && !suppressPageReset) {
              this.currentPage = 1;
              updatePageParam(1, true);
            }
            this.signature = nextSignature;
            this.seenSearch = true;
          }, this);
          instance.on('results', (searchResult) => {
            if (this.fallbackTimer) {
              window.clearTimeout(this.fallbackTimer);
              this.fallbackTimer = null;
            }
            this.searchResult = searchResult;
            this.renderResults();
          }, this);
          instance.on('error', (error) => {
            this.renderToken += 1;
            this.innerHTML = '<p class="callout alert">Search failed: ' + escapeHtml(error && error.message ? error.message : error) + '</p>';
          }, this);
          if (instance.searchResult) {
            this.searchResult = instance.searchResult;
            this.renderResults();
          } else {
            this.scheduleDirectFallback();
          }
        }).catch(() => {
          this.runDirectSearchFromUrl().catch(() => {
            this.innerHTML = '<p class="callout warning">Search is available after running Pagefind for this static build.</p>';
          });
        });
      }

      scheduleDirectFallback() {
        if (this.fallbackTimer) window.clearTimeout(this.fallbackTimer);
        this.fallbackTimer = window.setTimeout(() => {
          this.fallbackTimer = null;
          if (!this.searchResult) {
            this.runDirectSearchFromUrl().catch((error) => {
              this.innerHTML = '<p class="callout alert">Search failed: ' + escapeHtml(error && error.message ? error.message : error) + '</p>';
            });
          }
        }, 1200);
      }

      async runDirectSearchFromUrl() {
        var state = stateFromParams(currentParams());
        var filters = filtersForCategory(state.category);
        var signature = searchSignature(state.term, filters);
        this.renderToken += 1;
        this.innerHTML = '<p class="static-site-meta">Searching...</p>';
        var searchResult = await directPagefindSearch(state.term, filters);
        var latestState = stateFromParams(currentParams());
        var latestFilters = filtersForCategory(latestState.category);
        if (signature !== searchSignature(latestState.term, latestFilters)) return;
        this.searchResult = searchResult;
        window.dispatchEvent(new CustomEvent('giza:direct-search-results', {
          detail: { searchResult: searchResult, filters: filters }
        }));
        this.renderResults();
      }

      renderResults() {
        var token = this.renderToken + 1;
        this.renderToken = token;
        var rawResults = this.searchResult && this.searchResult.results ? this.searchResult.results : [];
        var total = rawResults.length;
        var totalPages = Math.max(1, Math.ceil(total / this.pageSize));
        if (this.currentPage > totalPages) {
          this.currentPage = totalPages;
          updatePageParam(this.currentPage, true);
        }
        var start = (this.currentPage - 1) * this.pageSize;
        var visible = rawResults.slice(start, start + this.pageSize);
        var noun = total === 1 ? 'search result' : 'search results';
        var status = '<div class="static-site-search-status"><h3 class="heading-alt m-t-half m-b-1">' + String(total) + ' ' + noun + ' found.</h3></div>';
        if (!total) {
          this.innerHTML = status + '<p>No catalog records matched this search.</p>';
          return;
        }
        this.innerHTML = status + '<p class="static-site-meta">Loading results ' + (start + 1).toLocaleString() + '-' + Math.min(start + this.pageSize, total).toLocaleString() + '...</p>';
        Promise.all(visible.map(function (raw) {
          return raw.data().catch(function () { return null; });
        })).then((items) => {
          if (token !== this.renderToken) return;
          var cards = items.filter(Boolean).map(renderResultCard).join('');
          this.innerHTML = status + '<div class="media-object-holder">' + cards + '</div>' + renderPagination(this.currentPage, totalPages);
        });
      }
    }

    customElements.define('giza-search-sidebar', GizaSearchSidebar);
    customElements.define('giza-search-results', GizaSearchResults);
  }

  function triggerSearchFromUrl(instance) {
    var state = stateFromParams(currentParams());
    var filters = filtersForCategory(state.category);
    instance.faceted = true;
    SearchRuntime.applyingUrlState = true;
    SearchRuntime.suppressNextPageReset = true;
    SearchRuntime.suppressNextUrlSync = true;
    if (state.term || typeof instance.triggerFilters !== 'function') {
      instance.triggerSearchWithFilters(state.term, filters);
    } else {
      instance.triggerFilters(filters);
    }
    window.setTimeout(function () {
      SearchRuntime.applyingUrlState = false;
    }, 0);
  }

  function notifyPagefindUnavailable() {
    Array.prototype.forEach.call(document.querySelectorAll('giza-search-results'), function (element) {
      element.innerHTML = '<p class="callout warning">Search is available after running Pagefind for this static build.</p>';
    });
  }

  window.GizaStaticSite = window.GizaStaticSite || {};
  window.GizaStaticSite.initPagefind = function () {
    if (SearchRuntime.initStarted || !document.querySelector('[data-giza-search-page]')) return;
    SearchRuntime.initStarted = true;
    defineSearchComponents();
    setupAdvancedForm();
    waitForPagefindInstance(INSTANCE_NAME).then(function (instance) {
      SearchRuntime.instance = instance;
      instance.faceted = true;
      instance.on('search', function (term, filters) {
        var suppressUrlSync = SearchRuntime.applyingUrlState || SearchRuntime.suppressNextUrlSync;
        SearchRuntime.suppressNextUrlSync = false;
        if (!suppressUrlSync && !SearchRuntime.enforcingCatalog) {
          syncSimpleSearchUrl(term, withCatalogFilter(filters));
        }
        if (SearchRuntime.enforcingCatalog || filtersIncludeCatalog(filters)) return;
        SearchRuntime.enforcingCatalog = true;
        instance.triggerSearchWithFilters(term || '', withCatalogFilter(filters));
        window.setTimeout(function () {
          SearchRuntime.enforcingCatalog = false;
        }, 0);
      }, SearchRuntime);
      triggerSearchFromUrl(instance);
      window.addEventListener('popstate', function () {
        triggerSearchFromUrl(instance);
      });
    }).catch(notifyPagefindUnavailable);
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


STATIC_TEMPLATE_PAGES = [
    StaticTemplatePage("about", "about.html", "About the Giza Project", "About the Giza Project at Harvard University."),
    StaticTemplatePage("blog", "blog.html", "The Giza Project Blog", "The Giza Project blog."),
    StaticTemplatePage("contact", "contact.html", "Contact Us", "Contact information for Digital Giza."),
    StaticTemplatePage("gizacard", "gizacard.html", "The GizaCARD", "The data model behind Digital Giza."),
    StaticTemplatePage("news", "news.html", "News", "Digital Giza news."),
    StaticTemplatePage("resources", "resources.html", "Educational Resources", "Educational resources from Digital Giza."),
    StaticTemplatePage("sampleblog", "sampleblogpost.html", "The Giza Project Blog", "Sample Giza Project blog post."),
    StaticTemplatePage("donate", "donate.html", "Donate", "Support the Giza Project."),
    StaticTemplatePage("gizaintro", "gizaintro.html", "Introduction to Giza", "Introduction to the Giza Plateau."),
    StaticTemplatePage("archaeology", "archaeology.html", "Archaeology at Giza", "Archaeology and excavation history at Giza."),
    StaticTemplatePage("commontopics", "commontopics.html", "People and Places of Giza", "Common topics about Giza."),
    StaticTemplatePage("faq", "faq.html", "Frequently Asked Questions", "Glossary and frequently asked questions."),
    StaticTemplatePage("gizaatschool", "gizaatschool.html", "Giza @ School", "Teaching resources for Giza."),
    StaticTemplatePage("giza3d", "giza3d.html", "Giza 3D", "Giza 3D resources and model links."),
]


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

    write_core_static_pages(args.output, repo_root)
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
        body_parts.append(render_static_template_fragment(repo_root, page_headers, context))

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
    pattern = re.compile(r"{%\s*block\s+'?([\w_]+)'?\s*%}(.*?){%\s*endblock\s*%}", re.DOTALL)
    for match in pattern.finditer(source):
        blocks[match.group(1)] = match.group(2)
    return blocks


def render_static_template_fragment(repo_root: Path, source: str, context: dict[str, str] | None = None) -> str:
    context = context or {}
    rendered = source
    rendered = re.sub(r"{%\s*(?:extends|load)\b.*?%}", "", rendered, flags=re.DOTALL)

    include_pattern = re.compile(r"{%\s*include\s+'([^']+)'\s*(?:with\s+(.*?))?\s*%}", re.DOTALL)
    while True:
        rendered, count = include_pattern.subn(
            lambda match: render_static_include(repo_root, match.group(1), parse_template_kwargs(match.group(2)), context),
            rendered,
        )
        if count == 0:
            break

    rendered = re.sub(r"{%\s*static\s+['\"]([^'\"]+)['\"]\s*%}", r"/static/\1", rendered)
    rendered = re.sub(r"{%\s*url\s+(.+?)\s*%}", render_static_url_tag, rendered)
    return rendered


def parse_template_kwargs(source: str | None) -> dict[str, Any]:
    if not source:
        return {}
    kwargs: dict[str, Any] = {}
    pattern = re.compile(r"([\w-]+)\s*=\s*(\"[^\"]*\"|'[^']*'|True|False|true|false|[^\s]+)")
    for key, raw_value in pattern.findall(source):
        value: Any = raw_value
        if (raw_value.startswith("\"") and raw_value.endswith("\"")) or (
            raw_value.startswith("'") and raw_value.endswith("'")
        ):
            value = raw_value[1:-1]
        elif raw_value in {"True", "true"}:
            value = True
        elif raw_value in {"False", "false"}:
            value = False
        kwargs[key] = value
    return kwargs


def render_static_include(repo_root: Path, include_name: str, kwargs: dict[str, Any], context: dict[str, str]) -> str:
    if include_name == "partials/page-header.html":
        return page_header(kwargs.get("title") or context.get("title") or "", bg=str(kwargs.get("bg") or "1"))
    if include_name == "partials/page-subheader.html":
        return render_page_subheader(
            backlink_url=plain_text(kwargs.get("backlink_url")),
            backlink_text=plain_text(kwargs.get("backlink_text") or "Back"),
            content=f'<h2 class="text-medium">{html.escape(context.get("subtitle") or "")}</h2>',
        )
    if include_name == "partials/page-subheader--gizaatschool.html":
        content = extract_template_blocks((repo_root / "templates" / include_name).read_text(encoding="utf-8")).get(
            "subheader_content", ""
        )
        return render_page_subheader(content=render_static_template_fragment(repo_root, content, context))
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


def render_page_subheader(*, content: str, backlink_url: str = "", backlink_text: str = "Back") -> str:
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
    title_html = f'<a class="heading-link" href="{html.escape(link, quote=True)}">{title}</a>' if link else title
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
        counter_html = f'<span class="badge">{html.escape(counter)}</span>' if counter else ""
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
    target = "" if kwargs.get("internal") else " target=\"_blank\""
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
        raise SystemExit(f"Unhandled template syntax in {template_name}: {rendered[start:end]!r}")


def render_giza3d_static_page(repo_root: Path) -> str:
    tours = render_static_template_fragment(
        repo_root,
        (repo_root / "templates" / "partials" / "3d-tours-list.html").read_text(encoding="utf-8"),
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
    advanced_search_body = """
<div class="page-header header-bg-5"><div class="row title"><header class="large-12 columns"><h1>Search the Archives</h1></header></div></div>
<div class="row static-site-search-page" data-giza-search-page>
  <section class="large-12 columns">
    <section class="static-site-advanced-search" data-pagefind-ignore>
      <h3>Advanced Search</h3>
      <p>Narrow your search results using the advanced search fields below.</p>
      <p class="text-smaller">Need help with abbreviations? Check out our <a href="/faq/#abbr">list of abbreviations on the FAQ page.</a></p>

      <form id="advanced-search-form" action="/search-results/" method="get">
        <div class="row">
          <fieldset id="category-radio-selector" class="medium-4 medium-push-8 columns">
            <legend>Search within the selected category:</legend>
            <div class="feature-block tertiary">
              <input id="objects" data-for-id="section-objects" value="objects" type="radio" name="category" checked><label for="objects">Objects</label><br>
              <input id="tombs" data-for-id="section-sites" value="sites" type="radio" name="category"><label for="tombs">Tombs and Monuments</label><br>
              <input id="diary" data-for-id="section-objects" value="diarypages" type="radio" name="category"><label for="diary">Diary Pages</label><br>
              <input id="unpubdocs" data-for-id="section-objects" value="unpubdocs" type="radio" name="category"><label for="unpubdocs">Unpublished Documents</label><br>
              <input id="mapsandplans" data-for-id="section-objects" value="mapsandplans" type="radio" name="category"><label for="mapsandplans">Maps and Plans</label>
            </div>
          </fieldset>

          <section id="section-objects" class="medium-8 medium-pull-4 columns category-section">
            <label>Object title or name:
              <input name="objects_title" type="text" placeholder="Example: 'royal statue' or 'Khafre'">
            </label>
            <label>Object or ID number:
              <input name="objects_allnumbers" type="text" placeholder="Example: 'HUMFA_14-11-206'">
            </label>
            <label>Material:
              <input name="objects_medium" type="text" placeholder="Example: 'alabaster'">
            </label>
            <label>Findspot:
              <input name="objects_provenance" type="text" placeholder="Example: 'G 2110'">
            </label>
            <label>Date of register entry:
              <input name="objects_entrydate" type="text" placeholder="Example: 05/23/1924">
            </label>
          </section>

          <section id="section-sites" class="medium-8 medium-pull-4 columns category-section" style="display: none;">
            <label>Tomb/Monument number:
              <input name="sites_number" type="text" placeholder="Example: 'G 7000 X'">
            </label>
            <label>Tomb/Monument name:
              <input name="sites_sitename" type="text" placeholder="Example: 'Eastern Cemetery'">
            </label>
            <label>Site Dates:
              <input name="sites_datevalues" type="text" placeholder="Example: 'Khufu to Shepseskaf'">
            </label>
            <label>People:
              <input name="sites_people" type="text" placeholder="Example: 'George Reisner'">
            </label>
          </section>
        </div>

        <div class="row">
          <div class="large-12 columns">
            <button class="button primary" type="submit">Search</button>
          </div>
        </div>
      </form>
    </section>
  </section>
</div>
""".strip()
    results_body = """
<div class="page-header header-bg-5"><div class="row title"><header class="large-12 columns"><h1>Search the Archives</h1></header></div></div>
<div class="row static-site-search-page" data-giza-search-page>
  <section class="medium-9 medium-push-3 columns">
    <pagefind-config instance="giza-search" faceted preload excerpt-length="30"></pagefind-config>
    <giza-search-results class="static-site-search-results" instance="giza-search" page-size="20"></giza-search-results>
  </section>
  <aside class="medium-3 medium-pull-9 columns">
    <giza-search-sidebar instance="giza-search"></giza-search-sidebar>
  </aside>
</div>
""".strip()
    extra_head = '<link href="/pagefind/pagefind-component-ui.css" rel="stylesheet">'
    extra_scripts = '<script src="/pagefind/pagefind-component-ui.js" type="module"></script><script>GizaStaticSite.initPagefind();</script>'
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
    result_image = summary.thumbnail or "/static/images/object1.png"
    values = {
        "title": summary.title,
        "type": type_label(summary.type),
        "category": search_category_label(summary.type),
        "catalog_id": summary.search_identifier,
        "image": result_image,
        "image_alt": summary.title if result_image else "",
        "thumbnail": summary.thumbnail,
    }
    return "\n".join(
        f'<meta data-pagefind-meta="{html.escape(key)}[content]" content="{html.escape(value, quote=True)}">'
        for key, value in values.items()
        if value
    )


def render_pagefind_filters(summary: ItemSummary) -> str:
    filters = [
        ("category", search_category_label(summary.type)),
        ("search_scope", "catalog"),
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
    search_identifier = plain_text(source.get("sitename") if item_type == "sites" else source.get("number")) or item_id
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
        search_identifier=search_identifier,
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


def search_category_label(item_type: str) -> str:
    return SEARCH_CATEGORY_LABELS.get(item_type, type_label(item_type))


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
