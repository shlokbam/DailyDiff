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
    # Query for repositories matching key topics with star thresholds, pushed recently
    queries = [
        f"stars:>100 pushed:>{since_date} topic:ai",
        f"stars:>100 pushed:>{since_date} topic:llm",
        f"stars:>100 pushed:>{since_date} topic:agents",
        f"stars:>150 pushed:>{since_date} topic:developer-tools",
    ]
    
    headers = {"User-Agent": "DailyDiff-Agent"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
    repos = []
    seen_ids = set()
    
    # We do a few target queries to fetch diverse AI/Dev tooling repos
    with httpx.Client() as client:
        for q in queries:
            url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=10"
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

def scout_arxiv() -> List[Dict[str, Any]]:
    """Scout arXiv for recent preprints in AI, Computational Linguistics, and Software Engineering."""
    url = (
        "http://export.arxiv.org/api/query?"
        "search_query=cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.SE"
        "&sortBy=submittedDate&sortOrder=descending"
        "&max_results=15"
    )
    papers = []
    import xml.etree.ElementTree as ET
    
    try:
        response = httpx.get(url, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            # arXiv namespace
            ns = {"arxiv": "http://www.w3.org/2005/Atom"}
            
            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip().replace("\n", " ")
                summary = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip().replace("\n", " ")
                paper_id_url = entry.find("{http://www.w3.org/2005/Atom}id").text.strip()
                
                papers.append({
                    "source": "arXiv",
                    "title": title,
                    "url": paper_id_url,
                    "description": summary[:300] + "...",
                    "full_abstract": summary,
                })
        else:
            logger.warning(f"arXiv API returned status {response.status_code}")
    except Exception as e:
        logger.error(f"arXiv scouting error: {e}")
        
    logger.info(f"arXiv scouted {len(papers)} raw signals.")
    return papers

def scout_huggingface() -> List[Dict[str, Any]]:
    """Scout Hugging Face Daily Papers API."""
    url = "https://huggingface.co/api/daily_papers"
    papers = []
    
    try:
        response = httpx.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for item in data[:10]: # Top 10 trending papers
                paper_info = item.get("paper", {})
                title = paper_info.get("title", "")
                summary = paper_info.get("summary", "")
                paper_id = paper_info.get("id", "")
                url_hf = f"https://huggingface.co/papers/{paper_id}" if paper_id else ""
                
                if title:
                    papers.append({
                        "source": "Hugging Face",
                        "title": title,
                        "url": url_hf,
                        "description": summary[:300] + "..." if summary else "",
                        "full_abstract": summary or "",
                    })
        else:
            logger.warning(f"Hugging Face daily papers API returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Hugging Face scouting error: {e}")
        
    logger.info(f"Hugging Face scouted {len(papers)} raw signals.")
    return papers

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

def scout_dev_to() -> List[Dict[str, Any]]:
    """Scout Dev.to RSS feed for trending technical articles."""
    logger.info("Scouting Dev.to RSS...")
    articles = []
    import xml.etree.ElementTree as ET
    import re
    
    try:
        url = "https://dev.to/feed"
        response = httpx.get(url, timeout=12)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            
            channel = root.find("channel")
            if channel is not None:
                items = channel.findall("item")[:10] # Top 10 articles
                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    desc_elem = item.find("description")
                    
                    title = title_elem.text.strip() if title_elem is not None else ""
                    link = link_elem.text.strip() if link_elem is not None else ""
                    desc = desc_elem.text.strip() if desc_elem is not None else ""
                    
                    desc_clean = re.sub(r'<[^>]*>', '', desc).strip()
                    desc_clean = desc_clean[:250] + "..." if len(desc_clean) > 250 else desc_clean
                    
                    if title and link:
                        articles.append({
                            "source": "Dev.to",
                            "title": title,
                            "url": link,
                            "description": desc_clean or f"Dev.to article: {title}."
                        })
        else:
            logger.warning(f"Dev.to RSS API returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Dev.to RSS scouting error: {e}")
        
    logger.info(f"Dev.to scouted {len(articles)} raw signals.")
    return articles

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
    arxiv_signals = scout_arxiv()
    hf_signals = scout_huggingface()
    hn_signals = scout_hacker_news()
    dev_to_signals = scout_dev_to()
    release_signals = scout_github_releases(days_ago=days)
    
    all_signals = github_signals + arxiv_signals + hf_signals + hn_signals + dev_to_signals + release_signals
    logger.info(f"Total raw signals collected: {len(all_signals)}")
    
    return {"raw_signals": all_signals}
