# Static Site Redeployment Specification

## Purpose

Temporarily replace the current VM-hosted Digital Giza application with a safer static deployment until the permanent replacement launches. The static site should preserve public catalog access, public item detail pages, IIIF/Mirador viewing, and search, while removing the runtime attack surface from Django, PostgreSQL, Elasticsearch, Apache/mod_wsgi, admin, and authentication.

This is a temporary preservation deployment. Exact feature parity is not required. The priority is a secure, stable public site with enough catalog functionality for the interim period.

## Current Understanding

The existing application is a Django 2.2 project with Elasticsearch 5.6 as the primary public catalog data source. Public item pages and IIIF manifests are backed by Elasticsearch. Some public or semi-public features are backed by PostgreSQL, including lessons, topics, collections, users, and MyGiza models.

Production export data has been copied into `static_site/`. The Elasticsearch archive contains both catalog and IIIF exports, and the Django content dump succeeded. Lessons and public collections should therefore be included in the temporary static deployment.

The live web endpoint is unreliable and times out. We should not crawl the production web application as the build source.

The build should avoid booting Django. Use a minimal static site generator that reads the exported data directly, emits static files, and reuses existing static assets where useful.

The Django admin and login/signup routes are no longer useful for the temporary public deployment. They should not exist in the static runtime.

## Confirmed VM Data Exports

Elasticsearch version:

- `5.6.16`

Exported Elasticsearch data:

- `giza.ndjson.gz`: `159,257` live documents, `38M` compressed.
- `iiif.ndjson.gz`: `134,580` live documents, `24M` compressed.

The export counts matched Elasticsearch `_count`, so all live docs were exported.

Index counts from production:

| Index | Live Docs | Notes |
| --- | ---: | --- |
| `giza` | `159,257` | Public catalog and special library docs |
| `iiif` | `134,580` | IIIF manifest docs |

`giza` document counts by type:

| Type | Count | Static Handling |
| --- | ---: | --- |
| `photos` | `83,403` | Generate item pages |
| `objects` | `31,694` | Generate item pages |
| `unpubdocs` | `11,226` | Generate item pages |
| `mapsandplans` | `10,109` | Generate item pages |
| `diarypages` | `7,612` | Generate item pages |
| `drawings` | `4,079` | Generate item pages |
| `sites` | `4,000` | Generate item pages |
| `ancientpeople` | `3,264` | Generate item pages |
| `videos` | `1,392` | Generate item pages and video listing if desired |
| `modernpeople` | `1,022` | Generate item pages |
| `pubdocs` | `796` | Generate item pages and library links |
| `library` | `289` | Special author/grouping docs, no item detail page |
| `institutions` | `167` | Generate item pages |
| `3dmodels` | `156` | Generate item pages |
| `groups` | `44` | Generate item pages |
| `animals` | `4` | Generate item pages |

Public item page total, excluding `library`:

- `158,968` item pages.

IIIF manifest facts:

- `134,580` total manifests.
- `19,354` manifests are multi-canvas.
- Largest observed manifest has `1,991` canvases.

Confirmed local production data:

- `static_site/giza-es-export.tar.gz` contains `giza-es-export/giza.ndjson.gz` and `giza-es-export/iiif.ndjson.gz`.
- `static_site/giza-content-dump.json.gz` is present and the Django content dump succeeded.
- Django content dump model counts: `10` lessons, `6` topics, `7,790` collections, and `3,679` Elasticsearch item references.
- Collection visibility counts: `1` public collection and `7,789` non-public collections.
- The static catalog does not require a PostgreSQL dump.
- Lessons and public collections are required for the temporary deployment.

## Target Architecture

The temporary deployment should be fully static at runtime.

Runtime components:

- Local development with `uv run python -m http.server --directory dist 8000` serving the generated output directory.
- Staging deployment at `https://giza-static.digitalhumanities.fas.harvard.edu/`.
- Eventual GitHub Pages deployment using the production domain `http://giza.fas.harvard.edu/`.
- Static HTML, CSS, JavaScript, images, and generated JSON.
- Pagefind client-side search index.
- External image/media services already referenced by catalog data.

No runtime components:

- Django.
- PostgreSQL.
- Elasticsearch.
- Apache/mod_wsgi application serving dynamic content.
- Admin routes.
- Login/signup/session/auth flows.
- MyGiza create/edit workflows.

Build-time components:

- Minimal Python 3.14 static site generator maintained in this repository and run through `uv`.
- Production exports under `static_site/`.
- Existing repository static assets, plus simple generator-owned templates or HTML helper functions.
- Pagefind CLI.

Build-time components explicitly not required:

- Django settings or template rendering.
- PostgreSQL.
- Elasticsearch.

## Data Sources

### Required Inputs

Required input files:

- `static_site/giza-es-export.tar.gz`
- `giza-es-export/giza.ndjson.gz` inside the ES archive.
- `giza-es-export/iiif.ndjson.gz` inside the ES archive.
- `static_site/giza-content-dump.json.gz`
- Repository static assets under `static/`
- Minimal generator templates or HTML helper functions maintained outside Django.

Required item fields are flexible because documents differ by type. The renderer should tolerate missing fields and use defensive defaults.

Commonly useful item fields:

- `_type`
- `_id`
- `_source.id`
- `_source.displaytext`
- `_source.description`
- `_source.number`
- `_source.allnumbers`
- `_source.primarydisplay`
- `_source.relateditems`
- `_source.department`
- `_source.period`
- `_source.medium`
- `_source.classificationtext`
- `_source.sitename`
- `_source.sitedates`
- `_source.pdf`

### Django Content Dump Inputs

Required Django content dump models:

- `giza.Topic`
- `giza.Lesson`
- `giza.Collection`
- `giza.ElasticsearchItem`

Do not require users/auth tables for static generation. Avoid copying user data unless there is a specific legal and operational reason.

Optional VM config:

- Apache vhost information.
- Rewrite and redirect rules.
- Deployed code/static paths, if production differs from the repo.

## Output Scope

### Required Output

Generate these static artifacts:

- Home page and core static pages.
- All public item detail pages for non-`library` `giza` docs.
- Top-level IIIF manifest JSON for all `iiif` docs.
- Pagefind search index.
- Search page using Pagefind UI and filters.
- `/library/` from ES `library` and `pubdocs` docs.
- `/videos/` from ES `videos` docs.
- `/lessons/` and `/lessons/<slug>` from the Django content dump.
- `/collections/` and `/collections/<slug>` for the public collection from the Django content dump.
- Static CSS, JS, fonts, images, and existing built assets.
- Helpful `404.html` and any static error pages.

Do not add an explanatory banner for reduced functionality.

Required item URL format:

- `/<type>/<id>/full/`

Static file format for item pages:

- `dist/<type>/<id>/full/index.html`

Required manifest URL format for GitHub Pages compatibility:

- `/manifests/<manifest-id>.json`

Static file format for manifests:

- `dist/manifests/<manifest-id>.json`

Optional legacy manifest URL format:

- `/manifests/<manifest-id>/`

Legacy manifest URL handling:

- GitHub Pages does not provide custom rewrites or headers, so the generator should not depend on `/manifests/<manifest-id>/` resolving to JSON.
- If extensionless manifest URLs must be preserved for existing IIIF consumers, add a CDN/proxy rewrite layer in front of the static files or choose a host that supports rewrites.
- For the first static deployment, item pages should link to `/manifests/<manifest-id>.json`.

### Optional Output

Optional artifacts:

- `/<type>/<id>.json` item JSON endpoints if known external consumers need them.
- Host-specific legacy support for `/manifests/<manifest-id>/` if a rewrite-capable host or CDN is added.
- Legacy redirects or static redirect pages from old paths.
- XML sitemap files split into manageable chunks.

In this document, external consumers means non-browser clients, third-party websites, scripts, libraries, or IIIF viewers that depend on Digital Giza URLs as data endpoints rather than ordinary human-facing pages. No known external consumer currently requires optional item JSON endpoints or IIIF sequence/canvas/annotation endpoints, so do not generate them initially.

### Initially Excluded Output

Do not generate these unless required by testing or external consumer needs:

- `/manifests/<id>/sequence/0`
- `/manifests/<id>/canvas/<n>`
- `/manifests/<id>/annotation/canvas/<n>`

Rationale:

- Top-level IIIF manifests include sequences, canvases, and annotations.
- Mirador should work with the top-level manifest URL.
- Fully materializing subresources could add hundreds of thousands or millions of files because one manifest has `1,991` canvases.

## Route Map

| Current Route | Static Handling | Notes |
| --- | --- | --- |
| `/` | Generate | Static home page |
| `/about/` | Generate | Static page |
| `/contact/` | Generate | Static page |
| `/gizacard/` | Generate | Static page |
| `/news/` | Generate | Static page |
| `/resources/` | Generate | Static page |
| `/blog/` | Generate or redirect | Existing page appears static/sample-like |
| `/donate/` | Generate or redirect | Current nav points to external Harvard giving URL |
| `/gizaintro/` | Generate | Static page |
| `/archaeology/` | Generate | Uses Knight Lab timeline CDN |
| `/commontopics/` | Generate | Static page |
| `/faq/` | Generate | Static page |
| `/gizaatschool/` | Generate | Static page |
| `/giza3d/` | Generate | Static wrapper around external 3D viewer |
| `/library/` | Generate | Data from ES `library` and `pubdocs` |
| `/videos/` | Generate | Data from ES `videos` |
| `/search/` | Replace | Pagefind search page |
| `/search-results/` | Replace | Redirect or serve Pagefind search page with query support |
| `/<type>/<id>/full/` | Generate | Main catalog detail pages |
| `/<type>/<id>/intro/` | Redirect | Redirect to `/<type>/<id>/full/` |
| `/<type>/<id>/allphotos/` | Redirect | Redirect to `/<type>/<id>/full/` initially |
| `/<type>/<id>.json` | Optional | Generate only if needed |
| `/manifests/<id>.json` | Generate | Top-level IIIF JSON for GitHub Pages compatibility |
| `/manifests/<id>/` | Optional legacy support | Only works with a rewrite-capable host/CDN, not plain GitHub Pages |
| `/manifests/<id>/sequence/0` | Exclude initially | Generate only if required |
| `/manifests/<id>/canvas/<n>` | Exclude initially | Generate only if required |
| `/manifests/<id>/annotation/canvas/<n>` | Exclude initially | Generate only if required |
| `/admin/` | Remove | Return 404 or gone |
| `/login/` | Remove | Already disabled in app routes |
| `/sign-up/` | Remove | Already disabled in app routes |
| `/logout/` | Remove | Already disabled in app routes |
| `/mygiza/` | Remove | Skip logged-in user functionality |
| `/collections/` | Generate | Required from Django content dump |
| `/collections/user` | Remove or redirect | No auth/session support |
| `/collections/create` | Remove | No dynamic writes |
| `/collections/<slug>` | Generate | Required for public collections from Django content dump |
| `/lessons/` | Generate | Required from Django content dump |
| `/lessons/<slug>` | Generate | Required from Django content dump |

## Rendering Strategy

Use a purpose-built static generator instead of Django.

Generator requirements:

- Run with `uv run python` using the repo-root Python 3.14 environment.
- Read compressed production exports directly from `static_site/`.
- Use Python standard-library modules where practical: `gzip`, `json`, `tarfile`, `pathlib`, `html`, `shutil`, and `mimetypes`.
- Emit static HTML, JSON, copied assets, and small client-side JavaScript helpers.
- Avoid importing Django settings, models, templates, URL routing, forms, context processors, or Elasticsearch clients.
- Reuse existing CSS/JS/assets from `static/` to keep visual continuity where possible.
- Recreate the public item page layout sufficiently for temporary use rather than pursuing exact template parity.
- Add Pagefind metadata and facets during HTML generation.
- Drop auth/admin/MyGiza dynamic behaviors cleanly.

Non-goals:

- Exact visual parity with the current Django templates.
- Offline Django template rendering.
- PostgreSQL or Elasticsearch access during the build.

Expected tradeoff:

- The static pages may be visually simpler than the current site, but the build will be safer, easier to run locally, and easier to deploy through GitHub Pages.

## Item Page Generation

Generate one item detail page for every non-`library` `giza` doc.

Canonical URL:

- `/<type>/<id>/full/`

Minimum content per item page:

- Page title from `displaytext` or fallback to `<type> <id>`.
- Primary image/video/iframe/PDF link when available.
- Description or overview when available.
- Key metadata fields relevant to the item type.
- Related items grouped by type when available.
- Links to related item pages when the related item id and type are available.
- Link to IIIF/Mirador viewer when `primarydisplay.has_manifest` or a manifest exists.

Rendering should be defensive:

- Missing `primarydisplay` should not fail the build.
- Missing `relateditems` should render no related section.
- Unrecognized types should still produce a generic details page.
- Long text fields should render safely and preserve readable formatting.

HTML escaping:

- Escape text fields by default.
- Allow known-safe HTML only where existing data is known to contain intended markup, such as publication boiler text, after evaluating risk.
- Prefer sanitization over raw insertion for fields that came from admin or external systems.

## IIIF And Mirador

Generate top-level IIIF manifests for every `iiif` doc.

Manifest output URL:

- `/manifests/<id>.json`

Manifest source:

- `_source.manifest`

Required static handling:

- Preserve JSON structure.
- Ensure `@id` values are absolute or resolve correctly against the static site domain.
- Preserve sequence, canvas, annotation, image service, and metadata content.
- Serve JSON with appropriate content type through the `.json` extension.
- Verify CORS behavior on staging and GitHub Pages if manifests may be consumed cross-origin.

Potential manifest rewriting:

- Existing Django dynamically set manifest `@id` and nested `@id` values using `request.build_absolute_uri('/manifests/')`.
- Static generation should rewrite relative manifest ids to absolute URLs using a build-time `--base-url`.
- For staging, use `https://giza-static.digitalhumanities.fas.harvard.edu/`.
- For production, use `http://giza.fas.harvard.edu/` unless HTTPS is enabled for the final domain before cutover.
- Example staging top-level `@id`: `https://giza-static.digitalhumanities.fas.harvard.edu/manifests/photos-49329.json`.
- Example production top-level `@id`: `http://giza.fas.harvard.edu/manifests/photos-49329.json`.
- Sequence/canvas/annotation `@id` values may remain stable identifiers even when separate endpoint files are not generated.

Important compatibility decision:

- Even if subresource endpoint files are not generated, internal `@id` values can remain stable identifiers.
- If a IIIF consumer attempts to fetch sequence/canvas/annotation `@id` URLs directly, those URLs will 404 unless generated or rewritten.
- Mirador generally consumes the full manifest and should not require fetching those separate URLs.
- Extensionless legacy manifest URLs, such as `/manifests/photos-49329/`, should be treated as optional compatibility work because GitHub Pages cannot rewrite them to `.json` files.

Testing Mirador:

- Test single-canvas item such as `/photos/49329/full/`.
- Test multi-canvas site manifests from samples such as `sites-329`, `sites-335`, or `sites-532`.
- Test the largest known manifest if feasible to assess viewer performance.
- Confirm Harvard IIIF image service URLs load from the static domain.

## Pagefind Search

Use Pagefind as the static search engine.

Expected acceptable differences from Elasticsearch:

- No Elasticsearch fuzzy matching.
- Different scoring/ranking.
- Different tokenization and stemming behavior.
- No ES nested query semantics.
- No exact item-number redirect unless implemented separately.
- Facets/filters are generated from emitted static metadata rather than ES aggregations.

Pagefind should index:

- Item detail pages.
- Core static pages.
- Library, video, lesson, and public collection pages.

Pagefind should not index:

- Manifest JSON.
- Asset files.
- Error pages unless desired.
- Search result UI pages unless desired.

Use Pagefind metadata and filters in generated item pages.

Recommended attributes:

```html
<main data-pagefind-body>
  ... visible item content ...
</main>

<meta data-pagefind-meta="title" content="...">
<meta data-pagefind-meta="type" content="Objects">
<meta data-pagefind-meta="thumbnail" content="...">

<span data-pagefind-filter="type">Objects</span>
<span data-pagefind-filter="department">Harvard University-Boston Museum of Fine Arts Expedition</span>
<span data-pagefind-filter="material">Limestone</span>
```

Recommended initial Pagefind filters:

- `type`
- `department`
- `classification`
- `material`
- `period`
- `site_name`
- `has_image`
- `has_manifest`
- `has_pdf`

Optional filters after testing cardinality:

- `date`
- `excavator`
- `tomb_owner`
- `owning_institution`
- `format`
- `photographer`

Avoid filters with extremely high cardinality unless user value is clear. High-cardinality filters can make the UI noisy and increase index size.

Search URL behavior:

- `/search/` should serve the Pagefind search UI.
- `/search-results/?q=<term>` should redirect to or render the same Pagefind search UI.
- Preserve query parameter `q` by reading it client-side and seeding the Pagefind search box.
- Advanced search fields can be removed, simplified, or mapped to filters later.

Exact number search behavior:

- Current ES search has special behavior for `type:number` patterns and may redirect directly to one matching item.
- For the temporary static site, omit initially unless it is high priority.
- A lightweight client-side lookup table can be generated later for item numbers if needed.

## Library And Video Pages

The `/library/` page currently uses Elasticsearch data and should be generated.

Library source docs:

- `library` type: author/grouping docs.
- `pubdocs` type: publication docs and PDFs.

Generate `/library/` because it is linked from nav and has public value.

Library page behavior:

- Sort by author/name as default.
- Optional static variants or client-side sorting for format/year.
- Link directly to PDF URLs when present.

The `/videos/` page currently uses ES `videos` docs and should be generated.

Video page behavior:

- Generate a listing from video docs.
- Preserve video source URLs from `primarydisplay.main`.
- Use thumbnails from `primarydisplay.thumbnail` where available.

## Lessons And Collections

These are PostgreSQL-backed in the current app, but the required content is now available from `static_site/giza-content-dump.json.gz`.

Confirmed dump facts:

- `10` `giza.lesson` records.
- `6` `giza.topic` records.
- `7,790` `giza.collection` records.
- `3,679` `giza.elasticsearchitem` records.
- Only `1` collection has `public=True`; the remaining `7,789` collections must not be published.

Generate these routes:

- `/lessons/`
- `/lessons/<slug>`
- `/collections/`
- `/collections/<slug>`

For lessons:

- Generate listing and detail pages from `Lesson` records.
- Preserve lesson content if it is public and not sensitive.
- Link lesson-associated collections if available.

For collections:

- Generate public collection listing only.
- Generate individual public collection pages only for collections with `public=True`.
- Resolve `ElasticsearchItem` references to generated item pages using type and ES id.
- Do not preserve editing, adding, deleting, owner-only collections, or auth-specific pages.

Privacy rule:

- Do not publish private collections.
- Do not publish user names or owner details unless already public and approved.
- Do not deploy auth/user data.
- If the dump contains ambiguous visibility flags, fail closed and exclude the collection until reviewed.

## Static Assets

Use prebuilt assets from the repo unless VM deployed assets differ.

Known assets:

- `static/css/app.css`
- `static/css/project.css`
- `static/css/giza.css`
- `static/css/blueimp-gallery.min.css`
- `static/js/app.js`
- `static/js/giza.js`
- `static/js/mirador-giza.js`
- `static/js/blueimp-gallery.min.js`
- `static/fonts/*`
- `static/images/*`
- `static/img/*`

The `client/` package is an old Foundation/Gulp project. Avoid requiring a new Node build unless static assets are missing or stale.

Asset strategy:

- Copy `static/` to `dist/static/`.
- Preserve existing relative asset paths where templates expect `/static/...`.
- If deploying under the domain root, keep `/static/` as the asset prefix.
- Do not hotlink local VM assets.

External dependencies to keep:

- Google Fonts.
- Font Awesome CDN if used.
- Knight Lab Timeline CDN for archaeology page.
- Harvard NRS URLs.
- Harvard IIIF image service URLs.
- `gizamedia.rc.fas.harvard.edu` media and 3D viewer URLs if still available.

## Build Pipeline

Recommended build command shape:

```bash
uv run python scripts/build_static_site.py \
  --es-archive static_site/giza-es-export.tar.gz \
  --django-content-dump static_site/giza-content-dump.json.gz \
  --output dist \
  --base-url https://giza-static.digitalhumanities.fas.harvard.edu

npx -y pagefind --site dist

uv run python -m http.server --directory dist 8000
```

For the production build, change `--base-url` to `http://giza.fas.harvard.edu` unless HTTPS is enabled for that domain before cutover.

Build stages:

1. Clean output directory.
2. Copy static assets.
3. Open `static_site/giza-es-export.tar.gz` and stream `giza.ndjson.gz`.
4. Build an item lookup map for related links where needed.
5. Generate item pages for non-`library` docs.
6. Generate static pages.
7. Generate library and video pages.
8. Load `static_site/giza-content-dump.json.gz`.
9. Generate lessons and public collections.
10. Stream `iiif.ndjson.gz` from the ES archive and write `/manifests/<id>.json` files.
11. Generate GitHub Pages-compatible redirect pages where useful.
12. Generate sitemap files if desired.
13. Run Pagefind.
14. Run validation checks.

Performance guidance:

- Stream exports where possible.
- Do not load every full IIIF manifest into memory at once.
- It is acceptable to build a compact lookup of item id/type/title/thumbnail for related links.
- Write files incrementally.
- Parallelize item HTML generation only after single-thread correctness is proven.

Expected output volume:

- Around `159k` item HTML files.
- Around `135k` IIIF manifest JSON files.
- Pagefind index files.
- Static assets.

This is large but manageable for modern static hosting. File count and output size should be verified against staging and GitHub Pages before production cutover.

## Hosting And Rewrites

Local development:

- Serve `dist/` with `uv run python -m http.server --directory dist 8000`.
- Test representative pages at `http://localhost:8000/`.
- Use `.json` manifest URLs so local development does not require rewrite support.

Staging host:

- First deployment target is `https://giza-static.digitalhumanities.fas.harvard.edu/`.
- Build staging manifests with `--base-url https://giza-static.digitalhumanities.fas.harvard.edu`.
- Verify the staging host can serve the large file count and correct MIME types for `.json`, `.css`, `.js`, fonts, and images.

Production host:

- Eventual deployment target is GitHub Pages using `http://giza.fas.harvard.edu/`.
- Build production manifests with `--base-url http://giza.fas.harvard.edu` unless HTTPS is enabled for the production domain before cutover.
- GitHub Pages does not support arbitrary rewrites, custom response headers, or true server-side redirects.
- Use concrete file paths and `.json` extensions rather than relying on host rewrites.

GitHub Pages-compatible route handling:

- `/search-results/` can be a generated static page that reads `?q=` client-side and forwards or renders the same Pagefind UI as `/search/`.
- `/<type>/<id>/intro/` and `/<type>/<id>/allphotos/` can be generated as lightweight HTML redirect pages pointing to `/<type>/<id>/full/` if link preservation is worth the extra files.
- `/manifests/<id>/` cannot be reliably rewritten to `/manifests/<id>.json` on plain GitHub Pages.
- Admin/auth routes should not be generated; they should fall through to `404.html`.
- `/mygiza/` should not be generated.

Headers and MIME behavior to verify:

- `.json` manifests are served as `application/json` or another browser-acceptable JSON MIME type.
- Cross-origin manifest consumption works if external IIIF viewers load the manifests.
- Static assets and Pagefind files load with acceptable cache behavior for launch.

## Validation Plan

Build validation:

- Confirm generated item page count equals `158,968` unless intentionally scoped.
- Confirm generated manifest count equals `134,580`.
- Confirm no generator exceptions were swallowed.
- Confirm no obviously empty title pages above an acceptable threshold.
- Confirm all required static assets exist.

Sample URL validation:

- `/`
- `/search/`
- `/library/`
- `/videos/`
- `/sites/3050/full/`
- `/objects/48587/full/`
- `/pubdocs/92/full/`
- `/videos/45481/full/`
- `/3dmodels/71017/full/`
- `/photos/49329/full/`
- `/manifests/photos-49329.json`
- `/manifests/sites-329.json`

Mirador validation:

- Item page with one canvas opens Mirador.
- Item page with many canvases opens Mirador.
- Browser console has no manifest fetch or CORS errors.
- Image tiles load from Harvard IIIF service.

Search validation:

- Search finds known terms such as `Khufu`, `Menkaure`, `Sphinx`, and `Reisner`.
- Search result titles and thumbnails render correctly.
- Type filter works.
- At least three metadata filters work on item pages.
- `/search-results/?q=Khufu` seeds or redirects to Pagefind search.

Link validation:

- Crawl generated HTML locally with a static link checker.
- Treat external media links as warnings, not hard blockers, unless many are broken.
- Treat internal 404s as release blockers except intentionally removed routes.

Security validation:

- No admin/login/signup pages are deployed.
- No Django secret, DB password, VM config, or exported raw data is in `dist/`.
- No private collection/user data is published.
- No `.gz` ES exports are deployed.

## Rollout Plan

Phase 1: Prototype

- Generate a small subset of item pages from each type.
- Generate a small subset of IIIF manifests.
- Build Pagefind index.
- Verify layout, search, and Mirador locally.

Phase 2: Full Local Build

- Generate all item pages and manifests.
- Run Pagefind.
- Run validation checks.
- Review output size and file count.

Phase 3: Staging Deploy

- Deploy to `https://giza-static.digitalhumanities.fas.harvard.edu/`.
- Verify MIME types, CORS behavior, and GitHub Pages compatibility assumptions.
- Test representative URLs and Mirador in browser.
- Share staging URL for content owner review.

Phase 4: Production Cutover

- Lower DNS TTL ahead of cutover if possible.
- Deploy final static build.
- Point `http://giza.fas.harvard.edu/` to GitHub Pages or the selected static frontend.
- Monitor 404s, search behavior, and IIIF/Mirador errors.

Phase 5: Temporary Maintenance

- Keep the ES exports and build scripts in a secure archive.
- Rebuild only if critical content fixes are needed.
- Avoid reopening dynamic VM services unless necessary.

## Risks And Mitigations

Risk: Static output has too many files for chosen host.

Mitigation: Measure output size and file count during the full local build, then verify staging and GitHub Pages can handle it before production cutover.

Risk: Simplified generator does not exactly match the old Django templates.

Mitigation: Preserve essential content and navigation first, reuse existing CSS/assets where useful, and accept minor visual differences for the temporary deployment.

Risk: Mirador requires subresource endpoints.

Mitigation: Test first. If required, generate sequence/canvas/annotation endpoints selectively or add dynamic edge function/rewrite logic.

Risk: Pagefind index becomes too large.

Mitigation: Tune indexed body content, exclude excessive related-item text, limit high-cardinality filters, and test index size early.

Risk: Publication or item fields contain unsafe HTML.

Mitigation: Escape by default and sanitize explicitly allowed HTML fields.

Risk: Lessons or collections contain important public content outside ES.

Mitigation: Use `static_site/giza-content-dump.json.gz` to preserve public lessons and collections, and fail closed for ambiguous private collection data.

Risk: External image/media services become unavailable.

Mitigation: Confirm those services are independent of the old VM. If not, identify critical media assets separately.

Risk: Old JSON endpoints have external consumers.

Mitigation: External consumers means third-party tools, scripts, libraries, or IIIF viewers using Digital Giza URLs as data endpoints. Check logs if available; otherwise omit optional JSON endpoints initially and generate `/<type>/<id>.json` later only if needed, using ES `_source`.

Risk: Existing deep links use `intro`, `allphotos`, or legacy `/v1/` paths.

Mitigation: Add redirects for known legacy routes.

## Resolved Decisions

- The limited Django content dump succeeded and is available at `static_site/giza-content-dump.json.gz`.
- Lesson pages are required.
- Public collection pages are required.
- Use a minimal Python 3.14 static generator run through `uv`, not Django.
- Use `uv run python -m http.server --directory dist 8000` for local development.
- Deploy first to `https://giza-static.digitalhumanities.fas.harvard.edu/`.
- Target GitHub Pages for eventual production deployment.
- Use `http://giza.fas.harvard.edu/` as the final production domain for manifest `@id` rewriting unless HTTPS is enabled before cutover.
- Do not display an explanatory banner.
- Do not generate `/mygiza/`.
- Do not generate optional item JSON endpoints or IIIF subresource endpoints initially unless testing or logs show they are required by external consumers.

## Remaining Watch Items

- Review lesson content and the single public collection for display quality before staging.
- Verify GitHub Pages can handle the generated file count and output size.
- Verify `.json` MIME type and CORS behavior on staging and production.
- Verify Mirador works with `/manifests/<id>.json` URLs and does not require extensionless manifest or IIIF subresource endpoints.

## Recommended Next Steps

1. Build a prototype `uv run python scripts/build_static_site.py` generator for a small representative subset.
2. Validate generated item pages, lessons, the public collection, Pagefind facets, and Mirador locally with `uv run python -m http.server --directory dist 8000`.
3. Review lesson content and the single public collection for display quality.
4. Generate the full static site and Pagefind index.
5. Deploy to `https://giza-static.digitalhumanities.fas.harvard.edu/` for staging review.
6. If staging succeeds, rebuild with `--base-url http://giza.fas.harvard.edu` and prepare the GitHub Pages production cutover.
