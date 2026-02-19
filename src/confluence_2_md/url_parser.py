"""Parse Confluence URLs to extract page IDs."""

import re
from urllib.parse import urlparse


def parse_confluence_url(url_or_id: str) -> dict:
    """Parse a Confluence URL or page ID and extract components.

    Supported formats:
        - Standard URL: https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Title
        - Short URL: https://domain.atlassian.net/wiki/x/AbCdEf
        - Display URL: https://domain.atlassian.net/wiki/display/SPACE/Title
        - Page ID only: "123456"

    Returns:
        dict with keys: page_id (str|None), short_link (str|None),
                        base_url (str|None), space_key (str|None)
    """
    url_or_id = url_or_id.strip()

    # Pure numeric page ID
    if re.fullmatch(r"\d+", url_or_id):
        return {
            "page_id": url_or_id,
            "short_link": None,
            "base_url": None,
            "space_key": None,
        }

    parsed = urlparse(url_or_id)
    if not parsed.scheme:
        # Try adding https://
        parsed = urlparse(f"https://{url_or_id}")

    base_url = f"{parsed.scheme}://{parsed.netloc}/wiki"
    path = parsed.path

    # Standard page URL: /wiki/spaces/SPACE/pages/123456/Title
    m = re.search(r"/wiki/spaces/([^/]+)/pages/(\d+)", path)
    if m:
        return {
            "page_id": m.group(2),
            "short_link": None,
            "base_url": base_url,
            "space_key": m.group(1),
        }

    # Legacy display URL: /wiki/display/SPACE/Title (no page ID available)
    m = re.search(r"/wiki/display/([^/]+)/", path)
    if m:
        return {
            "page_id": None,
            "short_link": None,
            "base_url": base_url,
            "space_key": m.group(1),
        }

    # Short URL: /wiki/x/AbCdEf
    m = re.search(r"/wiki/x/([A-Za-z0-9_-]+)", path)
    if m:
        return {
            "page_id": None,
            "short_link": m.group(1),
            "base_url": base_url,
            "space_key": None,
        }

    # Fallback: try to find any numeric page ID in the path
    m = re.search(r"/pages/(\d+)", path)
    if m:
        return {
            "page_id": m.group(1),
            "short_link": None,
            "base_url": base_url,
            "space_key": None,
        }

    raise ValueError(f"Cannot parse Confluence URL or page ID: {url_or_id}")
