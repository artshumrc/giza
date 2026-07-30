#!/usr/bin/env python3
"""Compare gizamedia_files_to_preserve.txt against the giza-media S3 bucket.

Regenerate the bucket listing with:
    aws s3 ls s3://giza-media/ --recursive > s3_raw.txt

Then run this script. Outputs, all relative to the repo root:
    s3_keys.txt          every key in the bucket
    keep.txt             preserve-list entries present in the bucket
    missing_from_s3.txt  preserve-list entries NOT in the bucket (investigate!)
    case_mismatch.tsv    missing entries that match a bucket key case-insensitively
    prunable.txt         bucket objects not on the preserve list
"""
import os
import re
from collections import Counter
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
PRESERVE = os.path.join(HERE, "gizamedia_files_to_preserve.txt")
S3_RAW = os.path.join(HERE, "s3_raw.txt")


def out(name):
    return os.path.join(HERE, name)


def norm(p):
    return unquote(p.strip()).lstrip("/")


# `aws s3 ls --recursive` lines are: date time size key
keys = []
for line in open(S3_RAW):
    m = re.match(r"^\S+\s+\S+\s+\d+\s+(.*)$", line.rstrip("\n"))
    if m:
        keys.append(m.group(1))
with open(out("s3_keys.txt"), "w") as f:
    f.write("".join(k + "\n" for k in keys))

preserve_raw = [l for l in open(PRESERVE) if l.strip()]
preserve = {norm(l) for l in preserve_raw}
s3 = {norm(k) for k in keys}

missing = sorted(preserve - s3)    # must-keep but absent from the bucket -> problem
prunable = sorted(s3 - preserve)   # in the bucket, not on the keep list
kept = preserve & s3

s3_ci = {k.lower(): k for k in s3}
ci_matches = {m: s3_ci[m.lower()] for m in missing if m.lower() in s3_ci}

print(f"preserve list lines      : {len(preserve_raw)} ({len(preserve)} unique)")
print(f"s3 objects               : {len(s3)}")
print(f"preserved found in s3    : {len(kept)}")
print(f"preserved MISSING from s3: {len(missing)}  (case-only mismatches: {len(ci_matches)})")
print(f"s3 objects NOT preserved : {len(prunable)}")

with open(out("missing_from_s3.txt"), "w") as f:
    f.write("".join(m + "\n" for m in missing))
with open(out("case_mismatch.tsv"), "w") as f:
    for k, v in sorted(ci_matches.items()):
        f.write(f"{k}\t{v}\n")
with open(out("prunable.txt"), "w") as f:
    f.write("".join(p + "\n" for p in prunable))
with open(out("keep.txt"), "w") as f:
    f.write("".join(k + "\n" for k in sorted(kept)))


def pref(k, n=2):
    return "/".join(k.split("/")[:n])


pc, kc = Counter(map(pref, prunable)), Counter(map(pref, kept))
print("\nprefix                        prunable     keep")
for p, c in pc.most_common(25):
    print(f"{p:<30}{c:>8} {kc.get(p, 0):>8}")
