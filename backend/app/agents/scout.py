import logging
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.config import GITHUB_TOKEN
from app.agents.state import AgentState

logger = logging.getLogger("DailyDiff.scout")

def get_scout_window_days() -> int:
    """Determine how many days back to search based on the current weekday."""
    # Monday is 0. If Monday, look back 3 days (covers Friday, Saturday, Sunday).
    # Otherwise, look back 2 days.
    current_weekday = datetime.utcnow().weekday()
    return 3 if current_weekday == 0 else 2

def scout_github(days_ago: int) -> List[Dict[str, Any]]:
    """Scout GitHub for active/trending repositories pushed recently."""
    since_date = (datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    created_since = (datetime.utcnow() - timedelta(days=45)).strftime("%Y-%m-%d")
    # Query for repositories matching key developer/utility topics for students/early careers
    queries = [
        f"stars:>15 pushed:>{since_date} created:>{created_since} topic:learn-to-code",
        f"stars:>30 pushed:>{since_date} created:>{created_since} topic:web-development",
        f"stars:>20 pushed:>{since_date} created:>{created_since} topic:beginner-friendly",
        f"stars:>30 pushed:>{since_date} created:>{created_since} topic:productivity",
        f"stars:>50 pushed:>{since_date} topic:developer-tools",
    ]
    
    headers = {"User-Agent": "DailyDiff-Agent"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
    repos = []
    seen_ids = set()
    
    # We do a few target queries to fetch diverse developer utility repos
    with httpx.Client() as client:
        for q in queries:
            url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=5"
            try:
                response = client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", []):
                        repo_id = item["id"]
                        if repo_id not in seen_ids:
                            seen_ids.add(repo_id)
                            repos.append({
                                "source": "GitHub",
                                "title": item["name"],
                                "full_name": item["full_name"],
                                "url": item["html_url"],
                                "description": item["description"] or "",
                                "stars": item["stargazers_count"],
                                "forks": item["forks_count"],
                                "language": item["language"] or "Unknown",
                            })
                else:
                    logger.warning(f"GitHub Search API returned status {response.status_code} for query: {q}")
            except Exception as e:
                logger.error(f"GitHub scouting error: {e}")
                
    logger.info(f"GitHub scouted {len(repos)} raw signals.")
    return repos




def scout_hacker_news() -> List[Dict[str, Any]]:
    """Scout Hacker News top stories with score >= 60."""
    logger.info("Scouting Hacker News...")
    stories = []
    
    try:
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        response = httpx.get(top_stories_url, timeout=10)
        if response.status_code == 200:
            story_ids = response.json()[:25] # Fetch top 25 story IDs
            
            with httpx.Client() as client:
                for story_id in story_ids:
                    item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    try:
                        item_res = client.get(item_url, timeout=5)
                        if item_res.status_code == 200:
                            item = item_res.json()
                            if not item:
                                continue
                            
                            url = item.get("url")
                            score = item.get("score", 0)
                            title = item.get("title", "")
                            
                            if url and score >= 60 and item.get("type") == "story" and title:
                                stories.append({
                                    "source": "Hacker News",
                                    "title": title,
                                    "url": url,
                                    "description": f"Hacker News top story (Score: {score}). Title: {title}.",
                                    "score": score
                                })
                    except Exception as e:
                        logger.error(f"Error fetching HN item {story_id}: {e}")
        else:
            logger.warning(f"Hacker News top stories API returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Hacker News scouting error: {e}")
        
    logger.info(f"Hacker News scouted {len(stories)} raw signals.")
    return stories

def fetch_rss_signals(url: str, source_name: str, max_items: int = 10, headers: dict = None) -> List[Dict[str, Any]]:
    """Helper to parse generic RSS/Atom feeds into raw signals."""
    logger.info(f"Scouting {source_name} RSS feed...")
    signals = []
    import xml.etree.ElementTree as ET
    import re
    
    if headers is None:
        headers = {"User-Agent": "DailyDiff-Agent/1.0"}
        
    try:
        response = httpx.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError as pe:
                logger.error(f"XML parse error for {source_name}: {pe}")
                return []
                
            channel = root.find("channel")
            if channel is not None:
                # Standard RSS format
                items = channel.findall("item")[:max_items]
                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    desc_elem = item.find("description")
                    
                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                    link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                    desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                    
                    # Clean up HTML tags from description
                    desc_clean = re.sub(r'<[^>]*>', '', desc).strip()
                    desc_clean = desc_clean[:300] + "..." if len(desc_clean) > 300 else desc_clean
                    
                    if title and link:
                        signals.append({
                            "source": source_name,
                            "title": title,
                            "url": link,
                            "description": desc_clean or f"{source_name} article: {title}."
                        })
            else:
                # Try Atom feed structure
                namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall(".//atom:entry", namespaces)
                if not entries:
                    entries = root.findall(".//entry")
                
                for entry in entries[:max_items]:
                    title_elem = entry.find("{http://www.w3.org/2005/Atom}title") or entry.find("title")
                    link_elem = entry.find("{http://www.w3.org/2005/Atom}link") or entry.find("link")
                    desc_elem = entry.find("{http://www.w3.org/2005/Atom}content") or entry.find("{http://www.w3.org/2005/Atom}summary") or entry.find("content") or entry.find("summary")
                    
                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                    
                    link = ""
                    if link_elem is not None:
                        link = link_elem.attrib.get("href", "")
                        if not link and link_elem.text:
                            link = link_elem.text.strip()
                            
                    desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                    desc_clean = re.sub(r'<[^>]*>', '', desc).strip()
                    desc_clean = desc_clean[:300] + "..." if len(desc_clean) > 300 else desc_clean
                    
                    if title and link:
                        signals.append({
                            "source": source_name,
                            "title": title,
                            "url": link,
                            "description": desc_clean or f"{source_name} entry: {title}."
                        })
        else:
            logger.warning(f"{source_name} RSS returned status {response.status_code}")
    except Exception as e:
        logger.error(f"{source_name} RSS scouting error: {e}")
        
    logger.info(f"{source_name} scouted {len(signals)} raw signals.")
    return signals

def scout_dev_to() -> List[Dict[str, Any]]:
    """Scout Dev.to RSS feed for trending technical articles."""
    return fetch_rss_signals("https://dev.to/feed", "Dev.to", max_items=10)

def scout_freecodecamp() -> List[Dict[str, Any]]:
    """Scout FreeCodeCamp RSS feed for beginner friendly tutorials and guides."""
    return fetch_rss_signals("https://www.freecodecamp.org/news/rss/", "FreeCodeCamp", max_items=10)

def scout_product_hunt() -> List[Dict[str, Any]]:
    """Scout Product Hunt RSS feed for new technical products and tools."""
    return fetch_rss_signals("https://www.producthunt.com/feed", "Product Hunt", max_items=12)

def scout_reddit() -> List[Dict[str, Any]]:
    """Scout Reddit webdev and learnprogramming subreddits via RSS feeds."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    webdev_signals = fetch_rss_signals("https://www.reddit.com/r/webdev/.rss", "Reddit /r/webdev", max_items=8, headers=headers)
    learnprog_signals = fetch_rss_signals("https://www.reddit.com/r/learnprogramming/.rss", "Reddit /r/learnprogramming", max_items=8, headers=headers)
    return webdev_signals + learnprog_signals

def scout_github_releases(days_ago: int) -> List[Dict[str, Any]]:
    """Scout major framework repositories for new releases in the window."""
    logger.info("Scouting GitHub releases...")
    releases = []
    
    target_repos = [
        "facebook/react",
        "vercel/next.js",
        "fastapi/fastapi",
        "tailwindlabs/tailwindcss",
        "django/django",
        "golang/go"
    ]
    
    headers = {"User-Agent": "DailyDiff-Agent"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
    since_date = datetime.utcnow() - timedelta(days=days_ago)
    
    with httpx.Client() as client:
        for repo in target_repos:
            url = f"https://api.github.com/repos/{repo}/releases"
            try:
                response = client.get(url, headers=headers, timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        continue
                    
                    latest = data[0]
                    pub_date_str = latest.get("published_at")
                    if pub_date_str:
                        pub_date = datetime.strptime(pub_date_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                        if pub_date >= since_date:
                            releases.append({
                                "source": "GitHub Release",
                                "title": f"{repo} Release: {latest.get('tag_name')}",
                                "url": latest.get("html_url"),
                                "description": f"New official release for {repo}. Tag: {latest.get('tag_name')}. Features: {latest.get('name', '')}. Details: {latest.get('body', '')[:300]}..."
                            })
                else:
                    logger.warning(f"GitHub Releases API returned status {response.status_code} for repo: {repo}")
            except Exception as e:
                logger.error(f"GitHub release scouting error for {repo}: {e}")
                
    logger.info(f"GitHub Releases scouted {len(releases)} raw signals.")
    return releases

def scout_ecosystem_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to collect all raw technology signals."""
    logger.info("Starting scouting node...")
    days = get_scout_window_days()
    
    github_signals = scout_github(days_ago=days)
    hn_signals = scout_hacker_news()
    dev_to_signals = scout_dev_to()
    freecodecamp_signals = scout_freecodecamp()
    product_hunt_signals = scout_product_hunt()
    reddit_signals = scout_reddit()
    release_signals = scout_github_releases(days_ago=days)
    
    all_signals = (
        github_signals + 
        hn_signals + 
        dev_to_signals + 
        freecodecamp_signals + 
        product_hunt_signals + 
        reddit_signals + 
        release_signals
    )
    logger.info(f"Total raw signals collected: {len(all_signals)}")
    
    return {"raw_signals": all_signals}

