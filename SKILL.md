---
name: confluence-to-md
description: Convert Confluence wiki pages to clean Markdown files using the confluence2md CLI. Use when the user provides a Confluence URL (atlassian.net/wiki) and wants to save it as a Markdown note, or when the user asks to import, convert, or fetch a Confluence page.
compatibility: Requires Python 3.11+ and pip. Requires confluence2md CLI installed via pip.
allowed-tools: Bash(confluence2md:*) Bash(pip:*) Bash(mv:*) Bash(mkdir:*) Bash(sed:*)
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

## Usage (Obsidian vault)

When the user provides a Confluence URL, follow these steps:

### Step 1: Convert and save

```bash
confluence2md "<url>" -o "00. Inbox/05. Confluence"
```

This saves the Markdown file to `00. Inbox/05. Confluence/` and images to a subfolder named after the page title.

### Step 2: Move images to Attachments

After conversion, move all downloaded images from the page-title subfolder to the vault's attachments folder:

```bash
mkdir -p "90. Settings/99. Attachments"
mv "00. Inbox/05. Confluence/<Page_Title>/"* "90. Settings/99. Attachments/"
rmdir "00. Inbox/05. Confluence/<Page_Title>"
```

Replace `<Page_Title>` with the actual sanitized page title (the folder name created by confluence2md).

### Step 3: Fix image paths in the Markdown file

Update all image references in the saved Markdown file. Replace the page-title-prefixed paths with the attachments path:

- Find: `<Page_Title>/filename.png`
- Replace with: `90. Settings/99. Attachments/filename.png`

Use sed or similar to do this in-place on the saved .md file. The relative path from `00. Inbox/05. Confluence/` to `90. Settings/99. Attachments/` is `../../90. Settings/99. Attachments/`.

So the replacement should be:
- From: `<Page_Title>/`
- To: `../../90. Settings/99. Attachments/`

## Behavior

1. Always follow the 3-step process above (convert → move images → fix paths)
2. After saving, confirm the filename and briefly describe the page content
3. If the user asks to summarize or analyze the page, first save it then read the saved file
4. If no images were downloaded (empty subfolder or no subfolder created), skip steps 2 and 3
