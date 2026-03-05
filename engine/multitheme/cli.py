"""CLI entry point for the multitheme engine.

Usage:
    python -m multitheme.cli build --config site.yaml --output docs/
"""

import argparse
import sys
from pathlib import Path

from .builder import build


def main():
    parser = argparse.ArgumentParser(
        description='Multitheme - Static site generator engine'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build the static site')
    build_parser.add_argument(
        '--config', '-c',
        default='site.yaml',
        help='Path to site.yaml config file (default: site.yaml)'
    )
    build_parser.add_argument(
        '--output', '-o',
        default='docs',
        help='Output directory (default: docs/)'
    )
    build_parser.add_argument(
        '--engine-dir',
        default=None,
        help='Path to engine/ directory (auto-detected by default)'
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == 'build':
        try:
            build(
                config_path=args.config,
                output_dir=args.output,
                engine_dir=args.engine_dir,
            )
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except ValueError as e:
            print(f"Config error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Build failed: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
