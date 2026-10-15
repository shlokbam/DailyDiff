from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import patch, MagicMock
from app.agents.scout import parse_feed_content, scout_github_releases, scout_github

SAMPLE_ATOM_FEED = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Product Hunt Daily</title>
  <link href="https://www.producthunt.com/"/>
  <updated>2026-10-12T00:00:00Z</updated>
  <id>tag:producthunt.com,2026:feed</id>
  <entry>
    <title>DevToolX - Local LLM Manager</title>
    <link href="https://www.producthunt.com/posts/devtoolx"/>
    <id>tag:producthunt.com,2026:post:12345</id>
    <updated>2026-10-12T00:00:00Z</updated>
    <summary>A fast desktop UI to organize local models on your device.</summary>
  </entry>
</feed>
"""

SAMPLE_RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Dev.to Articles</title>
    <link>https://dev.to</link>
    <description>Recent posts on Dev.to</description>
    <item>
      <title>Understanding Modern Concurrency in Python</title>
      <link>https://dev.to/user/concurrency-guide</link>
      <description><![CDATA[A practical deep dive into async programming and thread pools.]]></description>
      <pubDate>Mon, 12 Oct 2026 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

def test_atom_feed_parsing_yields_signal():
    signals = parse_feed_content(SAMPLE_ATOM_FEED, "Product Hunt")
    assert len(signals) == 1, f"Expected exactly 1 signal, got {len(signals)}"
    sig = signals[0]
    assert sig["source"] == "Product Hunt"
    assert sig["title"] == "DevToolX - Local LLM Manager"
    assert sig["url"] == "https://www.producthunt.com/posts/devtoolx"
    assert "local models" in sig["description"]

def test_rss_feed_parsing_yields_signal():
    signals = parse_feed_content(SAMPLE_RSS_FEED, "Dev.to")
    assert len(signals) == 1, f"Expected exactly 1 signal, got {len(signals)}"
    sig = signals[0]
    assert sig["source"] == "Dev.to"
    assert sig["title"] == "Understanding Modern Concurrency in Python"
    assert sig["url"] == "https://dev.to/user/concurrency-guide"
    assert "async programming" in sig["description"]

def test_null_release_body_is_safe():
    """Verify that a GitHub release with a null body does not crash."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "tag_name": "v1.0.0",
            "name": "Release v1.0.0",
            "html_url": "https://github.com/example/repo/releases/v1.0.0",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "body": None,  # Null body
        }
    ]
    with patch("httpx.Client") as mock_client_cls:
        client_instance = mock_client_cls.return_value.__enter__.return_value
        client_instance.get.return_value = mock_resp
        releases = scout_github_releases(days_ago=10)
        assert len(releases) > 0
        assert "Details: ..." in releases[0]["description"]


def test_github_signal_has_full_name_and_created_filter():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "id": 1,
                "name": "r",
                "full_name": "o/r",
                "html_url": "https://github.com/o/r",
                "description": "d",
                "stargazers_count": 5,
                "forks_count": 1,
                "language": "Python",
            }
        ]
    }
    with patch("httpx.Client") as mock_client_cls:
        client_instance = mock_client_cls.return_value.__enter__.return_value
        client_instance.get.return_value = mock_resp
        signals = scout_github(days_ago=2)
        assert signals[0]["full_name"] == "o/r"
        called_urls = [call.args[0] for call in client_instance.get.call_args_list if call.args]
        assert any("created:" in url for url in called_urls)

