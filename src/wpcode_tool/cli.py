from __future__ import annotations

import argparse
from pathlib import Path

from .builder import build_plugin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a WPCode export into a standalone WordPress plugin.",
    )
    parser.add_argument("export", type=Path, help="Path to the WPCode export JSON file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build"),
        help="Directory where the plugin should be created (default: ./build)",
    )
    parser.add_argument(
        "--slug",
        default="wpcode-generated-snippets",
        help="Plugin slug (default: wpcode-generated-snippets)",
    )
    parser.add_argument(
        "--name",
        default="WPCode Generated Snippets",
        help="Plugin name (default: WPCode Generated Snippets)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging during generation",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    plugin_path = build_plugin(
        export_path=args.export,
        output_directory=args.output,
        plugin_slug=args.slug,
        plugin_name=args.name,
        verbose=args.verbose,
    )
    print(f"Plugin created at {plugin_path}")


if __name__ == "__main__":
    main()
