"""Tests for URL parser."""

import pytest

from confluence_2_md.url_parser import parse_confluence_url


def test_numeric_page_id():
    result = parse_confluence_url("123456")
    assert result["page_id"] == "123456"
    assert result["short_link"] is None
    assert result["base_url"] is None


def test_standard_url():
    url = "https://mycompany.atlassian.net/wiki/spaces/DEV/pages/98765/My+Page+Title"
    result = parse_confluence_url(url)
    assert result["page_id"] == "98765"
    assert result["space_key"] == "DEV"
    assert result["base_url"] == "https://mycompany.atlassian.net/wiki"


def test_short_url():
    url = "https://mycompany.atlassian.net/wiki/x/AbCdEf"
    result = parse_confluence_url(url)
    assert result["page_id"] is None
    assert result["short_link"] == "AbCdEf"
    assert result["base_url"] == "https://mycompany.atlassian.net/wiki"


def test_display_url():
    url = "https://mycompany.atlassian.net/wiki/display/TEAM/Page+Title"
    result = parse_confluence_url(url)
    assert result["page_id"] is None
    assert result["space_key"] == "TEAM"


def test_invalid_url():
    with pytest.raises(ValueError, match="Cannot parse"):
        parse_confluence_url("https://example.com/nothing")


def test_whitespace_stripped():
    result = parse_confluence_url("  123456  ")
    assert result["page_id"] == "123456"
