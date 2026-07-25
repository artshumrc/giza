#!/usr/bin/env python3
"""Build a canonical manifest of gizamedia.rc.fas.harvard.edu files referenced by the Giza site.

Sources:
  1. ES export ndjson dumps (giza + iiif)  -- JSON, values are clean/raw
  2. Built static site HTML (dist/)         -- percent- and HTML-entity-encoded
  3. Django templates (templates/)          -- hard-coded, may contain template vars

Output canonical form: the server-relative file path (what actually lives on the drive),
decoded to raw UTF-8, with '\\' normalized to '/'. Query strings / template fragments stripped.
"""
import gzip, re, json, html, sys
from urllib.parse import unquote
from collections import defaultdict

HOST = "gizamedia.rc.fas.harvard.edu"
REPO = "/home/dflood/repos/giza"
ES = f"/tmp/claude-1000/-home-dflood-repos-giza/edcf8783-3d61-4a42-9f93-115c17f0af62/scratchpad/es/giza-es-export"

# raw-URL matcher: capture everything after host up to a hard delimiter.
# NOTE: space is allowed (real paths contain spaces); stops at quotes/brackets/whitespace-newline.
URL_RE = re.compile(r'https?:(?://|\\/\\/)?//?' + re.escape(HOST) + r'([^"\'<>`)\n\r\t]*)')
# simpler: find host then grab path
HOST_RE = re.compile(re.escape(HOST) + r'([^"\'<>`\n\r\t]*)')

def canon(raw_path):
    """raw_path = substring immediately after HOST (may start with / or //)."""
    p = raw_path
    # 1. decode HTML entities FIRST (&#x27; -> ', &amp; -> &) so entity '#' isn't mistaken for a fragment
    p = html.unescape(p)
    # 2. percent-decode (%20 -> space, %C3%.. -> raw bytes, %28 -> '(')
    p = unquote(p)
    # 3. strip query strings / django-template fragments / bare '#' anchors.
    #    NB filenames here don't contain literal '?' or '#'; the only '?' cases are the unity
    #    viewer query and already-corrupt BA?M paths (which have a clean BÄM twin from ES).
    for cut in ('?', '#', '{{', '{%', ' target='):
        i = p.find(cut)
        if i != -1:
            p = p[:i]
    # 4. windows path separators -> posix
    p = p.replace('\\', '/')
    p = p.strip()
    p = p.rstrip('/')             # drop trailing slash (dir refs like /images/3D/unity)
    while '//' in p:
        p = p.replace('//', '/')
    if not p.startswith('/'):
        p = '/' + p
    return p

def valid(c):
    if not c or c == '/':
        return False
    # must be a real media path root
    low = c.lower()
    if not (low.startswith('/images/') or low.startswith('/documents/')):
        return False
    # reject over-capture from binary blobs / concatenated urls
    if '�' in c:                       # unicode replacement char = binary garbage
        return False
    if 'http' in c[1:].lower():             # a second URL concatenated in
        return False
    if any(ord(ch) < 32 for ch in c):       # control chars
        return False
    if len(c) > 300:
        return False
    return True

def add_from_text(text, sink):
    for m in HOST_RE.finditer(text):
        c = canon(m.group(1))
        if valid(c):
            sink.add(c)

es_set = set()
dist_set = set()
tpl_set = set()

# 1. ES dumps
for fn in (f"{ES}/giza.ndjson.gz", f"{ES}/iiif.ndjson.gz"):
    with gzip.open(fn, 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            if HOST in line:
                add_from_text(line, es_set)

# 2. dist -- text files only (skip binary search-index blobs that cause over-capture)
import os
TEXT_EXT = ('.html', '.htm', '.js', '.css', '.json', '.xml', '.txt', '.webmanifest', '.svg')
for root, _, files in os.walk(f"{REPO}/dist"):
    for name in files:
        if not name.lower().endswith(TEXT_EXT):
            continue
        fp = os.path.join(root, name)
        try:
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                t = f.read()
        except Exception:
            continue
        if HOST in t:
            add_from_text(t, dist_set)

# 3. templates
for root, _, files in os.walk(f"{REPO}/templates"):
    for name in files:
        fp = os.path.join(root, name)
        try:
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                t = f.read()
        except Exception:
            continue
        if HOST in t:
            add_from_text(t, tpl_set)

union = es_set | dist_set | tpl_set

SC = "/tmp/claude-1000/-home-dflood-repos-giza/edcf8783-3d61-4a42-9f93-115c17f0af62/scratchpad"
with open(f"{SC}/manifest_canonical.txt", "w") as f:
    for p in sorted(union):
        f.write(p + "\n")

def stats(name, s):
    print(f"{name:22} {len(s):>7}")

print("=== distinct canonical file paths ===")
stats("ES dumps", es_set)
stats("dist HTML", dist_set)
stats("templates", tpl_set)
stats("UNION (to preserve)", union)
print()
print("=== overlap ===")
print(f"in ES and dist:        {len(es_set & dist_set)}")
print(f"ES only (not in dist): {len(es_set - dist_set)}")
print(f"dist only (hardcoded): {len(dist_set - es_set)}")
print(f"template only:         {len(tpl_set - es_set - dist_set)}")
print()
print("=== by top-level dir ===")
top = defaultdict(int)
for p in union:
    parts = p.strip('/').split('/')
    top[parts[0] if parts else ''] += 1
for k, v in sorted(top.items(), key=lambda x:-x[1]):
    print(f"  {k:15} {v}")
print()
print("=== by extension ===")
ext = defaultdict(int)
for p in union:
    m = re.search(r'\.([A-Za-z0-9]{1,5})$', p)
    ext[m.group(1).lower() if m else '(none)'] += 1
for k, v in sorted(ext.items(), key=lambda x:-x[1]):
    print(f"  {k:10} {v}")
print()
thumbs = sum(1 for p in union if '/thumbnails/' in p.lower() or '_thumb.' in p.lower())
print(f"=== thumbnails: {thumbs}   originals: {len(union)-thumbs} ===")
print()
print("=== entries with non-ASCII or replacement char (encoding-ambiguous, need manual check) ===")
amb = [p for p in union if any(ord(ch) > 127 for ch in p)]
print(f"count: {len(amb)}")
for p in sorted(amb)[:15]:
    print("  ", p)
with open(f"{SC}/manifest_ambiguous.txt","w") as f:
    for p in sorted(amb):
        f.write(p+"\n")
