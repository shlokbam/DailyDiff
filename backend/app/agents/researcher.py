import logging
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from app.agents.state import AgentState
from app.config import GITHUB_TOKEN

logger = logging.getLogger("DailyDiff.researcher")

def fetch_github_readme(full_name: str) -> str:
    """Fetch the README content of a GitHub repository."""
    # We can try fetching from raw github content directly for main or master branch
    headers = {"User-Agent": "DailyDiff-Agent"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{full_name}/{branch}/README.md"
        try:
            response = httpx.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Return first 4000 characters to avoid flooding LLM context
                return response.text[:4000]
        except Exception:
            continue
            
    # Fallback to GitHub Repository API details
    api_url = f"https://api.github.com/repos/{full_name}"
    try:
        response = httpx.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return f"Repo: {data.get('name')}\nDescription: {data.get('description')}\nTopics: {', '.join(data.get('topics', []))}"
    except Exception as e:
        logger.error(f"GitHub API fallback readme fetch error: {e}")
        
    return ""

def fetch_web_page_text(url: str) -> str:
    """Fetch text from a regular web page and extract clean visible text."""
    try:
        response = httpx.get(url, headers={"User-Agent": "DailyDiff-Agent"}, timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove scripts and style elements
            for script in soup(["script", "style", "meta", "noscript"]):
                script.decompose()
            text = soup.get_text(separator=" ")
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = "\n".join(chunk for chunk in chunks if chunk)
            return clean_text[:4000]
    except Exception as e:
        logger.error(f"External web scraping error for {url}: {e}")
    return ""

def research_candidates_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to collect detailed documentation and abstracts for candidates."""
    logger.info("Starting Research Agent node...")
    candidates = state.get("candidates", [])
    if not candidates:
        logger.warning("No candidates to research.")
        return {"researched_candidates": []}
        
    researched = []
    
    for c in candidates:
        logger.info(f"Researching: {c['title']} ({c['source']})")
        detailed = ""
        
        if c["source"] == "GitHub":
            detailed = fetch_github_readme(c["full_name"])
        elif c["source"] in ["arXiv", "Hugging Face"]:
            # Use full abstract compiled during scouting
            detailed = c.get("full_abstract", c.get("description", ""))
        else:
            detailed = fetch_web_page_text(c["url"])
            
        new_candidate = c.copy()
        new_candidate["detailed_content"] = detailed or c.get("description", "")
        researched.append(new_candidate)
        
    logger.info(f"Research node complete: processed {len(researched)} candidates.")
    return {"researched_candidates": researched}
