"""CLI entry point for confluence2md."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from confluence_2_md.config import load_settings
from confluence_2_md.converter import convert
from confluence_2_md.fetcher import ConfluenceFetcher
from confluence_2_md.url_parser import parse_confluence_url


def _sanitize_filename(title: str) -> str:
    """Convert a page title to a safe filename."""
    # Replace characters illegal in filenames
    name = re.sub(r'[<>:"/\\|?*]', "_", title)
    # Collapse multiple underscores/spaces
    name = re.sub(r"[_\s]+", "_", name).strip("_")
    return name or "page"


def _resolve_output_path(output_arg: str, title: str) -> Path:
    """Resolve the output file path.

    If output_arg is a directory (or has no .md extension), treat it as a
    directory and derive the filename from the page title.
    """
    p = Path(output_arg)
    # Treat as directory if: existing dir, no extension, or no .md suffix
    if p.is_dir() or not p.suffix:
        filename = f"{_sanitize_filename(title)}.md"
        return p / filename
    return p


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="confluence2md",
        description="Convert Confluence pages to Markdown.",
    )
    p.add_argument(
        "url",
        help="Confluence page URL or numeric page ID",
    )
    p.add_argument(
        "-o", "--output",
        nargs="?",
        const="output",
        default=None,
        help="Output directory or file path (default: output/). "
             "If a directory is given, filename is derived from page title.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="Output JSON (for programmatic use)",
    )
    p.add_argument(
        "--no-images",
        action="store_true",
        help="Skip downloading images",
    )
    p.add_argument(
        "--base-url",
        help="Override CONFLUENCE_BASE_URL",
    )
    p.add_argument(
        "--username",
        help="Override CONFLUENCE_USERNAME",
    )
    p.add_argument(
        "--token",
        help="Override CONFLUENCE_TOKEN",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Load settings
    try:
        settings = load_settings(
            base_url=args.base_url,
            username=args.username,
            token=args.token,
        )
        settings.validate_required()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse URL
    try:
        parsed = parse_confluence_url(args.url)
    except ValueError as e:
        print(f"URL error: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve page ID
    fetcher = ConfluenceFetcher(settings)
    page_id = parsed["page_id"]

    if not page_id and parsed["short_link"]:
        try:
            page_id = fetcher.resolve_short_link(parsed["short_link"])
        except Exception as e:
            print(f"Failed to resolve short link: {e}", file=sys.stderr)
            sys.exit(1)

    if not page_id:
        print("Could not determine page ID from the given URL.", file=sys.stderr)
        sys.exit(1)

    # Use base_url from parsed URL if settings doesn't have one from CLI
    if parsed["base_url"] and not args.base_url:
        settings.CONFLUENCE_BASE_URL = parsed["base_url"]
        fetcher = ConfluenceFetcher(settings)

    # Fetch page
    try:
        page = fetcher.fetch_page(page_id)
    except Exception as e:
        print(f"Fetch error: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine image download behavior
    download_images = not args.no_images and not args.json_mode

    # Resolve output path (needed before convert to determine image_dir name)
    out_path = None
    if args.output and not args.json_mode:
        out_path = _resolve_output_path(args.output, page.title)

    # Image directory = same name as the .md file (without extension)
    image_dir_name = _sanitize_filename(page.title) if out_path else "assets"

    # Convert HTML → Markdown
    markdown = convert(page.html_content, download_images=download_images, image_dir=image_dir_name)

    # Download images if needed
    if download_images and page.attachments:
        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}
        image_attachments = [
            a for a in page.attachments
            if Path(a.filename).suffix.lower() in image_exts
        ]

        if image_attachments:
            if out_path:
                assets_dir = out_path.parent / image_dir_name
            else:
                assets_dir = Path.cwd() / "assets"

            for att in image_attachments:
                try:
                    fetcher.download_attachment(att, assets_dir)
                except Exception as e:
                    print(
                        f"Warning: Failed to download {att.filename}: {e}",
                        file=sys.stderr,
                    )

    # Output
    if args.json_mode:
        result = {
            "title": page.title,
            "page_id": page.page_id,
            "url": page.url,
            "markdown": markdown,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
        print(f"Written to {out_path}", file=sys.stderr)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
