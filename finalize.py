#!/usr/bin/env python3
"""Turn the canonical manifest into the final deliverables."""
import re
SC = "/tmp/claude-1000/-home-dflood-repos-giza/edcf8783-3d61-4a42-9f93-115c17f0af62/scratchpad"

paths = [l.rstrip("\n") for l in open(f"{SC}/manifest_canonical.txt") if l.strip()]

# 4 unambiguous truncation fragments (single-quote / '?' delimiter artifacts) whose
# complete forms are already present elsewhere in the list. Drop these.
JUNK = {
    "/documents/o",
    "/documents/Thumbnails/o",
    "/images/BŽM/Giza_Abklatsche_TIFF/Kiste2/BA",
    "/images/BŽM/Giza_Abklatsche_TIFF/Kiste2/Thumbnails/BA",
}
clean = sorted(p for p in paths if p not in JUNK)

with open(f"{SC}/gizamedia_files_to_preserve.txt", "w") as f:
    f.write("\n".join(clean) + "\n")

# encoding-ambiguous subset (BÄM / BÃ„M / BŽM mojibake families) — same physical files,
# uncertain byte-form; reconcile against a real drive listing.
amb = [p for p in clean if any(ord(c) > 127 for c in p)]
with open(f"{SC}/gizamedia_encoding_ambiguous.txt", "w") as f:
    f.write("\n".join(sorted(amb)) + "\n")

# thumbnails vs originals split (handy for tiering)
thumbs = [p for p in clean if "/thumbnails/" in p.lower() or "_thumb." in p.lower()]
origs  = [p for p in clean if p not in set(thumbs)]

print(f"final files to preserve : {len(clean)}")
print(f"  originals             : {len(origs)}")
print(f"  thumbnails            : {len(thumbs)}")
print(f"encoding-ambiguous (BÄM): {len(amb)}")
print("wrote:")
print("  gizamedia_files_to_preserve.txt")
print("  gizamedia_encoding_ambiguous.txt")
