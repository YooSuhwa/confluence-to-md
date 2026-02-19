"""Tests for Confluence fetcher (using httpx mocking)."""

import pytest

from confluence_2_md.config import Settings
from confluence_2_md.fetcher import ConfluenceError, ConfluenceFetcher


@pytest.fixture
def settings():
    return Settings(
        CONFLUENCE_BASE_URL="https://test.atlassian.net/wiki",
        CONFLUENCE_USERNAME="user@test.com",
        CONFLUENCE_TOKEN="fake-token",
    )


@pytest.fixture
def fetcher(settings):
    return ConfluenceFetcher(settings)


def _make_page_response(page_id="123", title="Test Page", html="<p>Hello</p>"):
    return {
        "id": page_id,
        "title": title,
        "body": {"storage": {"value": html}},
    }


def _make_attachments_response(items=None):
    if items is None:
        items = []
    return {"results": items}


class TestFetchPage:
    def test_fetch_page_success(self, fetcher, httpx_mock):
        httpx_mock.add_response(
            url="https://test.atlassian.net/wiki/api/v2/pages/123?body-format=storage",
            json=_make_page_response(),
        )
        httpx_mock.add_response(
            url="https://test.atlassian.net/wiki/api/v2/pages/123/attachments",
            json=_make_attachments_response(),
        )

        page = fetcher.fetch_page("123")
        assert page.page_id == "123"
        assert page.title == "Test Page"
        assert page.html_content == "<p>Hello</p>"

    def test_fetch_page_not_found(self, fetcher, httpx_mock):
        httpx_mock.add_response(
            url="https://test.atlassian.net/wiki/api/v2/pages/999?body-format=storage",
            status_code=404,
        )

        with pytest.raises(ConfluenceError, match="Page not found"):
            fetcher.fetch_page("999")


class TestFetchAttachments:
    def test_attachments_listed(self, fetcher, httpx_mock):
        httpx_mock.add_response(
            url="https://test.atlassian.net/wiki/api/v2/pages/123?body-format=storage",
            json=_make_page_response(),
        )
        httpx_mock.add_response(
            url="https://test.atlassian.net/wiki/api/v2/pages/123/attachments",
            json=_make_attachments_response([
                {
                    "title": "image.png",
                    "mediaType": "image/png",
                    "downloadLink": "/download/attachments/123/image.png",
                }
            ]),
        )

        page = fetcher.fetch_page("123")
        assert len(page.attachments) == 1
        assert page.attachments[0].filename == "image.png"
