---
name: confluence-to-md
description: Convert Confluence wiki pages to clean Markdown files using the confluence2md CLI. Use when the user provides a Confluence URL (atlassian.net/wiki) and wants to save it as a Markdown note, or when the user asks to import, convert, or fetch a Confluence page.
compatibility: Requires Python 3.11+ and pip. Requires confluence2md CLI installed via pip.
allowed-tools: Bash(confluence2md:*) Bash(pip:*)
---

# Confluence to Markdown

Convert Confluence pages to clean Obsidian-compatible Markdown with images.

## Prerequisites

Install the CLI if not already available:

```bash
pip install confluence-2-md
```

Credentials must be configured in `~/.confluence_2_md.env`:

```
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_TOKEN=your-api-token
```

If the command fails with a configuration error, tell the user to create this file with their Atlassian credentials.

## Usage

When the user provides a Confluence URL, run:

```bash
confluence2md "<url>" -o .
```

This saves the page as a Markdown file in the current directory with images in a subfolder named after the page title.

### Supported URL formats

- Standard: `https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Title`
- Short link: `https://domain.atlassian.net/wiki/x/AbCdEf`
- Page ID: `123456`

### Options

| Flag | Description |
|------|-------------|
| `-o .` | Save to current directory (recommended for Obsidian vaults) |
| `-o <dir>` | Save to a specific directory |
| `-o <file.md>` | Save with a specific filename |
| `--no-images` | Skip downloading images |
| `--json` | Output JSON instead of Markdown |

### Output structure

```
current-directory/
├── Page_Title.md
└── Page_Title/
    ├── image1.png
    └── diagram.svg
```

## Behavior

1. Always use `-o .` to save files in the current working directory unless the user specifies otherwise
2. After saving, confirm the filename and briefly describe the page content
3. If the user asks to summarize or analyze the page, first save it then read the saved file
4. Images are downloaded automatically into a subfolder matching the Markdown filename
