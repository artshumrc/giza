# gizamedia hot-storage preservation manifest

**Question answered:** which files currently on the non-IIIF media drive
(`gizamedia.rc.fas.harvard.edu` — "a drive with a web server in front of it") are
actually referenced by the Giza website and therefore must be preserved when that
storage migrates to S3.

## Result

**24,176 distinct files** must be preserved.

| | count |
|---|---|
| originals | 12,027 |
| thumbnails | 12,149 |
| **total** | **24,176** |

By type: `.jpg` 21,930 · `.mov` 1,226 · `.pdf` 821 · `.mp4` 166 · `.html` 28 (3D-tour viewer pages) · `.webm`/`.ogv` 1 each · directory/app refs 3.

By collection (top): GPH 9,025 · HUMFA 8,008 · MFA-images 3,853 · RPM 1,846 · Berlin (BÄM/BŽM/BÃ„M) 273 · documents 463 · videos 157 · GEM 135 · ASU 132 · CBE 114 · others (TUR, EMC, NMEC, UPM, 3D, website) < 100 each.

All files live under `/images/` (23,713) or `/documents/` (463).

## Files in this deliverable

- **`gizamedia_files_to_preserve.txt`** — the authoritative list, one server-relative path per line (24,176 lines). This is the migration allow-list.
- **`gizamedia_encoding_ambiguous.txt`** — 277 entries (subset of the above) from the Berlin museum collection whose byte encoding is uncertain (see caveat 1). Reconcile these against the real drive listing.

## Which host, and why only this one

Every URL in the data and the built site was inventoried. Hosts found:

| host | role | migrating? |
|---|---|---|
| `gizamedia.rc.fas.harvard.edu` | **non-IIIF media on a plain web server** | **YES — this manifest** |
| `nrs.harvard.edu`, `ids.lib.harvard.edu` | Harvard DRS — IIIF-served | no (IIIF, managed) |
| `iiif-cache.digitalhumanities.fas.harvard.edu` | project IIIF thumbnail cache | no (IIIF, regenerable — see caveat 3) |
| `fonts.googleapis.com`, `use.fontawesome.com`, `cdn.knightlab.com`, `community.alumni.harvard.edu`, `www.neh.gov`, `stats.digitalhumanities.fas.harvard.edu`, external museum sites | fonts / CDNs / analytics / funder & partner links | no (not our media) |

`gizamedia.rc.fas.harvard.edu` is the only host serving raw, non-IIIF media files
directly off a drive, so it is the only one in scope.

## Sources scanned

1. **ES export dumps** — `static_site/giza-es-export.tar.gz` → `giza.ndjson.gz`
   (159,257 records) + `iiif.ndjson.gz` (134,580 records). JSON string values, parsed clean.
2. **Built static site** — every text file under `dist/` (`.html/.js/.css/.json/.xml/...`).
   Binary files (the dredge/pagefind search index) were **excluded** — matching inside
   them produced garbage over-captures.
3. **Django templates** — `templates/` (caught the hardcoded homepage video, which is
   in no other source).

Overlap: 24,118 paths appear in **both** the ES dumps and the built HTML — i.e. the ES
data and the deployed site agree almost exactly, so the ES dump is a faithful (not
bloated) catalog. Source-exclusive additions: 3 hardcoded in HTML (`o'connor` PDF+thumb,
`/images/3D/unity`), 3 in templates (`GizaHome_web.{mp4,webm,ogv}`), and ~54 in the ES
data only (mostly real `MFA-images/.../Giza_Necropolis_*` library PDFs not linked in the
current build but still referenced).

## Normalization applied

The same file appears in several encodings across sources; all were collapsed to one
canonical server-relative path:
- percent-decoding (`%20`→space, `%28`→`(`, …),
- HTML-entity decoding (`&#x27;`→`'`, `&amp;`→`&`),
- Windows→POSIX separators (`\`→`/`),
- query strings, Django template fragments (`{{…}}`), and `#` anchors stripped,
- 4 unambiguous truncation fragments dropped (their complete forms are present).

## Caveats — read before deleting anything from the drive

1. **Berlin museum (BÄM) encoding ambiguity (277 files).** These appear in three
   mojibake forms of the same prefix — `BÄM` (Latin-1), `BŽM` (MacRoman), `BÃ„M`
   (double-encoded UTF-8) — because the source data is character-set-corrupted. They
   denote the *same physical files*. Which byte-form actually exists on the drive cannot
   be determined from the repo; **reconcile `gizamedia_encoding_ambiguous.txt` against a
   real directory listing** and keep whichever form is on disk.

2. **This is a reference list, not a drive audit.** It says what the site *asks for*. It
   does not confirm each file exists on the drive (some references may already be broken
   404s), and it deliberately excludes files the site never references (those are the
   "more files than we need"). Diff this list against `find`/`ls` output from the drive to
   get the exact keep/drop sets.

3. **IIIF thumbnail cache not included.** `iiif-cache.digitalhumanities.fas.harvard.edu`
   is project-controlled but is a *cache* of IIIF derivatives and is regenerable from the
   DRS source images, so it is treated as non-preservation. Confirm this assumption if
   that cache is also hosted on the migrating drive.

## Reproduce

`catalog.py` builds `manifest_canonical.txt`; `finalize.py` produces the two deliverable
lists. Both are in this directory.
