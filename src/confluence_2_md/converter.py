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

    def _in_table(self, parent_tags):
        return "td" in parent_tags or "th" in parent_tags

    def convert_pre(self, el, text, parent_tags):
        # Get raw code from element, not pre-processed text
        code_el = el.find("code")
        raw = code_el.get_text() if code_el else el.get_text()
        if not raw.strip():
            return ""
        lang = el.get("data-lang", "")
        code = raw.strip("\n")
        if self._in_table(parent_tags):
            # Inside table: fenced code blocks break table format
            escaped = code.replace("|", "\\|")
            if "\n" not in escaped:
                return f" `{escaped}` "
            # Multi-line: HTML code block
            html_escaped = escaped.replace("\n", "<br>")
            return f" <code>{html_escaped}</code> "
        return f"\n```{lang}\n{code}\n```\n"

    def convert_code(self, el, text, parent_tags):
        """Handle inline code. Escape pipes when in a table cell."""
        if not text:
            return ""
        # Skip if parent is <pre> — handled by convert_pre
        if "pre" in parent_tags:
            return text
        if self._in_table(parent_tags):
            escaped = text.replace("|", "\\|")
            return f"`{escaped}`"
        return f"`{text}`"

    def convert_td(self, el, text, parent_tags):
        """Escape unprotected pipes in table cell text."""
        # Pipes inside backticks are already escaped by convert_code/convert_pre
        return f" {text.strip()} |"

    def convert_th(self, el, text, parent_tags):
        """Escape unprotected pipes in table header text."""
        return f" {text.strip()} |"

    def convert_details(self, el, text, parent_tags):
        """Preserve <details> tags as raw HTML."""
        return str(el)

    def convert_summary(self, el, text, parent_tags):
        """Handled by convert_details — should not be called standalone."""
        return text

    def convert_div(self, el, text, parent_tags):
        """Pass through raw markdown divs as-is."""
        if el.get("data-raw-markdown"):
            return el.get_text()
        return super().convert_div(el, text, parent_tags) if hasattr(super(), 'convert_div') else f"\n{text}\n"

    def convert_mark(self, el, text, parent_tags):
        """Convert <mark> to ==text== (Obsidian) or <mark> HTML passthrough."""
        if not text:
            return ""
        color = el.get("data-highlight-color", "")
        if self.options.get("obsidian"):
            if color and color != "yellow":
                return f'<mark style="background: {color}">{text}</mark>'
            return f"=={text}=="
        # Standard mode: pass through as HTML
        if color:
            return f'<mark style="background: {color}">{text}</mark>'
        return f"<mark>{text}</mark>"


def _md(html: str, **kwargs) -> str:
    return _ConfluenceMarkdownConverter(**kwargs).convert(html)


def convert(
    html: str,
    download_images: bool = False,
    image_dir: str = "assets",
    obsidian: bool = False,
) -> str:
    """Convert Confluence storage-format HTML to Markdown.

    Args:
        html: Confluence storage-format HTML string.
        download_images: If True, rewrite image refs to local image_dir/ paths.
        image_dir: Directory name for image references in Markdown.
        obsidian: If True, use Obsidian-flavored syntax (wikilink images, callouts).

    Returns:
        Markdown string.
    """
    if not html or not html.strip():
        return ""

    # Strip CDATA markers before parsing — lxml silently drops CDATA content
    html = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', html, flags=re.DOTALL)

    soup = BeautifulSoup(html, "lxml")

    # Phase 1: Pre-process Confluence-specific elements
    _preprocess_code_blocks(soup)
    _preprocess_info_panels(soup, obsidian=obsidian)
    _preprocess_expand_macros(soup)
    _preprocess_task_lists(soup)
    _preprocess_user_mentions(soup)
    _preprocess_page_links(soup)
    _preprocess_status_macros(soup)
    _preprocess_toc_macros(soup)
    _preprocess_emoticons(soup)
    _preprocess_images(soup, download_images, image_dir, obsidian=obsidian)
    _preprocess_noformat(soup)
    _preprocess_highlights(soup)

    # Phase 2: Convert to Markdown via markdownify
    cleaned_html = str(soup)
    md = _md(cleaned_html, heading_style="ATX", bullets="-", strip=["span"],
             obsidian=obsidian)

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


_HIGHLIGHT_CLASS_COLORS = {
    "highlight-yellow": "yellow",
    "highlight-red": "#ffcccb",
    "highlight-green": "#90ee90",
    "highlight-blue": "#add8e6",
    "highlight-grey": "#d3d3d3",
    "highlight-teal": "#008080",
    "highlight-purple": "#dda0dd",
}


def _preprocess_highlights(soup: BeautifulSoup) -> None:
    """Convert highlight spans/marks to <mark> tags.

    Handles:
    - <span class="highlight-yellow">
    - <span style="background-color: ...">
    - <mark> (pass through)
    - ac:structured-macro[highlight]
    """
    # 1. Highlight spans via class
    for span in soup.find_all("span", class_=lambda c: c and any(
        cls.startswith("highlight-") for cls in (c if isinstance(c, list) else [c])
    )):
        classes = span.get("class", [])
        color = "yellow"
        for cls in classes:
            if cls in _HIGHLIGHT_CLASS_COLORS:
                color = _HIGHLIGHT_CLASS_COLORS[cls]
                break
        mark = soup.new_tag("mark")
        mark["data-highlight-color"] = color
        mark.extend(list(span.children))
        span.replace_with(mark)

    # 2. Spans with background-color style
    for span in soup.find_all("span", style=re.compile(r"background-color")):
        style = span.get("style", "")
        bg_match = re.search(r"background-color:\s*([^;]+)", style)
        if bg_match:
            color = bg_match.group(1).strip()
            mark = soup.new_tag("mark")
            mark["data-highlight-color"] = color
            mark.extend(list(span.children))
            span.replace_with(mark)

    # 3. Highlight macro
    for macro in soup.find_all("ac:structured-macro"):
        name = _get_macro_name(macro)
        if name != "highlight":
            continue
        color = _get_param(macro, "color") or "yellow"
        body = macro.find("ac:rich-text-body")
        inner = body.decode_contents() if body else ""
        mark = soup.new_tag("mark")
        mark["data-highlight-color"] = color
        inner_soup = BeautifulSoup(inner, "html.parser")
        for child in list(inner_soup.children):
            mark.append(child)
        macro.replace_with(mark)

    # 4. Existing <mark> tags without color → default yellow
    for mark in soup.find_all("mark"):
        if not mark.get("data-highlight-color"):
            mark["data-highlight-color"] = "yellow"


def _preprocess_info_panels(soup: BeautifulSoup, *, obsidian: bool = False) -> None:
    """ac:structured-macro[info/note/warning/tip] → blockquote with label.

    If obsidian=True, uses Obsidian callout syntax: > [!type] Title
    """
    panel_types = {
        "info": "info",
        "note": "note",
        "warning": "warning",
        "tip": "tip",
        "panel": "note",
    }
    for macro in soup.find_all("ac:structured-macro"):
        name = _get_macro_name(macro)
        if name not in panel_types:
            continue

        callout_type = panel_types[name]
        title = _get_param(macro, "title")

        body = macro.find("ac:rich-text-body")
        inner_html = body.decode_contents() if body else ""

        if obsidian:
            # Convert inner HTML to markdown first for callout body
            inner_md = _md(
                str(BeautifulSoup(inner_html, "html.parser")),
                heading_style="ATX", bullets="-", strip=["span"],
            ).strip()
            callout_header = f"[!{callout_type}] {title}" if title else f"[!{callout_type}]"
            # Build callout as lines prefixed with >
            lines = [f"> {callout_header}"]
            for line in inner_md.split("\n"):
                lines.append(f"> {line}" if line.strip() else ">")
            callout_text = "\n".join(lines)
            # Wrap in a div to pass through markdownify as-is
            div = soup.new_tag("div")
            div.string = f"\n{callout_text}\n"
            div["data-raw-markdown"] = "true"
            macro.replace_with(div)
        else:
            header_text = callout_type.capitalize()
            if title:
                header_text = f"{header_text}: {title}"

            bq = soup.new_tag("blockquote")
            p = soup.new_tag("p")
            strong = soup.new_tag("strong")
            strong.string = header_text
            p.append(strong)
            bq.append(p)
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


def _preprocess_images(
    soup: BeautifulSoup,
    download: bool,
    image_dir: str = "assets",
    *,
    obsidian: bool = False,
) -> None:
    """ac:image → <img> tag (or Obsidian wikilink embed).

    If obsidian=True, outputs ![[filename]] syntax.
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
            if obsidian:
                # Obsidian wikilink embed: ![[filename]]
                div = soup.new_tag("div")
                div.string = f"![[{filename}]]"
                div["data-raw-markdown"] = "true"
                ac_image.replace_with(div)
                continue
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
