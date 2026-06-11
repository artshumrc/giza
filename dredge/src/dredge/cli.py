from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .codegen import write_client
from .compiler import BuildError, compile_site, validate_config


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

    args = parser.parse_args(argv)
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

        result = compile_site(config_path)
        for warning in result.warnings:
            print(f"warning[{warning.code}]: {warning.message}", file=sys.stderr)
        print(f"compiled {result.page_count} pages")
        print(f"database: {result.db_path}")
        print(f"manifest: {result.manifest_path}")
        if result.client_path is not None:
            print(f"client: {result.client_path}")
        return 0
    except BuildError as error:
        print(f"error[{error.code}]: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
