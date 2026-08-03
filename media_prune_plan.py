#!/usr/bin/env python3
"""Turn the per-object prune list into a plan someone can actually execute.

`prunable.txt` is 198,790 individual keys, which is neither reviewable nor a
sensible thing to hand to `aws s3 rm`. This rolls it up: any directory whose
*entire* subtree is deletable becomes one recursive delete, and only the keys in
directories that still hold something we keep are listed individually.

Two guards run before anything is written, because a rollup is the step where a
mistake stops being one object and becomes a whole tree:

  * nothing on the plan may appear in keep.txt, and
  * nothing on the plan may appear in the independent sweep's resolved set --
    a second, separately-written extraction of every reference in the built
    site, the ES export and the repo sources.

Tiers exist because "unreferenced" and "irreplaceable" are different questions.
The archival masters are 76% of the bytes and nothing links them, but that is a
preservation call, so they are quantified and held back rather than swept in.

Usage:
    python3 media_prune_plan.py [--include-masters] [--include-unlinked-apps]
                                [--sweep-referenced PATH] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Prune reasons that are safe on the reference analysis alone.
SAFE_REASONS = {"os-junk", "unreferenced", "beside-kept", "variant-of-kept"}
# Prune reasons that are a judgement call, opted into explicitly.
GATED_REASONS = {"master-or-tiff": "--include-masters",
                 "unlinked-app": "--include-unlinked-apps"}

GB = 1024 ** 3


def read_sizes(path: Path) -> dict[str, int]:
    """Parse `aws s3 ls --recursive` output. Keys contain spaces, so split 3x."""
    sizes = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4:
            sizes[parts[3]] = int(parts[2])
    return sizes


def read_reasons(path: Path) -> dict[str, str]:
    reasons = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        reason, _, key = line.partition("\t")
        if key:
            reasons[key] = reason
    return reasons


def read_lines(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}


def app_bundles(all_keys: list[str]) -> set[str]:
    """Prefixes that have to be deleted whole or not at all.

    A macOS ``.app`` is a directory that behaves like a single file. Its Mono
    runtime configs and ``.nib`` resources are classed as ordinary unreferenced
    objects, so without this the plan takes 29 of the 107 objects in each bundle
    and leaves something that is neither reclaimed nor runnable.
    """
    bundles = set()
    for key in all_keys:
        parts = key.split("/")
        for i, segment in enumerate(parts[:-1]):
            if segment.lower().endswith(".app"):
                bundles.add("/".join(parts[: i + 1]))
    return bundles


def rollup(all_keys: list[str], delete: set[str]) -> tuple[list[str], list[str]]:
    """Split the delete set into whole-directory deletes and leftover files.

    A directory qualifies only when every object beneath it is being deleted, so
    a recursive delete cannot reach anything we are keeping. Only the topmost
    such directory is emitted; its descendants are implied.
    """
    total: dict[str, int] = defaultdict(int)
    doomed: dict[str, int] = defaultdict(int)
    for key in all_keys:
        is_doomed = key in delete
        parts = key.split("/")[:-1]
        for i in range(len(parts)):
            prefix = "/".join(parts[: i + 1])
            total[prefix] += 1
            if is_doomed:
                doomed[prefix] += 1

    fully = {p for p in total if total[p] == doomed[p]}
    # Keep only the highest fully-deletable ancestor.
    maximal = []
    for prefix in fully:
        parent = prefix.rpartition("/")[0]
        if parent and parent in fully:
            continue
        maximal.append(prefix)
    maximal.sort()

    covered = tuple(p + "/" for p in maximal)
    files = sorted(k for k in delete if not k.startswith(covered))
    return maximal, files


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--include-masters", action="store_true",
                    help="also delete masters/ and .tif/.tiff originals (201 GB)")
    ap.add_argument("--include-unlinked-apps", action="store_true",
                    help="also delete complete 3D applications the site never links")
    ap.add_argument("--s3-raw", default=HERE / "s3_raw.txt", type=Path)
    ap.add_argument("--keep", default=HERE / "keep.txt", type=Path)
    ap.add_argument("--prune-reasons", default=HERE / "prune_reasons.tsv", type=Path)
    ap.add_argument("--sweep-referenced", type=Path,
                    help="independent sweep's resolved-object list, used as a "
                         "second veto over the plan")
    ap.add_argument("--out-dir", default=HERE / "prune_plan", type=Path)
    args = ap.parse_args(argv)

    sizes = read_sizes(args.s3_raw)
    all_keys = sorted(sizes)
    keep = read_lines(args.keep)
    reasons = read_reasons(args.prune_reasons)
    referenced = read_lines(args.sweep_referenced) if args.sweep_referenced else set()

    selected = set(SAFE_REASONS)
    for reason, flag in GATED_REASONS.items():
        if (reason == "master-or-tiff" and args.include_masters) or (
                reason == "unlinked-app" and args.include_unlinked_apps):
            selected.add(reason)

    delete = {k for k, r in reasons.items() if r in selected}

    # Guard 1: the plan must not touch the allow-list.
    overlap = delete & keep
    if overlap:
        print(f"ABORT: {len(overlap)} planned deletions are in keep.txt, e.g. "
              f"{sorted(overlap)[:3]}", file=sys.stderr)
        return 1

    # Guard 2: the independent sweep gets a veto. It resolves directory
    # references to whole subtrees, so it is broader than keep.txt on purpose.
    vetoed = delete & referenced
    if vetoed:
        delete -= vetoed
        print(f"note: {len(vetoed)} objects held back -- the independent sweep "
              f"reaches them even though the catalog does not")

    if not referenced:
        print("WARNING: no --sweep-referenced given; the second guard did not "
              "run and this plan rests on one analysis only", file=sys.stderr)

    # Guard 3: an app bundle goes whole or stays whole. Only relevant while the
    # applications are held back; once they are opted in, the bundle is fully
    # inside the delete set anyway and this changes nothing.
    if not args.include_unlinked_apps:
        for bundle in app_bundles(all_keys):
            inside = {k for k in delete if k.startswith(bundle + "/")}
            if inside:
                delete -= inside
                print(f"note: {len(inside)} objects held back to keep "
                      f"{bundle} intact")

    dirs, files = rollup(all_keys, delete)

    dir_bytes = sum(sizes[k] for k in delete
                    if k.startswith(tuple(p + "/" for p in dirs))) if dirs else 0
    file_bytes = sum(sizes[k] for k in files)
    total_bytes = sum(sizes[k] for k in delete)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "delete_directories.txt").write_text(
        "\n".join(dirs) + "\n", encoding="utf-8")
    (args.out_dir / "delete_files.txt").write_text(
        "\n".join(files) + "\n", encoding="utf-8")
    (args.out_dir / "delete_all_keys.txt").write_text(
        "\n".join(sorted(delete)) + "\n", encoding="utf-8")

    held = {k: r for k, r in reasons.items() if r not in selected}
    held_by_reason: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for key, reason in held.items():
        held_by_reason[reason][0] += 1
        held_by_reason[reason][1] += sizes[key]

    bucket_bytes = sum(sizes.values())
    print()
    print(f"bucket                {len(all_keys):>9,} objects  {bucket_bytes/GB:>7.1f} GB")
    print(f"keep (validated)      {len(keep):>9,} objects  "
          f"{sum(sizes[k] for k in keep if k in sizes)/GB:>7.1f} GB")
    print(f"planned for deletion  {len(delete):>9,} objects  {total_bytes/GB:>7.1f} GB")
    print()
    print(f"  as {len(dirs):,} whole-directory deletes   "
          f"{dir_bytes/GB:>7.1f} GB")
    print(f"  as {len(files):,} individual file deletes  {file_bytes/GB:>7.1f} GB")
    if held_by_reason:
        print()
        print("held back (decide explicitly):")
        for reason, (n, b) in sorted(held_by_reason.items(), key=lambda kv: -kv[1][1]):
            print(f"  {reason:16} {n:>7,} objects  {b/GB:>7.1f} GB  "
                  f"({GATED_REASONS.get(reason, 'n/a')})")
    print()
    print(f"wrote {args.out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
