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

## Supported URL formats

- Standard: `https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Title`
- Short link: `https://domain.atlassian.net/wiki/x/AbCdEf`
- Page ID: `123456`

## Usage

When the user provides a Confluence URL, run:

```bash
confluence2md "<url>" --obsidian -o "00. Inbox/05. Confluence" --image-dir "90. Settings/99. Attachments"
```

The `--obsidian` flag enables:
- Wikilink image embeds: `![[filename.png]]` instead of `![alt](path)`
- Obsidian callout syntax: `> [!info]` instead of plain blockquotes

Images are saved flat (no subfolder per page) in the attachments directory.

## Frontmatter

After saving the Markdown file, prepend YAML frontmatter to the file. Generate the following properties:

```yaml
---
type:
  - source
aliases:
  - <generate 1-2 short Korean aliases summarizing the page title>
CMDS:
index:
status: reference
tags:
  - <generate 2-5 relevant tags based on page content, in Korean or English as appropriate>
date created: <today's date in YYYY-MM-DD format>
related:
source_url: <the original Confluence URL>
---
```

Rules:
- `aliases`: Generate concise aliases based on the page title. Abbreviate or simplify the title.
- `CMDS`, `index`, `related`: Leave empty (no value after the colon).
- `status`: Always set to `reference`.
- `tags`: Generate relevant tags by reading the converted Markdown content. Use lowercase.
- `date created`: Use today's date.
- `source_url`: Use the exact URL the user provided.

## Behavior

1. Always use the command with `--obsidian`, `-o "00. Inbox/05. Confluence"`, and `--image-dir "90. Settings/99. Attachments"`
2. After saving, read the file to generate appropriate aliases and tags, then prepend the frontmatter
3. Confirm the filename and briefly describe the page content
4. If the user asks to summarize or analyze the page, first save it then read the saved file
