# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Confluence to Markdown converter — fetches Confluence pages via API v2 and converts storage-format HTML to clean Markdown.

## Build & Run

```bash
pip install -e ".[dev]"          # Install with dev dependencies
confluence2md <url_or_id>         # Convert and print to stdout
confluence2md <url> -o file.md    # Save to file (images → assets/)
confluence2md <url> --json        # JSON output for programmatic use
```

## Test

```bash
pytest tests/ -v
```

## Architecture

- `src/confluence_2_md/` — Main package
  - `cli.py` — CLI entry point (argparse)
  - `config.py` — Settings via pydantic-settings (.env loading)
  - `fetcher.py` — Confluence API v2 client (httpx + tenacity retry)
  - `converter.py` — HTML→Markdown (BeautifulSoup preprocessing + markdownify)
  - `url_parser.py` — URL/page-ID extraction
- `tests/` — pytest tests

## Configuration

Set via `.env` file (CWD or `~/.confluence_2_md.env`) or environment variables:
- `CONFLUENCE_BASE_URL` — e.g. `https://domain.atlassian.net/wiki`
- `CONFLUENCE_USERNAME` — email
- `CONFLUENCE_TOKEN` — API token
