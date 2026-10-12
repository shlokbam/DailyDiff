import pytest
from app.agents.scout import parse_feed_content

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
