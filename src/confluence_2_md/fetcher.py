"""Confluence API client for fetching pages and attachments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from confluence_2_md.config import Settings


class ConfluenceError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _should_retry(exc: BaseException) -> bool:
    """Don't retry on 4xx client errors (except 429 rate limit)."""
    if isinstance(exc, ConfluenceError) and exc.status_code:
        if 400 <= exc.status_code < 500 and exc.status_code != 429:
            return False
    return True


@dataclass
class Attachment:
    filename: str
    media_type: str
    download_url: str


@dataclass
class PageData:
    page_id: str
    title: str
    html_content: str
    url: str
    attachments: list[Attachment] = field(default_factory=list)


class ConfluenceFetcher:
    def __init__(self, settings: Settings) -> None:
        settings.validate_required()
        self.base_url = settings.CONFLUENCE_BASE_URL.rstrip("/")
        self.api_url = f"{self.base_url}/api/v2"
        self.auth = (settings.CONFLUENCE_USERNAME, settings.CONFLUENCE_TOKEN)

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_should_retry),
        reraise=True,
    )
    def fetch_page(self, page_id: str) -> PageData:
        """Fetch a page by ID with storage-format body."""
        url = f"{self.api_url}/pages/{page_id}"
        params = {"body-format": "storage"}

        with httpx.Client(auth=self.auth, timeout=30.0) as client:
            resp = client.get(url, headers=self._headers(), params=params)

            if resp.status_code == 404:
                raise ConfluenceError(f"Page not found: {page_id}", 404)
            if resp.status_code != 200:
                raise ConfluenceError(
                    f"Failed to fetch page {page_id}: {resp.text}",
                    resp.status_code,
                )

            data = resp.json()

        html = data.get("body", {}).get("storage", {}).get("value", "")
        title = data.get("title", "")
        page_url = f"{self.base_url}/pages/{page_id}"

        # Fetch attachments
        attachments = self._fetch_attachments(page_id)

        return PageData(
            page_id=page_id,
            title=title,
            html_content=html,
            url=page_url,
            attachments=attachments,
        )

    def resolve_short_link(self, short_code: str) -> str:
        """Resolve a short link (/wiki/x/CODE) by following the redirect to get the page ID."""
        url = f"{self.base_url}/x/{short_code}"

        with httpx.Client(
            auth=self.auth, timeout=30.0, follow_redirects=True
        ) as client:
            resp = client.get(url)

            if resp.status_code != 200:
                raise ConfluenceError(
                    f"Failed to resolve short link: {short_code}", resp.status_code
                )

            # The final URL after redirect should contain the page ID
            final_url = str(resp.url)

        from confluence_2_md.url_parser import parse_confluence_url

        parsed = parse_confluence_url(final_url)
        if parsed["page_id"]:
            return parsed["page_id"]
        raise ConfluenceError(
            f"Could not extract page ID from resolved URL: {final_url}"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _fetch_attachments(self, page_id: str) -> list[Attachment]:
        """Fetch the list of attachments for a page."""
        url = f"{self.api_url}/pages/{page_id}/attachments"

        with httpx.Client(auth=self.auth, timeout=30.0) as client:
            resp = client.get(url, headers=self._headers())
            if resp.status_code != 200:
                return []

            data = resp.json()

        attachments = []
        for item in data.get("results", []):
            title = item.get("title", "")
            media_type = item.get("mediaType", "")
            download_path = item.get("downloadLink", "")
            if download_path:
                download_url = f"{self.base_url}{download_path}"
            else:
                download_url = ""
            attachments.append(
                Attachment(
                    filename=title,
                    media_type=media_type,
                    download_url=download_url,
                )
            )
        return attachments

    def download_attachment(self, attachment: Attachment, dest_dir: Path) -> Path:
        """Download an attachment to a local directory."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / attachment.filename

        with httpx.Client(
            auth=self.auth, timeout=60.0, follow_redirects=True, verify=False
        ) as client:
            with client.stream("GET", attachment.download_url) as resp:
                resp.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        return dest_path
