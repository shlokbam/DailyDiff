"""Scout node: gathers tech signals from GitHub, HN, Dev.to, FCC, Product Hunt, Reddit, and releases."""

import logging, re, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx
from app.config import GITHUB_TOKEN
from app.agents.state import AgentState
from app.run_health import health

logger = logging.getLogger("DailyDiff.scout")

def get_scout_window_days() -> int:
    return 3 if datetime.now(timezone.utc).weekday() == 0 else 2

def _find_elem(parent: ET.Element, tags: List[str]) -> Optional[ET.Element]:
    """Finds first matching child element without relying on truth-testing an Element."""
    for tag in tags:
        el = parent.find(tag)
        if el is not None:
            return el
    return None

def parse_feed_content(content: bytes, source_name: str, max_items: int = 10) -> List[Dict[str, Any]]:
    """Parse RSS or Atom XML content into raw signals."""
    try:
        root = ET.fromstring(content)
    except Exception as e:
        logger.error(f"Feed parse error for {source_name}: {e}")
        return []

    signals, channel = [], root.find("channel")
    if channel is not None:
        for item in channel.findall("item")[:max_items]:
            t, l = item.findtext("title", "").strip(), item.findtext("link", "").strip()
            d = re.sub(r'<[^>]*>', '', item.findtext("description", "")).strip()[:300]
            if t and l:
                signals.append({"source": source_name, "title": t, "url": l, "description": d or f"{source_name}: {t}"})
    else:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        if not entries:
            entries = root.findall(".//entry")
        for entry in entries[:max_items]:
            t_elem = _find_elem(entry, ["{http://www.w3.org/2005/Atom}title", "title"])
            t = (t_elem.text if t_elem is not None and t_elem.text else "").strip()
            l_elem = _find_elem(entry, ["{http://www.w3.org/2005/Atom}link", "link"])
            link = (l_elem.attrib.get("href") or l_elem.text or "").strip() if l_elem is not None else ""
            s_elem = _find_elem(entry, ["{http://www.w3.org/2005/Atom}summary", "summary", "{http://www.w3.org/2005/Atom}content", "content"])
            raw_d = s_elem.text if s_elem is not None and s_elem.text else ""
            d = re.sub(r'<[^>]*>', '', raw_d).strip()[:300]
            if t and link:
                signals.append({"source": source_name, "title": t, "url": link, "description": d or f"{source_name}: {t}"})
    return signals

def fetch_rss(url: str, source_name: str, max_items: int = 10, headers: dict = None) -> List[Dict[str, Any]]:
    try:
        r = httpx.get(url, headers=headers or {"User-Agent": "DailyDiff-Agent/1.0"}, timeout=12, follow_redirects=True)
        if r.status_code == 200:
            return parse_feed_content(r.content, source_name, max_items)
    except Exception as e:
        logger.warning(f"Error scouting {source_name}: {e}")
    return []

def scout_github(days_ago: int) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    created_since = (now - timedelta(days=45)).strftime("%Y-%m-%d")
    queries = [
        f"stars:>15 pushed:>{since} created:>{created_since} topic:learn-to-code",
        f"stars:>30 pushed:>{since} created:>{created_since} topic:web-development",
        f"stars:>20 pushed:>{since} created:>{created_since} topic:beginner-friendly",
        f"stars:>30 pushed:>{since} created:>{created_since} topic:productivity",
        f"stars:>50 pushed:>{since} topic:developer-tools",
    ]
    headers = {"User-Agent": "DailyDiff-Agent", **({"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {})}
    repos, seen = [], set()
    with httpx.Client(follow_redirects=True) as client:
        for q in queries:
            try:
                r = client.get(f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=5", headers=headers, timeout=8)
                if r.status_code == 200:
                    for it in r.json().get("items", []):
                        if it["id"] not in seen:
                            seen.add(it["id"])
                            repos.append({
                                "source": "GitHub",
                                "title": it["name"],
                                "full_name": it["full_name"],
                                "url": it["html_url"],
                                "description": it.get("description") or f"GitHub repository {it['name']}",
                                "stars": it.get("stargazers_count", 0),
                                "forks": it.get("forks_count", 0),
                                "language": it.get("language") or "Unknown",
                            })
            except Exception as e:
                logger.warning(f"GitHub search error for {q}: {e}")
    return repos

def scout_hacker_news() -> List[Dict[str, Any]]:
    stories = []
    try:
        with httpx.Client(follow_redirects=True) as client:
            r = client.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=8)
            if r.status_code == 200:
                for sid in r.json()[:15]:
                    item_resp = client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5)
                    if item_resp.status_code == 200:
                        d = item_resp.json() or {}
                        if d.get("title") and d.get("url"):
                            stories.append({"source": "Hacker News", "title": d["title"], "url": d["url"], "description": f"Hacker News top story (Score: {d.get('score', 0)}): {d['title']}"})
    except Exception as e:
        logger.warning(f"Hacker News scouting error: {e}")
    return stories

def scout_github_releases(days_ago: int) -> List[Dict[str, Any]]:
    targets = ["facebook/react", "vercel/next.js", "fastapi/fastapi", "tailwindlabs/tailwindcss", "golang/go"]
    headers = {"User-Agent": "DailyDiff-Agent", **({"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {})}
    since = datetime.now(timezone.utc) - timedelta(days=days_ago)
    releases = []
    with httpx.Client(follow_redirects=True) as client:
        for repo in targets:
            try:
                r = client.get(f"https://api.github.com/repos/{repo}/releases", headers=headers, timeout=8)
                if r.status_code == 200 and isinstance(r.json(), list) and r.json():
                    latest = r.json()[0]
                    pub = latest.get("published_at")
                    if pub and datetime.strptime(pub.replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc) >= since:
                        body = (latest.get("body") or "")[:300]
                        releases.append({"source": "GitHub Release", "title": f"{repo} Release: {latest.get('tag_name')}", "url": latest.get("html_url"), "description": f"New release for {repo}. Tag: {latest.get('tag_name')}. Details: {body}..."})
            except Exception as e:
                logger.warning(f"Release scout error for {repo}: {e}")
    return releases

def scout_ecosystem_node(state: AgentState) -> Dict[str, Any]:
    days = get_scout_window_days()
    signals = (
        scout_github(days) + scout_hacker_news() + fetch_rss("https://dev.to/feed", "Dev.to", 8)
        + fetch_rss("https://www.freecodecamp.org/news/rss/", "FreeCodeCamp", 8)
        + fetch_rss("https://www.producthunt.com/feed", "Product Hunt", 10)
        + fetch_rss("https://www.reddit.com/r/webdev/.rss", "Reddit /r/webdev", 6, headers={"User-Agent": "DailyDiff:v1"})
        + scout_github_releases(days)
    )
    health.set_count("raw_signals", len(signals))
    return {"raw_signals": signals}
