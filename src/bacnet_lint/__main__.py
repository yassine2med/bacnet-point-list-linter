"""Command line entry: python -m bacnet_lint FILE.csv [--max-length N]"""

import argparse
import sys

from .linter import lint_file


def main(argv: list[str] | None = None) -> int:
    """Print findings; return 0 when clean, 1 when findings exist, 2 when the file cannot be read."""
    parser = argparse.ArgumentParser(prog="bacnet_lint", description="Lint a BACnet point list CSV.")
    parser.add_argument("file")
    parser.add_argument("--max-length", type=int, default=32, help="longest allowed name")
    args = parser.parse_args(argv)
    try:
        findings = lint_file(args.file, args.max_length)
    except OSError as err:
        print(f"cannot read file: {err}", file=sys.stderr)
        return 2
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
