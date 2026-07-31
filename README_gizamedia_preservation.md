# giza-media preservation and the media move to CloudFront

**Question answered:** which files on the retiring media drive
(`gizamedia.rc.fas.harvard.edu` — "a drive with a web server in front of it") does
the Giza website actually need, so the rest can be pruned from the `giza-media`
S3 bucket that replaced it.

Everything here is produced by `media_catalog.py`. It supersedes the earlier
`catalog.py` / `finalize.py` / `compare_s3_media.py` chain, which under-counted
(see *What the first pass missed*).

## Result

Of **223,093** objects in the bucket, **24,303** are needed.

| | count |
|---|---|
| directly referenced | 21,865 |
| referenced under a path the records get wrong | 2,201 |
| inside a referenced application directory | 230 |
| thumbnail twin of a kept original | 7 |
| **keep** | **24,303** |
| **prunable** | **198,790** |

`keep_reasons.tsv` and `prune_reasons.tsv` give the reason for every object.

## Files

- **`keep.txt`** — the preservation allow-list. Do not delete anything on it.
- **`prunable.txt`** — everything else in the bucket.
- **`prune_reasons.tsv`** — why each object is prunable. Read this before deleting:
  `unlinked-app` (669) are complete, working applications the site simply never
  links to, and `master-or-tiff` (45,119) are the originals behind kept
  derivatives. Neither is safe to delete on a script's say-so.
- **`missing_from_s3.txt`** — 143 references with no file anywhere. Each was
  probed against the live origin and 404s there too, so these are long-standing
  dead links, not gaps in the migration. 24 are 3D viewer applications that were
  never on the drive.
- **`media_path_repairs.tsv`** — **a build input, not a report.** See below.
- **`s3_keys.txt`** — the bucket listing the catalog resolves against.
  Regenerate with `aws s3 ls s3://giza-media/ --recursive > s3_raw.txt`.

## Broken links the move fixed

2,275 paths in the TMS records point at files that exist under a different name.
`media_path_repairs.tsv` maps each recorded path onto the real object, and
`static_site_builder.media` applies it while rewriting URLs, so the site links to
the file instead of a 404.

| fault | links |
|---|---|
| `3D Model Textures` folder renamed `…_remove from TMS Collections` | 1,486 |
| `Avatars` folder renamed `…_PDM broke all links_remove from TMS Collections` | 370 |
| trailing space in the folder name `G 7530-7540 ` | 343 |
| accents stored decomposed (NFD) where the records use NFC | 67 |
| case mismatches (`.jpg`/`.JPG`, `GPh`/`GPH`) | 9 |

Separately, the Berlin museum prefix survives in the records as `BŽM`, `BA?M`,
and `BÃ„M`; all are normalised to `BÄM` before the path is read. That is code
(`MEDIA_MOJIBAKE_REPAIRS`) rather than a map row, because the `BA?M` spelling
contains a literal `?` that would otherwise be taken for a query string and
truncate the path. Normalising it surfaced 2,197 references no earlier scan
could see.

Net effect: media links that resolve went from 21,603 to 24,064 of 24,178 —
**89.3% to 99.5%**, across 1,620 pages. None of these worked on the old host
either; this fixes long-broken links rather than repairing migration damage.

**If `media_path_repairs.tsv` is absent the build still succeeds** and silently
re-emits every one of those dead links. The build logs `Media path repairs
loaded: N` on startup, and warns when the file is missing.

## Which host, and why only this one

| host | role | in scope? |
|---|---|---|
| `gizamedia.rc.fas.harvard.edu` | non-IIIF media on a plain web server | **yes — now `giza-media` behind CloudFront** |
| `nrs.harvard.edu`, `ids.lib.harvard.edu` | Harvard DRS — IIIF-served | no (managed) |
| `iiif-cache.digitalhumanities.fas.harvard.edu` | project IIIF thumbnail cache | no (regenerable) |
| fonts / CDNs / analytics / funder and partner links | not our media | no |

The IIIF cache no longer fronts these images: CloudFront is already a CDN, and
the cache was verified to be a byte-identical pass-through rather than a resizer.
It still fronts `ids.lib` and `nrs`, which we do not control.

## Sources scanned

1. **ES export** — `static_site/giza-es-export.tar.gz`. Confirmed that no media
   field holds a host-less path, so anchoring on the host misses nothing.
2. **The built site** — every text file under `dist/`. Build before cataloguing;
   without it the run warns and the result is not safe to prune by.
3. **Repo sources** — `templates/`, `static/`, `scripts/`, `tms/`. Catches paths
   hardcoded outside the data.
4. **The bucket's own files** — the parseable objects, followed transitively.
   This is the one the first pass lacked.

## What the first pass missed

Worth recording, because both failures were silent:

- **Directory references.** `/images/3D/unity/` is an iframe `src`, not a file.
  Reducing it to `/images/3D/unity` matched no object key, so all 89 files of the
  live Giza 3D viewer were marked prunable.
- **References that exist only inside the bucket.** `images/3D/unity/index.html`
  loads `TemplateData/*.js`, `Build/WebGL.wasm`, and a directory of bare-named
  Unity assetbundles. Nothing outside the bucket names them, and nothing had
  parsed the media files themselves.
- **Unresolvable references were dropped rather than reported**, so the run
  claimed 3 missing files when the real number was 2,641.

`media_catalog.py` resolves a directory reference to its whole subtree, follows
references between objects to a fixpoint, and treats any directory with an HTML
entry point as a self-contained application whose subtree is kept — because
assetbundles, .NET assemblies, and `.nib` resources are loaded by name at runtime
and no static parse will find them.

Where a recorded path does not resolve, it walks the path against the real tree
and accepts a rename only when exactly one real child differs by whitespace,
case, a `_suffix`, or a mojibake round-trip. Ambiguity fails rather than guesses.

## Reproduce

```
aws s3 ls s3://giza-media/ --recursive > s3_raw.txt   # refresh the listing
uv run poe static-build-production                    # dist/ must exist
python media_catalog.py --bucket-text-dir <mirror>
```

`--bucket-text-dir` is a local mirror of the bucket's parseable objects
(`.html/.js/.css/.json/.xml`, ~144 files) used to follow references between them.
Without it the transitive pass is skipped and **the result is not safe to prune
by** — the run says so.
