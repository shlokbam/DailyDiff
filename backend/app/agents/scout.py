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

def scout_ecosystem_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to collect all raw technology signals."""
    logger.info("Starting scouting node...")
    days = get_scout_window_days()
    
    github_signals = scout_github(days_ago=days)
    arxiv_signals = scout_arxiv()
    hf_signals = scout_huggingface()
    
    all_signals = github_signals + arxiv_signals + hf_signals
    logger.info(f"Total raw signals collected: {len(all_signals)}")
    
    return {"raw_signals": all_signals}
