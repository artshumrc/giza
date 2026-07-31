#!/usr/bin/env python3
"""Decide which giza-media objects the site needs, conservatively.

Supersedes the catalog.py / finalize.py pair, which only looked for the media
host in the ES export, the built site, and the Django templates. That misses two
whole classes of reference and is why the Giza 3D viewers ended up on the prune
list:

  * A reference can name a *directory* -- ``/images/3D/unity/`` is an iframe src,
    not a file. The old canonicaliser reduced it to ``/images/3D/unity``, which
    matches no object key, so all 89 files of the app looked unreferenced.
  * A referenced file can pull in others that nothing outside the bucket ever
    names. ``images/3D/unity/index.html`` loads TemplateData/*.js and *.png,
    Build/*.wasm, and a directory of bare-named Unity assetbundles. Those only
    appear inside files that live in the bucket, which nothing ever parsed.

So this walks references transitively and treats a directory reference as
covering its whole subtree. Where it has to guess it guesses toward keeping, and
puts the guess in its own tier so the decision stays visible.

Usage:
    python media_catalog.py --bucket-text-dir <dir>   # mirror of parseable objects

Inputs are the repo's s3_keys.txt (from `aws s3 ls s3://giza-media/ --recursive`),
the ES export, the built dist/, and the repo's own sources.
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import sys
import tarfile
import unicodedata
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent

# Every host that has served these paths. The path after the host is the object
# key, so a reference to any of them resolves the same way.
MEDIA_HOSTS = (
    "gizamedia.rc.fas.harvard.edu",
    "d1g9lvwdq3dcse.cloudfront.net",
)
HOST_RE = re.compile(
    "(?:" + "|".join(re.escape(h) for h in MEDIA_HOSTS) + r")([^\"'<>`\n\r\t]*)"
)

# Objects worth parsing for references to further objects.
PARSEABLE_EXT = (".html", ".htm", ".js", ".css", ".json", ".xml", ".manifest", ".svg")

# Extensions a bare quoted string must have before we treat it as a file
# reference. Without this every English word in a script becomes a candidate.
ASSET_EXT = (
    "html|htm|js|css|json|xml|txt|csv|manifest|svg|png|jpg|jpeg|gif|webp|ico|bmp|tif|"
    "tiff|pdf|mp4|webm|ogv|ogg|mov|m4v|mp3|wav|data|wasm|mem|memgz|jsgz|datagz|unity3d|"
    "assetbundle|dll|zip"
)
REF_PATTERNS = (
    # attribute / property assignments: src="x", href='x', url: "x"
    re.compile(
        r"""(?:src|href|url|poster|data-src|dataUrl|codeUrl|frameworkUrl|loaderUrl|"""
        r"""streamingAssetsUrl|memoryUrl|symbolsUrl|asmUrl|dataFile|scriptFile)"""
        r"""\s*[:=]\s*["']([^"']+)["']""",
        re.IGNORECASE,
    ),
    # CSS url(...)
    re.compile(r"""url\(\s*["']?([^"'()]+)["']?\s*\)""", re.IGNORECASE),
    # any quoted string that looks like a file with a known asset extension
    re.compile(r"""["']([^"'<>\n\r\t]{1,200}\.(?:""" + ASSET_EXT + r"""))["']""",
               re.IGNORECASE),
)
SKIP_REF_PREFIXES = ("data:", "javascript:", "mailto:", "tel:", "blob:", "#", "about:")


def canon(raw: str) -> tuple[str, bool]:
    """Normalise a raw reference to bucket-key form.

    Returns the key and whether the reference looked like a directory (it ended
    in a slash, or was a bare path with no extension).
    """
    value = raw
    # Entities first, so an entity-encoded '#' is not mistaken for a fragment.
    for _ in range(3):
        decoded = html.unescape(value)
        if decoded == value:
            break
        value = decoded
    # Percent-decode. No object key contains a literal '%', so decoding until
    # stable is safe and handles the doubly-encoded iiif-cache ``?url=`` form.
    for _ in range(3):
        decoded = unquote(value)
        if decoded == value:
            break
        value = decoded
    # Before anything is treated as a query string: the BA?M spelling of BÄM
    # carries a literal '?' in the middle of a filename, and cutting there would
    # silently truncate the reference to nothing.
    for mangled, correct in MOJIBAKE:
        if mangled in value:
            value = value.replace(mangled, correct)
    for cut in ("?", "#", "{{", "{%", " target=", '\\"'):
        index = value.find(cut)
        if index != -1:
            value = value[:index]
    value = value.replace("\\", "/").strip()
    while "//" in value:
        value = value.replace("//", "/")
    is_dir = value.endswith("/")
    value = value.strip("/")
    if not is_dir and value and "." not in value.rsplit("/", 1)[-1]:
        # No extension on the last segment: a directory reference, or one of the
        # bare-named Unity assetbundles. Either way, try it both ways.
        is_dir = True
    return value, is_dir


def plausible(key: str) -> bool:
    if not key:
        return False
    lowered = key.lower()
    if not (lowered.startswith("images/") or lowered.startswith("documents/")):
        return False
    if "�" in key or "http" in lowered[1:]:
        return False
    if any(ord(char) < 32 for char in key):
        return False
    return len(key) <= 300


# Mojibake families in the TMS data. The same physical folder is spelled several
# ways depending on which encoding round-trip mangled it; the drive spells it BÄM.
MOJIBAKE = (("BŽM", "BÄM"), ("BÃ„M", "BÄM"), ("BA?M", "BÄM"), ("BÃM", "BÄM"))


def segment_variants(segment: str) -> list[str]:
    """Spellings of a path segment worth trying when the exact one is absent."""
    out = [segment.strip(), unicodedata.normalize("NFC", segment),
           unicodedata.normalize("NFD", segment)]
    for bad, good in MOJIBAKE:
        if bad in segment:
            out.append(segment.replace(bad, good))
    return out


class Bucket:
    """The object listing, with prefix and fuzzy lookup."""

    def __init__(self, keys: list[str]) -> None:
        self.keys = sorted(keys)
        self.exact = set(self.keys)
        self.by_lower: dict[str, str] = {}
        self.by_nfc: dict[str, str] = {}
        for key in self.keys:
            self.by_lower.setdefault(key.lower(), key)
            self.by_nfc.setdefault(unicodedata.normalize("NFC", key), key)
        # prefix -> the child segment names directly under it
        self.children: dict[str, set[str]] = defaultdict(set)
        for key in self.keys:
            parts = key.split("/")
            for depth in range(len(parts)):
                self.children["/".join(parts[:depth])].add(parts[depth])

    def repair(self, path: str) -> str | None:
        """Walk ``path`` against the real tree, healing one segment at a time.

        Folders on the source drive have been renamed since the TMS records were
        written -- annotated with suffixes like ``_remove from TMS Collections``,
        given a trailing space, or mangled by an encoding round-trip. At each
        level, if the recorded segment is absent, accept the single real child
        that differs only in one of those ways. Ambiguity fails rather than
        guesses, so a repair is only ever made when there is exactly one answer.
        """
        prefix = ""
        for segment in path.split("/"):
            here = self.children.get(prefix)
            if not here:
                return None
            if segment in here:
                prefix = f"{prefix}/{segment}" if prefix else segment
                continue
            candidates = {c for c in here if c in segment_variants(segment)}
            if not candidates:
                stripped = segment.strip()
                candidates = {
                    c for c in here
                    if c.startswith(f"{stripped}_") or c.lower() == stripped.lower()
                }
            if len(candidates) != 1:
                return None
            resolved = candidates.pop()
            prefix = f"{prefix}/{resolved}" if prefix else resolved
        return prefix

    def subtree(self, prefix: str) -> list[str]:
        """Every key under ``prefix`` treated as a directory."""
        prefix = prefix.rstrip("/") + "/"
        start = bisect_left(self.keys, prefix)
        out = []
        for key in self.keys[start:]:
            if not key.startswith(prefix):
                break
            out.append(key)
        return out

    def resolve(self, key: str, is_dir: bool) -> tuple[list[str], str]:
        """Resolve a reference to object keys. Returns (keys, how)."""
        if not is_dir and key in self.exact:
            return [key], "file"
        subtree = self.subtree(key)
        if subtree:
            return subtree, "subtree"
        if key in self.exact:
            return [key], "file"
        # Same file, different byte-form: NFC/NFD accents or a case difference.
        for variant, how in (
            (unicodedata.normalize("NFC", key), "nfc"),
            (unicodedata.normalize("NFD", key), "nfd"),
        ):
            if variant in self.exact:
                return [variant], how
            match = self.by_nfc.get(variant)
            if match:
                return [match], how
        match = self.by_lower.get(key.lower())
        if match:
            return [match], "case"
        # Last resort: the recorded path no longer matches the drive layout.
        repaired = self.repair(key)
        if repaired:
            if repaired in self.exact:
                return [repaired], "repaired"
            subtree = self.subtree(repaired)
            if subtree:
                return subtree, "repaired-subtree"
        return [], "missing"


def iter_text_files(root: Path, extensions: tuple[str, ...] | None = None):
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if extensions and not name.lower().endswith(extensions):
                continue
            path = Path(dirpath) / name
            try:
                yield path, path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue


def seeds_from_text(text: str, sink: dict[str, set[str]], origin: str) -> None:
    for match in HOST_RE.finditer(text):
        key, is_dir = canon(match.group(1))
        if plausible(key):
            sink[origin].add(f"{int(is_dir)}{key}")


def collect_seeds(args: argparse.Namespace) -> dict[str, set[str]]:
    """Every direct reference to the media host, by where it was found."""
    seeds: dict[str, set[str]] = defaultdict(set)

    archive = HERE / args.es_archive
    if archive.exists():
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not member.name.endswith(".ndjson.gz"):
                    continue
                handle = tar.extractfile(member)
                if handle is None:
                    continue
                with gzip.open(handle, "rt", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if any(host in line for host in MEDIA_HOSTS):
                            seeds_from_text(line, seeds, "es")
    else:
        print(f"WARNING: {archive} not found; skipping the ES export", file=sys.stderr)

    dist = HERE / args.dist
    if dist.exists():
        text_ext = (
            ".html", ".htm", ".js", ".css", ".json", ".xml", ".txt", ".webmanifest",
            ".svg",
        )
        for _, text in iter_text_files(dist, text_ext):
            if any(host in text for host in MEDIA_HOSTS):
                seeds_from_text(text, seeds, "dist")
    else:
        print(
            f"WARNING: {dist} not found; build the site first so the emitted "
            "HTML is covered",
            file=sys.stderr,
        )

    # Repo sources: hardcoded references in templates, stylesheets, and scripts
    # that a data-driven scan would never see.
    for name in ("templates", "static", "scripts", "tms", "client", "offline_scripts"):
        root = HERE / name
        if not root.exists():
            continue
        for _, text in iter_text_files(root):
            if any(host in text for host in MEDIA_HOSTS):
                seeds_from_text(text, seeds, f"repo:{name}")

    return seeds


def expand(
    bucket: Bucket, seeds: set[str]
) -> tuple[dict[str, str], list[str], list[tuple[str, str]]]:
    """Resolve seeds, then follow references inside the bucket to a fixpoint."""
    kept: dict[str, str] = {}
    missing: list[str] = []
    repairs: list[tuple[str, str]] = []
    pending: list[str] = []

    def add(keys: list[str], tier: str) -> None:
        for key in keys:
            if key not in kept:
                kept[key] = tier
                if key.lower().endswith(PARSEABLE_EXT):
                    pending.append(key)

    for seed in sorted(seeds):
        is_dir, key = seed[0] == "1", seed[1:]
        keys, how = bucket.resolve(key, is_dir)
        if not keys:
            missing.append(key)
            continue
        if how in {"file", "nfc", "nfd", "case"}:
            tier = "referenced"
        elif how.startswith("repaired"):
            tier = "repaired"
        else:
            tier = "subtree"
        # Any byte-level difference between the recorded path and the real key
        # has to be recorded, not just the folder renames: S3 matches keys byte
        # for byte, so an accented name stored decomposed will not answer to the
        # composed spelling the records use, however alike they look.
        if len(keys) == 1 and keys[0] != key:
            repairs.append((key, keys[0]))
            tier = "repaired"
        add(keys, tier)

    # An HTML entry point means the directory is a self-contained application
    # whose parts are loaded by name at runtime (Unity assetbundles, .NET
    # assemblies, .nib resources). Static parsing cannot see those, so keep the
    # whole subtree.
    for key in list(kept):
        if key.lower().endswith((".html", ".htm")):
            add(bucket.subtree(key.rsplit("/", 1)[0]), "app-subtree")

    app_roots = {
        key.rsplit("/", 1)[0] for key in kept if key.lower().endswith((".html", ".htm"))
    }

    while pending:
        key = pending.pop()
        text = read_bucket_text(key)
        if text is None:
            continue
        base = key.rsplit("/", 1)[0] if "/" in key else ""
        # Some of these apps write stylesheet URLs relative to the page rather
        # than to the stylesheet, so a ref that does not resolve beside its own
        # file gets a second try from the entry point's directory.
        root = next(
            (r for r in sorted(app_roots, key=len, reverse=True)
             if base == r or base.startswith(f"{r}/")),
            base,
        )
        for pattern in REF_PATTERNS:
            for match in pattern.finditer(text):
                ref = match.group(1).strip()
                if not ref or ref.lower().startswith(SKIP_REF_PREFIXES):
                    continue
                if "://" in ref and not any(host in ref for host in MEDIA_HOSTS):
                    continue
                if any(host in ref for host in MEDIA_HOSTS):
                    target, is_dir = canon(HOST_RE.search(ref).group(1))
                    bases: tuple[str, ...] = ("",)
                else:
                    target, is_dir = canon(join(base, ref))
                    bases = (base, root)
                for attempt, origin in enumerate(bases):
                    if attempt:
                        target, is_dir = canon(join(origin, ref))
                    if not plausible(target):
                        continue
                    keys, _ = bucket.resolve(target, is_dir)
                    if keys:
                        add(keys, "transitive")
                        break
                else:
                    if plausible(target):
                        missing.append(target)

    return kept, missing, repairs


def join(base: str, ref: str) -> str:
    if ref.startswith("/"):
        return ref
    parts = [p for p in base.split("/") if p]
    for part in ref.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


_TEXT_DIR: Path | None = None


def read_bucket_text(key: str) -> str | None:
    if _TEXT_DIR is None:
        return None
    path = _TEXT_DIR / key
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def add_thumbnail_siblings(bucket: Bucket, kept: dict[str, str]) -> None:
    """Keep the Thumbnails/<stem>_thumb.* twin of every kept original.

    Some pages build a thumbnail path from the original rather than reading it
    from a field, so the twin can be needed without ever being named.
    """
    index: dict[str, list[str]] = defaultdict(list)
    for key in bucket.keys:
        folder, _, name = key.rpartition("/")
        if folder.lower().endswith("/thumbnails"):
            index[folder.rsplit("/", 1)[0].lower()].append(key)
    for key in list(kept):
        folder, _, name = key.rpartition("/")
        if folder.lower().endswith("/thumbnails"):
            continue
        stem = name.rsplit(".", 1)[0].lower()
        for candidate in index.get(folder.lower(), ()):
            cand_stem = candidate.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
            if cand_stem in (stem, f"{stem}_thumb") and candidate not in kept:
                kept[candidate] = "thumbnail-sibling"


OS_JUNK = ("thumbs.db", ".ds_store", "desktop.ini")
APP_MARKERS = (
    ".html", ".htm", ".dll", ".nib", ".jsgz", ".memgz", ".unity3d", ".wasm", ".ress",
)


def classify_prune(bucket: Bucket, kept: dict[str, str], prune: list[str]) -> dict[str, str]:
    """Label each prunable object with why it is unreferenced.

    Not everything unreferenced is equally safe to delete. A stray JPEG nobody
    links to is one thing; a complete 3D viewer whose entry point the site
    simply never got a link to is another, and so is the TIFF master behind a
    kept derivative. Deletion is irreversible, so the reason travels with the
    key and a human decides.
    """
    app_dirs = set()
    for key in bucket.keys:
        if key.lower().endswith(APP_MARKERS):
            app_dirs.add(key.rsplit("/", 1)[0])
    kept_dirs = {key.rsplit("/", 1)[0] for key in kept}
    kept_stems = {
        (key.rsplit("/", 1)[0], key.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower())
        for key in kept
    }

    labels: dict[str, str] = {}
    for key in prune:
        folder, _, name = key.rpartition("/")
        lowered = name.lower()
        if lowered in OS_JUNK:
            labels[key] = "os-junk"
        elif any(folder == d or folder.startswith(f"{d}/") for d in app_dirs):
            labels[key] = "unlinked-app"
        elif "/masters/" in f"/{key.lower()}" or lowered.endswith((".tif", ".tiff")):
            labels[key] = "master-or-tiff"
        elif (folder, lowered.rsplit(".", 1)[0]) in kept_stems:
            labels[key] = "variant-of-kept"
        elif folder in kept_dirs:
            labels[key] = "beside-kept"
        else:
            labels[key] = "unreferenced"
    return labels


def main(argv: list[str]) -> int:
    global _TEXT_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-keys", default="s3_keys.txt")
    parser.add_argument("--es-archive", default="static_site/giza-es-export.tar.gz")
    parser.add_argument("--dist", default="dist")
    parser.add_argument(
        "--bucket-text-dir",
        help=(
            "Local mirror of the bucket's parseable objects (html/js/css/json/"
            "xml), used to follow references between objects. Without it the "
            "transitive pass is skipped and the result is NOT safe to prune by."
        ),
    )
    args = parser.parse_args(argv)

    if args.bucket_text_dir:
        _TEXT_DIR = Path(args.bucket_text_dir)

    keys = [line.rstrip("\n") for line in open(HERE / args.s3_keys, encoding="utf-8")
            if line.strip()]
    bucket = Bucket(keys)
    print(f"bucket objects            : {len(bucket.keys):,}")

    seeds = collect_seeds(args)
    all_seeds: set[str] = set()
    for origin, found in sorted(seeds.items()):
        print(f"  references from {origin:<12}: {len(found):,}")
        all_seeds |= found
    print(f"distinct references       : {len(all_seeds):,}")

    if _TEXT_DIR is None:
        print(
            "WARNING: no --bucket-text-dir; references between objects in the "
            "bucket were NOT followed",
            file=sys.stderr,
        )

    kept, missing, repairs = expand(bucket, all_seeds)
    add_thumbnail_siblings(bucket, kept)

    tiers = Counter(kept.values())
    print("\nkeep, by why:")
    for tier, count in tiers.most_common():
        print(f"  {tier:<18} {count:>8,}")
    print(f"  {'TOTAL':<18} {len(kept):>8,}")

    prune = [key for key in bucket.keys if key not in kept]
    prune_labels = classify_prune(bucket, kept, prune)
    print(f"\nprunable                  : {len(prune):,}")
    for label, count in Counter(prune_labels.values()).most_common():
        print(f"  {label:<18} {count:>8,}")
    missing = sorted(set(missing))
    print(f"referenced but absent     : {len(missing):,}")
    print(f"broken links with a target: {len(repairs):,}")

    # These are the filenames the repo has always used for the keep/prune
    # decision. This script writes them directly rather than to a parallel set,
    # so there is never a second, staler answer to "is this object needed?".
    written = [
        ("keep.txt", sorted(kept)),
        ("prunable.txt", prune),
        ("missing_from_s3.txt", missing),
        ("keep_reasons.tsv", [f"{t}\t{k}" for k, t in sorted(kept.items())]),
        ("prune_reasons.tsv", [f"{prune_labels[k]}\t{k}" for k in prune]),
        # Consumed by the build (see static_site_builder.media): each row
        # rewrites a path the data records onto the object holding the file.
        ("media_path_repairs.tsv",
         [f"{ref}\t{target}" for ref, target in sorted(set(repairs))]),
    ]
    for name, lines in written:
        write(name, lines)
    print("\nwrote " + ", ".join(name for name, _ in written))
    return 0


def write(name: str, lines: list[str]) -> None:
    with open(HERE / name, "w", encoding="utf-8") as handle:
        handle.write("".join(line + "\n" for line in lines))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
