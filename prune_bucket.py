#!/usr/bin/env python3
"""Delete the audited objects from s3://giza-media, and nothing else.

Deletes exactly the keys listed in prune_plan/delete_all_keys.txt. It does not
use ``aws s3 rm --recursive``, deliberately: that re-lists the bucket at delete
time, so it would also remove anything uploaded under those prefixes since the
audit. That is not hypothetical here -- refreshing the inventory on 2026-08-03
turned up three PDFs that had appeared since the previous listing, and the site
references all three. Naming every key means the deletion can only ever affect
what was actually reviewed.

Guards, all of which run again at delete time rather than trusting the file:

  * every key is re-checked against keep.txt, so a stale or hand-edited plan
    cannot delete something the site needs;
  * every key must be absent from keep.txt AND present in prunable.txt;
  * a log of deleted keys makes the run resumable and auditable -- rerunning
    skips what already went.

Default is a dry run. Nothing is deleted without --execute.

Usage:
    python3 prune_bucket.py                 # dry run, prints what would go
    python3 prune_bucket.py --execute       # actually delete
    python3 prune_bucket.py --execute       # rerun after an interruption
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUCKET = "giza-media"
BATCH = 1000  # delete-objects hard limit


def read_lines(path: Path) -> list[str]:
    return [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--execute", action="store_true",
                    help="actually delete; without this it is a dry run")
    ap.add_argument("--plan", type=Path,
                    default=HERE / "prune_plan" / "delete_all_keys.txt")
    ap.add_argument("--keep", type=Path, default=HERE / "keep.txt")
    ap.add_argument("--prunable", type=Path, default=HERE / "prunable.txt")
    ap.add_argument("--log", type=Path, default=HERE / "prune_plan" / "deleted.log")
    ap.add_argument("--errors", type=Path, default=HERE / "prune_plan" / "errors.log")
    ap.add_argument("--bucket", default=BUCKET)
    ap.add_argument("--limit", type=int,
                    help="stop after this many keys (for a cautious first pass)")
    args = ap.parse_args(argv)

    plan = read_lines(args.plan)
    keep = set(read_lines(args.keep))
    prunable = set(read_lines(args.prunable))

    # Guard 1: the plan may not name anything on the allow-list.
    overlap = [k for k in plan if k in keep]
    if overlap:
        print(f"ABORT: {len(overlap)} planned keys are in keep.txt, e.g. "
              f"{overlap[:3]}", file=sys.stderr)
        return 1

    # Guard 2: the plan may not name anything outside the audited prunable set.
    stray = [k for k in plan if k not in prunable]
    if stray:
        print(f"ABORT: {len(stray)} planned keys are not in prunable.txt, e.g. "
              f"{stray[:3]}", file=sys.stderr)
        return 1

    done: set[str] = set()
    if args.log.exists():
        done = set(read_lines(args.log))
        if done:
            print(f"resuming: {len(done):,} keys already deleted")

    todo = [k for k in plan if k not in done]
    if args.limit:
        todo = todo[: args.limit]

    print(f"bucket        : s3://{args.bucket}")
    print(f"plan          : {len(plan):,} keys")
    print(f"already gone  : {len(done):,}")
    print(f"to delete now : {len(todo):,}  in {(len(todo)+BATCH-1)//BATCH} batches")
    print(f"mode          : {'EXECUTE -- deletes are permanent' if args.execute else 'DRY RUN'}")
    print()

    if not todo:
        print("nothing to do")
        return 0

    if not args.execute:
        for key in todo[:10]:
            print(f"  would delete  {key}")
        if len(todo) > 10:
            print(f"  ... and {len(todo)-10:,} more")
        print("\nre-run with --execute to delete")
        return 0

    args.log.parent.mkdir(parents=True, exist_ok=True)
    deleted = errors = 0
    with args.log.open("a", encoding="utf-8") as log, \
            args.errors.open("a", encoding="utf-8") as errlog:
        for start in range(0, len(todo), BATCH):
            batch = todo[start : start + BATCH]
            payload = json.dumps(
                {"Objects": [{"Key": k} for k in batch], "Quiet": True})
            proc = subprocess.run(
                ["aws", "s3api", "delete-objects", "--bucket", args.bucket,
                 "--delete", payload, "--output", "json"],
                capture_output=True, text=True,
            )
            if proc.returncode != 0:
                errlog.write(f"BATCH FAILED at offset {start}: "
                             f"{proc.stderr.strip()}\n")
                errlog.flush()
                print(f"  batch {start//BATCH+1}: FAILED -- {proc.stderr.strip()[:200]}",
                      file=sys.stderr)
                print("stopping; fix the cause and re-run to resume",
                      file=sys.stderr)
                return 1
            # Quiet mode returns only errors, so an empty Errors list is success.
            failed = {}
            if proc.stdout.strip():
                body = json.loads(proc.stdout)
                for err in body.get("Errors", []):
                    failed[err.get("Key")] = f"{err.get('Code')}: {err.get('Message')}"
            for key in batch:
                if key in failed:
                    errlog.write(f"{key}\t{failed[key]}\n")
                    errors += 1
                else:
                    log.write(key + "\n")
                    deleted += 1
            log.flush()
            errlog.flush()
            print(f"  batch {start//BATCH+1}/{(len(todo)+BATCH-1)//BATCH}: "
                  f"{deleted:,} deleted, {errors} errors")

    print(f"\ndeleted {deleted:,} objects; {errors} errors")
    if errors:
        print(f"see {args.errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
