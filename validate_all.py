#!/usr/bin/env python3
"""HEAD-probe every referenced gizamedia path (with the verified BÄM encoding fix applied)
to split the reference list into files that actually exist in hot storage vs broken 404s."""
import urllib.request, urllib.parse, ssl, sys, time
from concurrent.futures import ThreadPoolExecutor
SC = "/tmp/claude-1000/-home-dflood-repos-giza/edcf8783-3d61-4a42-9f93-115c17f0af62/scratchpad"
BASE = "https://gizamedia.rc.fas.harvard.edu"
ctx = ssl.create_default_context()

def fix(p):
    # verified on-disk encoding is UTF-8 'Ä' (%C3%84); repair mojibake prefixes
    return p.replace("BÃ„M", "BÄM").replace("BŽM", "BÄM")

def head(path):
    enc = urllib.parse.quote(path.encode("utf-8"), safe="/")
    req = urllib.request.Request(BASE + enc, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            return path, r.status
    except urllib.error.HTTPError as e:
        return path, e.code
    except Exception as e:
        return path, f"ERR:{type(e).__name__}"

raw = [l.rstrip("\n") for l in open(f"{SC}/gizamedia_files_to_preserve.txt") if l.strip()]
# skip the pure directory/app refs that aren't single files
SKIP = {"/images/3D/unity",
        "/images/UPM/UPMAA Giza records- Photo_field_negatives",
        "/images/UPM/UPMAA Giza records- Photo_field_negatives/Thumbnails"}
paths = [fix(p) for p in raw if p not in SKIP]
# dedupe after fix (mojibake variants may now collide with correct form)
seen, uniq = set(), []
for p in paths:
    if p not in seen:
        seen.add(p); uniq.append(p)

print(f"probing {len(uniq)} unique paths ({len(raw)} raw, {len(raw)-len(uniq)} skipped/merged)...", flush=True)
t0 = time.time()
results = {}
done = 0
with ThreadPoolExecutor(max_workers=32) as ex:
    for path, status in ex.map(head, uniq):
        results[path] = status
        done += 1
        if done % 2000 == 0:
            print(f"  {done}/{len(uniq)}  ({time.time()-t0:.0f}s)", flush=True)

present = sorted(p for p, s in results.items() if s == 200)
missing = sorted((s, p) for p, s in results.items() if s != 200)

with open(f"{SC}/gizamedia_present.txt", "w") as f:
    f.write("\n".join(present) + ("\n" if present else ""))
with open(f"{SC}/gizamedia_missing.txt", "w") as f:
    f.write("\n".join(f"{s}\t{p}" for s, p in missing) + ("\n" if missing else ""))

from collections import Counter
codes = Counter(s for _, s in missing)
print(f"\nDONE in {time.time()-t0:.0f}s")
print(f"  present (HTTP 200) : {len(present)}")
print(f"  not present        : {len(missing)}")
print(f"  status breakdown of not-present: {dict(codes)}")
