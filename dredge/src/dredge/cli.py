from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .codegen import write_client
from .compiler import (
    BROTLI_MAX_QUALITY,
    BROTLI_MIN_QUALITY,
    BROTLI_QUALITY,
    BuildError,
    compile_site,
    validate_config,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dredge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("validate", "compile", "codegen"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument(
            "-c",
            "--config",
            default="dredge.config.json",
            help="Path to dredge.config.json",
        )
        if command == "compile":
            command_parser.add_argument(
                "--metrics-json",
                type=Path,
                help="Write compiler timing and progress metrics to this JSON file",
            )
            command_parser.add_argument(
                "--brotli-quality",
                type=int,
                choices=range(BROTLI_MIN_QUALITY, BROTLI_MAX_QUALITY + 1),
                default=BROTLI_QUALITY,
                metavar=f"{BROTLI_MIN_QUALITY}-{BROTLI_MAX_QUALITY}",
                help=(
                    "Brotli quality for the compressed search database "
                    f"(default: {BROTLI_QUALITY})"
                ),
            )

    synth_parser = subparsers.add_parser(
        "synth",
        help="Generate a deterministic synthetic site for stress testing",
    )
    synth_parser.add_argument(
        "root", type=Path, help="Directory to generate the site and config into"
    )
    synth_parser.add_argument(
        "-n", "--count", type=int, default=1_000, help="Number of pages to generate"
    )
    synth_parser.add_argument(
        "--seed", type=int, default=1, help="Deterministic generation seed"
    )
    synth_parser.add_argument(
        "--shard-size",
        type=int,
        default=1_000,
        help="Pages per subdirectory shard",
    )

    args = parser.parse_args(argv)

    if args.command == "synth":
        from .synthetic import generate_site

        site = generate_site(
            args.root,
            count=args.count,
            seed=args.seed,
            shard_size=args.shard_size,
        )
        print(f"generated {site.page_count} pages")
        print(f"source: {site.source_dir}")
        print(f"config: {site.config_path}")
        return 0

    config_path = Path(args.config)

    try:
        if args.command == "validate":
            config = validate_config(config_path)
            print(f"valid: {config.path}")
            return 0

        if args.command == "codegen":
            config = validate_config(config_path)
            client_path = write_client(config, require_output=True)
            print(f"client: {client_path}")
            return 0

        result = compile_site(
            config_path,
            metrics_json_path=args.metrics_json,
            progress_stream=sys.stderr,
            brotli_quality=args.brotli_quality,
        )
        for warning in result.warnings:
            print(f"warning[{warning.code}]: {warning.message}", file=sys.stderr)
        print(f"compiled {result.page_count} pages")
        print(f"database: {result.db_path}")
        print(f"compressed: {result.compressed_db_path}")
        print(f"manifest: {result.manifest_path}")
        if args.metrics_json is not None:
            print(f"metrics: {args.metrics_json}")
        if result.client_path is not None:
            print(f"client: {result.client_path}")
        return 0
    except BuildError as error:
        print(f"error[{error.code}]: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
