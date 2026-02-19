"""Convert Confluence storage-format HTML to Markdown.

Two-phase conversion:
1. BeautifulSoup pre-processing: normalize ac:* macros to standard HTML
2. markdownify: convert clean HTML to Markdown
3. Post-processing: whitespace cleanup
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import MarkdownConverter

# Emoticon name → Unicode emoji mapping
EMOTICON_MAP = {
    "smile": "\U0001f642",
    "sad": "\U0001f641",
    "cheeky": "\U0001f61b",
    "laugh": "\U0001f604",
    "wink": "\U0001f609",
    "thumbs-up": "\U0001f44d",
    "thumbs-down": "\U0001f44e",
    "information": "\u2139\ufe0f",
    "tick": "\u2705",
    "cross": "\u274c",
    "warning": "\u26a0\ufe0f",
    "plus": "\u2795",
    "minus": "\u2796",
    "question": "\u2753",
    "light-on": "\U0001f4a1",
    "light-off": "\U0001f4a1",
    "yellow-star": "\u2b50",
    "red-star": "\u2b50",
    "green-star": "\u2b50",
    "blue-star": "\u2b50",
    "heart": "\u2764\ufe0f",
    "broken-heart": "\U0001f494",
}


class _ConfluenceMarkdownConverter(MarkdownConverter):
    """Custom markdownify converter that handles special elements."""

    def convert_pre(self, el, text, parent_tags):
        if not text:
            return ""
        lang = el.get("data-lang", "")
        code = text.strip("\n")
        return f"\n```{lang}\n{code}\n```\n"

    def convert_details(self, el, text, parent_tags):
        """Preserve <details> tags as raw HTML."""
        return str(el)

    def convert_summary(self, el, text, parent_tags):
        """Handled by convert_details — should not be called standalone."""
        return text


def _md(html: str, **kwargs) -> str:
    return _ConfluenceMarkdownConverter(**kwargs).convert(html)


def convert(html: str, download_images: bool = False, image_dir: str = "assets") -> str:
    """Convert Confluence storage-format HTML to Markdown.

    Args:
        html: Confluence storage-format HTML string.
        download_images: If True, rewrite image refs to local image_dir/ paths.
        image_dir: Directory name for image references in Markdown.

    Returns:
        Markdown string.
    """
    if not html or not html.strip():
        return ""

    soup = BeautifulSoup(html, "lxml")

    # Phase 1: Pre-process Confluence-specific elements
    _preprocess_code_blocks(soup)
    _preprocess_info_panels(soup)
    _preprocess_expand_macros(soup)
    _preprocess_task_lists(soup)
    _preprocess_user_mentions(soup)
    _preprocess_page_links(soup)
    _preprocess_status_macros(soup)
    _preprocess_toc_macros(soup)
    _preprocess_emoticons(soup)
    _preprocess_images(soup, download_images, image_dir)
    _preprocess_noformat(soup)

    # Phase 2: Convert to Markdown via markdownify
    cleaned_html = str(soup)
    md = _md(cleaned_html, heading_style="ATX", bullets="-", strip=["span"])

    # Phase 3: Post-process
    md = _postprocess(md)

    return md


# ---------------------------------------------------------------------------
# Phase 1: Pre-processing helpers
# ---------------------------------------------------------------------------


def _get_macro_name(tag: Tag) -> str | None:
    """Get the ac:name attribute from a structured-macro tag."""
    return tag.get("ac:name") or tag.get("data-macro-name")


def _get_param(tag: Tag, name: str) -> str:
    """Get a named parameter value from inside a macro tag."""
    param = tag.find("ac:parameter", attrs={"ac:name": name})
    if param:
        return param.get_text(strip=True)
    return ""


def _preprocess_code_blocks(soup: BeautifulSoup) -> None:
    """ac:structured-macro[code/code-block] → fenced code block placeholder.

    markdownify doesn't extract language from class attrs, so we inject
    a raw fenced code block wrapped in a <div> to pass through.
    """
    for macro in soup.find_all("ac:structured-macro"):
        name = _get_macro_name(macro)
        if name not in ("code", "code-block"):
            continue

        lang = _get_param(macro, "language") or ""
        body = macro.find("ac:plain-text-body")
        code_text = body.get_text() if body else ""

        # Use a <pre> with data-lang so we can fix in post-processing
        pre = soup.new_tag("pre")
        pre["data-lang"] = lang
        code = soup.new_tag("code")
        code.string = code_text
        pre.append(code)
        macro.replace_with(pre)


def _preprocess_noformat(soup: BeautifulSoup) -> None:
    """ac:structured-macro[noformat] → <pre><code>."""
    for macro in soup.find_all("ac:structured-macro"):
        name = _get_macro_name(macro)
        if name != "noformat":
            continue

        body = macro.find("ac:plain-text-body")
        text = body.get_text() if body else ""

        pre = soup.new_tag("pre")
        code = soup.new_tag("code")
        code.string = text
        pre.append(code)
        macro.replace_with(pre)


def _preprocess_info_panels(soup: BeautifulSoup) -> None:
    """ac:structured-macro[info/note/warning/tip] → blockquote with label."""
    panel_types = {
        "info": "Info",
        "note": "Note",
        "warning": "Warning",
        "tip": "Tip",
        "panel": "Note",
    }
    for macro in soup.find_all("ac:structured-macro"):
        name = _get_macro_name(macro)
        if name not in panel_types:
            continue

        label = panel_types[name]
        title = _get_param(macro, "title")

        body = macro.find("ac:rich-text-body")
        inner_html = body.decode_contents() if body else ""

        header_text = label
        if title:
            header_text = f"{label}: {title}"

        bq = soup.new_tag("blockquote")
        p = soup.new_tag("p")
        strong = soup.new_tag("strong")
        strong.string = header_text
        p.append(strong)
        bq.append(p)
        # Parse inner content with html.parser to avoid extra <html><body>
        inner_soup = BeautifulSoup(inner_html, "html.parser")
        for child in list(inner_soup.children):
            bq.append(child)
        macro.replace_with(bq)


def _preprocess_expand_macros(soup: BeautifulSoup) -> None:
    """ac:structured-macro[expand] → <details><summary>."""
    for macro in soup.find_all("ac:structured-macro"):
        name = _get_macro_name(macro)
        if name != "expand":
            continue

        title = _get_param(macro, "title") or "Click to expand"
        body = macro.find("ac:rich-text-body")
        inner_html = body.decode_contents() if body else ""

        details = soup.new_tag("details")
        summary = soup.new_tag("summary")
        summary.string = title
        details.append(summary)
        inner_soup = BeautifulSoup(inner_html, "html.parser")
        for child in list(inner_soup.children):
            details.append(child)
        macro.replace_with(details)


def _preprocess_task_lists(soup: BeautifulSoup) -> None:
    """ac:task-list / ac:task → ul with checkbox markers."""
    for task_list in soup.find_all("ac:task-list"):
        ul = soup.new_tag("ul")

        for task in task_list.find_all("ac:task", recursive=False):
            status_tag = task.find("ac:task-status")
            body_tag = task.find("ac:task-body")

            checked = (
                status_tag and status_tag.get_text(strip=True) == "complete"
            )
            body_html = body_tag.decode_contents() if body_tag else ""

            marker = "[x]" if checked else "[ ]"
            li = soup.new_tag("li")
            inner = BeautifulSoup(f"{marker} {body_html}", "html.parser")
            for child in list(inner.children):
                li.append(child)
            ul.append(li)

        task_list.replace_with(ul)


def _preprocess_user_mentions(soup: BeautifulSoup) -> None:
    """ac:link > ri:user → @DisplayName."""
    for link in soup.find_all("ac:link"):
        user = link.find("ri:user")
        if not user:
            continue

        # Try to get display name from link body or ri:user attributes
        body = link.find("ac:link-body") or link.find("ac:plain-text-link-body")
        if body:
            display_name = body.get_text(strip=True)
        else:
            display_name = user.get("ri:userkey", "") or user.get("ri:account-id", "user")

        mention = soup.new_string(f"@{display_name}")
        link.replace_with(mention)


def _preprocess_page_links(soup: BeautifulSoup) -> None:
    """ac:link > ri:page → [Page Title]()."""
    for link in soup.find_all("ac:link"):
        page = link.find("ri:page")
        if not page:
            # Also handle ri:content-entity
            entity = link.find("ri:content-entity")
            if not entity:
                continue
            title = entity.get("ri:content-title", "Link")
            a = soup.new_tag("a", href="")
            a.string = title
            link.replace_with(a)
            continue

        title = page.get("ri:content-title", "")
        body = link.find("ac:link-body") or link.find("ac:plain-text-link-body")
        display = body.get_text(strip=True) if body else title

        a = soup.new_tag("a", href="")
        a.string = display or "Link"
        link.replace_with(a)


def _preprocess_status_macros(soup: BeautifulSoup) -> None:
    """ac:structured-macro[status] → **[STATUS]**."""
    for macro in soup.find_all("ac:structured-macro"):
        name = _get_macro_name(macro)
        if name != "status":
            continue

        title = _get_param(macro, "title") or "STATUS"
        strong = soup.new_tag("strong")
        strong.string = f"[{title.upper()}]"
        macro.replace_with(strong)


def _preprocess_toc_macros(soup: BeautifulSoup) -> None:
    """ac:structured-macro[toc] → remove (not useful in Markdown)."""
    for macro in soup.find_all("ac:structured-macro"):
        name = _get_macro_name(macro)
        if name == "toc":
            macro.decompose()


def _preprocess_emoticons(soup: BeautifulSoup) -> None:
    """ac:emoticon → Unicode emoji."""
    for emoticon in soup.find_all("ac:emoticon"):
        emo_name = emoticon.get("ac:name", "")
        emoji = EMOTICON_MAP.get(emo_name, f":{emo_name}:")
        emoticon.replace_with(soup.new_string(emoji))


def _preprocess_images(soup: BeautifulSoup, download: bool, image_dir: str = "assets") -> None:
    """ac:image → <img> tag.

    If download=True, rewrites src to image_dir/filename.
    Otherwise keeps the Confluence download URL placeholder.
    """
    for ac_image in soup.find_all("ac:image"):
        attachment = ac_image.find("ri:attachment")
        url_tag = ac_image.find("ri:url")

        alt = ac_image.get("ac:alt", "")

        if attachment:
            filename = attachment.get("ri:filename", "image")
            if not alt:
                alt = filename
            if download:
                src = f"{image_dir}/{filename}"
            else:
                src = filename  # placeholder; CLI will handle
        elif url_tag:
            src = url_tag.get("ri:value", "")
            if not alt:
                alt = "image"
        else:
            src = ""
            alt = alt or "image"

        img = soup.new_tag("img", src=src, alt=alt)
        ac_image.replace_with(img)


# ---------------------------------------------------------------------------
# Phase 3: Post-processing
# ---------------------------------------------------------------------------


def _postprocess(md: str) -> str:
    """Clean up Markdown output."""
    # Collapse 3+ consecutive blank lines into 2
    md = re.sub(r"\n{3,}", "\n\n", md)
    # Remove trailing whitespace on each line
    md = "\n".join(line.rstrip() for line in md.split("\n"))
    # Ensure single trailing newline
    md = md.strip() + "\n"
    return md
