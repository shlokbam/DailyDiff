import logging
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Tuple
from app.agents.state import AgentState
from app.config import GITHUB_TOKEN
from app.run_health import health

logger = logging.getLogger("DailyDiff.researcher")

MAX_EVIDENCE_CHARS = 1800

def fetch_github_readme(full_name: str) -> Tuple[str, str]:
    """
    Fetch the README content of a GitHub repository.
    Returns a tuple of (content, content_source_kind).
    """
    headers = {"User-Agent": "DailyDiff-Agent"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{full_name}/{branch}/README.md"
        try:
            response = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
            if response.status_code == 200 and response.text.strip():
                return response.text[:MAX_EVIDENCE_CHARS], "readme"
        except Exception:
            continue

    # Fallback to GitHub Repository API details
    api_url = f"https://api.github.com/repos/{full_name}"
    try:
        response = httpx.get(api_url, headers=headers, timeout=10, follow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            topics = data.get("topics", [])
            text = f"Repo: {data.get('name')}\nDescription: {data.get('description')}\nTopics: {', '.join(topics)}"
            return text[:MAX_EVIDENCE_CHARS], "api_fallback"
    except Exception as e:
        logger.error(f"GitHub API fallback readme fetch error: {e}")

    return "", "empty"

def fetch_web_page_text(url: str) -> Tuple[str, str]:
    """
    Fetch text from a regular web page and extract clean visible text.
    Returns a tuple of (content, content_source_kind).
    """
    try:
        response = httpx.get(url, headers={"User-Agent": "DailyDiff-Agent"}, timeout=12, follow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style", "meta", "noscript", "svg"]):
                script.decompose()
            text = soup.get_text(separator=" ")
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = "\n".join(chunk for chunk in chunks if chunk).strip()
            if clean_text:
                return clean_text[:MAX_EVIDENCE_CHARS], "web_page"
    except Exception as e:
        logger.error(f"External web scraping error for {url}: {e}")
    return "", "empty"

def research_candidates_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to collect detailed documentation and abstracts for candidates."""
    logger.info("Starting Research Agent node...")
    candidates = state.get("candidates", [])
    if not candidates:
        logger.warning("No candidates to research.")
        health.set_count("researched", 0)
        return {"researched_candidates": []}

    researched = []

    for c in candidates:
        logger.info(f"Researching: {c.get('title')} ({c.get('source')})")
        detailed = ""
        source_kind = "empty"

        source = c.get("source", "")
        url = c.get("url", "")

        if source == "GitHub" and c.get("full_name"):
            detailed, source_kind = fetch_github_readme(c["full_name"])
        elif source in ["arXiv", "Hugging Face"] and c.get("full_abstract"):
            detailed = c["full_abstract"][:MAX_EVIDENCE_CHARS]
            source_kind = "web_page"
        elif url and url.startswith("http"):
            detailed, source_kind = fetch_web_page_text(url)

        if not detailed:
            detailed = ""
            source_kind = "description_only" if c.get("description") else "empty"

        health.set_content_source(url, source_kind)

        new_candidate = c.copy()
        new_candidate["detailed_content"] = detailed
        new_candidate["content_source"] = source_kind
        researched.append(new_candidate)

    logger.info(f"Research node complete: processed {len(researched)} candidates.")
    health.set_count("researched", len(researched))
    return {"researched_candidates": researched}
