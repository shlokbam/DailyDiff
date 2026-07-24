import os
import logging
import json
import httpx
from datetime import datetime
from pathlib import Path
from app.config import ARCHIVE_DIR, HISTORY_FILE_PATH
from app.database import init_db, init_history_file, append_to_history
from app.agents.graph import create_agent_graph

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DailyDiff.runner")

def build_markdown_brief(briefs: list, date_str: str) -> str:
    """Generate a clean, readable Markdown version of the daily brief."""
    md_content = f"# DailyDiff — {date_str}\n"
    md_content += "*We scan the noise. Five things survive.*\n\n"
    md_content += "---\n\n"
    
    if not briefs:
        md_content += "### No meaningful updates today. The technology ecosystem was quiet.\n"
        return md_content

    category_emojis = {
        "Tech Shift": "🔥",
        "Cool Tool": "💎",
        "Career & Learning": "🧠",
        "Ecosystem Update": "⚡",
        "Watchlist": "👀",
    }
    
    for item in briefs:
        category = item.get("category", "Tech Shift")
        emoji = category_emojis.get(category, "✨")
        
        md_content += f"## {emoji} {category.upper()}: {item.get('title')}\n\n"
        md_content += f"**What Happened:** {item.get('description')}\n\n"
        md_content += f"**Why It Matters:** {item.get('why_it_matters')}\n\n"
        md_content += f"**Who Cares:** {item.get('who_cares')}\n\n"
        
        url = item.get("source_url")
        if url:
            md_content += f"**Source:** [{url}]({url})\n\n"
            
        md_content += f"**Verdict:** `{item.get('verdict', 'WATCH')}` | **Confidence:** `{item.get('confidence', 80)}%`\n\n"
        md_content += "---\n\n"
        
    return md_content

def main():
    logger.info("Initializing DailyDiff system environments...")
    init_db()
    init_history_file()
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    mistral_key = os.getenv("MISTRAL_API_KEY")
    simulate = not gemini_key and not mistral_key
    
    briefs = []
    if simulate:
        logger.warning("No API keys found. Running in SIMULATION mode to verify file generation and formatting...")
        briefs = [
            {
                "category": "Career & Learning",
                "title": "Modern React Portfolio Template",
                "description": "**A high-performance, responsive React portfolio template built with Tailwind CSS was launched.**\n\nWhat happened: This open-source template includes built-in SEO optimization, a dark-mode toggle, and a section for GitHub integrations designed to help students stand out.",
                "why_it_matters": "Enables tech students and early-career developers to spin up a professional portfolio in minutes, boosting their job search readiness.",
                "who_cares": "CS students building portfolios, job-seeking software engineers.",
                "verdict": "INTEGRATE",
                "confidence": 95,
                "source_url": "https://github.com/learn-to-code/portfolio-template"
            },
            {
                "category": "Cool Tool",
                "title": "HTTPie visual API Client",
                "description": "**HTTPie released a web client focused on learning API request structures.**\n\nWhat happened: It offers an intuitive visual request editor and clean response parsing that makes testing endpoints and learning REST API concepts simple.",
                "why_it_matters": "Provides a zero-setup, highly visual alternative to Postman, making it perfect for beginners learning web development.",
                "who_cares": "React beginners, backend learners, web development students.",
                "verdict": "WATCH",
                "confidence": 90,
                "source_url": "https://github.com/httpie/httpie"
            }
        ]
    else:
        # Run the agent workflow
        logger.info("Starting LangGraph agent workflow execution...")
        graph = create_agent_graph()
        
        initial_state = {
            "raw_signals": [],
            "candidates": [],
            "researched_candidates": [],
            "vetted_candidates": [],
            "criticisms": [],
            "final_briefs": [],
            "errors": []
        }
        
        result_state = graph.invoke(initial_state)
        briefs = result_state.get("final_briefs", [])
    
    # Save the results
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    logger.info(f"Execution complete. Found {len(briefs)} briefs to publish for {date_str}.")
    
    # Save to history.json
    append_to_history(briefs, date_str)
    
    # Generate and save Markdown archive
    md_text = build_markdown_brief(briefs, date_str)
    
    # Hierarchical archive path: YYYY/MM/DD.md
    now = datetime.utcnow()
    year_dir = ARCHIVE_DIR / f"{now.year}"
    month_dir = year_dir / f"{now.month:02d}"
    month_dir.mkdir(parents=True, exist_ok=True)
    
    day_file_path = month_dir / f"{now.day:02d}.md"
    with open(day_file_path, "w") as f:
        f.write(md_text)
    logger.info(f"Saved Markdown archive to {day_file_path}")
    
    # Also save as latest.md in target data directory
    latest_md_path = HISTORY_FILE_PATH.parent / "latest.md"
    with open(latest_md_path, "w") as f:
        f.write(md_text)
    logger.info(f"Saved latest brief to {latest_md_path}")

    # Trigger subscription email dispatch via FastAPI webhook if backend URL is configured
    backend_url = os.getenv("BACKEND_API_URL")
    notify_token = os.getenv("NOTIFY_SECRET_TOKEN")
    if backend_url and briefs:
        logger.info(f"Triggering email notifications to backend at {backend_url}...")
        try:
            headers = {}
            if notify_token:
                headers["X-Auth-Token"] = notify_token
                
            payload = {
                "date": date_str,
                "published_at": datetime.utcnow().isoformat() + "Z",
                "briefs": briefs
            }
            
            response = httpx.post(f"{backend_url}/api/notify-subscribers", json=payload, headers=headers, timeout=120)
            if response.status_code == 200:
                logger.info("Successfully notified backend to send email briefs.")
            else:
                logger.error(f"Failed to notify backend: Status {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error calling notify-subscribers webhook: {e}")

if __name__ == "__main__":
    main()
