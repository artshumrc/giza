#!/usr/bin/env python3
"""Independent re-derivation of every giza-media object the site references.

Deliberately broader and dumber than media_catalog.py: no allow-listing of
extensions, no cleverness about what looks like an asset. Anything that names a
media host, anywhere in any file, counts. The point is to find references the
original catalog missed, so it must not share the original's assumptions.
"""
from __future__ import annotations

import re
import sys
import tarfile
import gzip
import html
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent

HOSTS = ("gizamedia.rc.fas.harvard.edu", "d1g9lvwdq3dcse.cloudfront.net")
# Grab everything after the host up to a character that cannot appear in an
# HTML attribute / JSON string value. Intentionally permissive: spaces are legal
# in these keys, so a space alone does not terminate the path.
# ')' is deliberately allowed: plenty of these filenames contain parentheses
# ("BÄM_SQ_040_044_002a(1).jpg"), and excluding it truncates a real reference
# into a dead one. The unbalanced trailing ')' from a CSS url(...) wrapper is
# stripped in canon() instead.
HOST_RE = re.compile(
    "(?:" + "|".join(re.escape(h) for h in HOSTS) + r")([^\"'<>`\n\r\t\\]*)",
    re.IGNORECASE,
)
MOJIBAKE = (("BA?M", "BÄM"), ("BŽM", "BÄM"), ("BÃ„M", "BÄM"))

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tif", ".tiff",
    ".pdf", ".mp4", ".webm", ".ogv", ".mov", ".m4v", ".mp3", ".wav", ".zip",
    ".gz", ".woff", ".woff2", ".ttf", ".eot", ".wasm", ".so", ".pyc", ".pack",
    ".idx", ".unity3d", ".assetbundle", ".dll", ".data", ".mem",
}


def canon(raw: str) -> tuple[str, bool]:
    """Normalise one raw reference to bucket-key form. Mirrors the builder."""
    value = raw
    for _ in range(3):
        d = html.unescape(value)
        if d == value:
            break
        value = d
    for _ in range(3):
        d = unquote(value)
        if d == value:
            break
        value = d
    for mangled, correct in MOJIBAKE:
        value = value.replace(mangled, correct)
    # Note: no bare '\' cut here. Some recorded paths use Windows separators
    # (percent-encoded as %5C); truncating at one turns a real file reference
    # into a directory reference and silently expands a whole subtree.
    for cut in ("?", "#", "{{", "{%", " target=", '\\"'):
        i = value.find(cut)
        if i != -1:
            value = value[:i]
    value = value.replace("\\", "/").strip()
    # Drop only parens the reference did not open itself, so a CSS url(...)
    # wrapper is removed while a genuine "(1).jpg" survives.
    while value.count(")") > value.count("(") and value.endswith(")"):
        value = value[:-1]
    while "//" in value:
        value = value.replace("//", "/")
    is_dir = value.endswith("/")
    value = value.strip("/")
    if not is_dir and value and "." not in value.rsplit("/", 1)[-1]:
        is_dir = True
    return value, is_dir


def iter_text_files(base: Path):
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in BINARY_EXT:
            continue
        yield path


def scan():
    # ref -> set of source locations, so every finding is traceable to a file.
    refs: dict[str, set[str]] = defaultdict(set)
    scanned = 0

    targets = [
        ROOT / "dist",
        ROOT / "templates",
        ROOT / "static",
        ROOT / "client",
        ROOT / "scripts",
        ROOT / "tms",
        ROOT / "search",
        ROOT / "giza",
        ROOT / "data",
        ROOT / "offline_scripts",
        ROOT / "static_site",
    ]
    for base in targets:
        if not base.exists():
            print(f"  MISSING source tree: {base}", file=sys.stderr)
            continue
        for path in iter_text_files(base):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            scanned += 1
            if "gizamedia" not in text and "d1g9lvwdq3dcse" not in text:
                continue
            rel = str(path.relative_to(ROOT))
            for match in HOST_RE.findall(text):
                refs[match].add(rel)

    # The ES export, read straight out of the tarball.
    archive = ROOT / "static_site" / "giza-es-export.tar.gz"
    if archive.exists():
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar:
                if not member.isfile():
                    continue
                fh = tar.extractfile(member)
                if fh is None:
                    continue
                raw = fh.read()
                if member.name.endswith(".gz"):
                    try:
                        raw = gzip.decompress(raw)
                    except OSError:
                        pass
                text = raw.decode("utf-8", errors="replace")
                scanned += 1
                for match in HOST_RE.findall(text):
                    refs[match].add(f"es-export:{member.name}")
    else:
        print(f"  MISSING ES export: {archive}", file=sys.stderr)

    print(f"scanned {scanned} text files; {len(refs)} distinct raw references",
          file=sys.stderr)
    return refs


def main() -> int:
    refs = scan()

    bucket_keys = set()
    for line in (ROOT / "s3_keys.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            bucket_keys.add(line)
    # NFC/NFD both ways, so an accent-normalisation difference is not a miss.
    by_nf = {}
    by_lower = {}
    for key in bucket_keys:
        by_nf.setdefault(unicodedata.normalize("NFC", key), key)
        by_nf.setdefault(unicodedata.normalize("NFD", key), key)
        by_lower.setdefault(key.lower(), key)

    prefixes = sorted(bucket_keys)
    keep = set(
        line for line in (ROOT / "keep.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    repairs = {}
    rp = ROOT / "media_path_repairs.tsv"
    if rp.exists():
        for line in rp.read_text(encoding="utf-8").splitlines():
            recorded, _, actual = line.partition("\t")
            if recorded and actual:
                repairs[recorded] = actual

    resolved: dict[str, set[str]] = defaultdict(set)   # bucket key -> sources
    # How each key was reached. A key named outright is a hard requirement; one
    # reached only by expanding a directory reference is an inference, and the
    # two must not be reported as the same kind of finding.
    via_file: set[str] = set()
    via_dir: dict[str, set[str]] = defaultdict(set)
    unresolved: dict[str, set[str]] = defaultdict(set)
    stats = Counter()

    from bisect import bisect_left

    def subtree(prefix: str) -> list[str]:
        start = bisect_left(prefixes, prefix)
        out = []
        for i in range(start, len(prefixes)):
            if not prefixes[i].startswith(prefix):
                break
            out.append(prefixes[i])
        return out

    for raw, sources in refs.items():
        key, is_dir = canon(raw)
        if not key:
            continue
        # Apply the same repair map the build applies.
        key = repairs.get(key, key)
        hit = None
        if key in bucket_keys:
            hit = key
        else:
            for variant in (
                unicodedata.normalize("NFC", key),
                unicodedata.normalize("NFD", key),
            ):
                if variant in by_nf:
                    hit = by_nf[variant]
                    break
            if hit is None and key.lower() in by_lower:
                hit = by_lower[key.lower()]
        if hit is not None:
            resolved[hit] |= sources
            via_file.add(hit)
            stats["file"] += 1
            continue
        # Directory reference: the whole subtree is in play.
        children = subtree(key.rstrip("/") + "/")
        if children:
            for child in children:
                resolved[child] |= sources
                via_dir[child] |= sources
            stats["dir"] += 1
            stats[f"dir:{key} -> {len(children)} objects"] += 1
            continue
        unresolved[key] |= sources
        stats["unresolved"] += 1

    out = Path(sys.argv[1] if len(sys.argv) > 1 else "sweep_out")
    out.mkdir(parents=True, exist_ok=True)

    missed = sorted(k for k in resolved if k not in keep)
    (out / "sweep_referenced.txt").write_text(
        "\n".join(sorted(resolved)) + "\n", encoding="utf-8")
    with (out / "sweep_missed_by_keep.tsv").open("w", encoding="utf-8") as fh:
        for key in missed:
            fh.write(f"{key}\t{';'.join(sorted(resolved[key])[:3])}\n")
    with (out / "sweep_unresolved.tsv").open("w", encoding="utf-8") as fh:
        for key in sorted(unresolved):
            fh.write(f"{key}\t{';'.join(sorted(unresolved[key])[:3])}\n")

    missed_by_file = sorted(k for k in missed if k in via_file)
    missed_by_dir = sorted(k for k in missed if k not in via_file)
    with (out / "sweep_missed_named_outright.tsv").open("w", encoding="utf-8") as fh:
        for key in missed_by_file:
            fh.write(f"{key}\t{';'.join(sorted(resolved[key])[:3])}\n")

    for label, count in sorted(stats.items()):
        if label.startswith("dir:"):
            print(f"  directory ref: {label[4:]}")
    print(f"raw refs resolved as: file={stats['file']} dir={stats['dir']} "
          f"unresolved={stats['unresolved']}")
    print(f"distinct bucket objects referenced (independent sweep): {len(resolved)}")
    print(f"keep.txt size: {len(keep)}")
    print(f"MISSED, named outright by a reference: {len(missed_by_file)}  <-- must be zero")
    print(f"MISSED, only via directory-ref expansion: {len(missed_by_dir)}")
    print(f"unresolved references: {len(unresolved)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
