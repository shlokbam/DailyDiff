import os
import sys
import time
import logging
import json
import subprocess
import httpx
from datetime import datetime, timezone
from pathlib import Path
from app.config import ARCHIVE_DIR, HISTORY_FILE_PATH, DATA_DIR
from app.database import init_db, init_history_file, append_to_history
from app.agents.graph import create_agent_graph
from app.agents.researcher import MAX_EVIDENCE_CHARS
from app.run_health import health
from app.checks import validate_briefs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DailyDiff.runner")

def get_git_sha() -> str:
    """Retrieve current commit SHA for run provenance."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"

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

    show_confidence = os.getenv("SHOW_CONFIDENCE", "false").lower() == "true"

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

        if show_confidence and item.get("confidence") is not None:
            md_content += f"**Verdict:** `{item.get('verdict', 'WATCH')}` | **Confidence:** `{item.get('confidence')}%`\n\n"
        else:
            md_content += f"**Verdict:** `{item.get('verdict', 'WATCH')}`\n\n"

        md_content += "---\n\n"

    return md_content

def build_run_snapshot(date_str: str, result_state: dict, briefs: list, failure_reasons: list = None) -> dict:
    """Build a complete state and provenance snapshot for data/runs."""
    evidence_by_url = {}
    for c in result_state.get("researched_candidates", []):
        url = c.get("url")
        if url:
            evidence_by_url[url] = f"{c.get('description', '')} {(c.get('detailed_content') or '')[:MAX_EVIDENCE_CHARS]}"

    health_dict = health.to_dict()
    snapshot = {
        "date": date_str,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": get_git_sha(),
        "health": health_dict,
        "decisions": health_dict.get("decisions", {}),
        "raw_signals": [
            {
                "title": s.get("title"),
                "url": s.get("url"),
                "source": s.get("source"),
                "description": (s.get("description") or "")[:500]
            }
            for s in result_state.get("raw_signals", [])
        ],
        "skeptic_kept": [
            c.get("url") for c in result_state.get("candidates", [])
        ],
        "candidates": [
            {
                "title": c.get("title"),
                "url": c.get("url"),
                "source": c.get("source"),
                "content_source": c.get("content_source"),
                "evidence": (c.get("detailed_content") or "")[:MAX_EVIDENCE_CHARS]
            }
            for c in result_state.get("researched_candidates", [])
        ],
        "verifier_results": [
            {
                "title": c.get("title"),
                "url": c.get("url"),
                "status": c.get("verifier_status", "VALID"),
                "reason": c.get("verifier_reason", "")
            }
            for c in result_state.get("vetted_candidates", [])
        ],
        "analyst_outputs": [
            {
                "title": c.get("title"),
                "verdict": c.get("verdict"),
                "why_it_matters": c.get("why_it_matters"),
                "who_cares": c.get("who_cares")
            }
            for c in result_state.get("vetted_candidates", [])
        ],
        "final_briefs": briefs
    }
    if failure_reasons:
        snapshot["failure_reasons"] = failure_reasons
        snapshot["degraded_reasons"] = failure_reasons
    return snapshot

def main():
    start_time = time.time()
    # Compute date string once and reuse across snapshot, gate, and archive
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info("Initializing DailyDiff system environments...")
    init_db()
    init_history_file()

    # Reset health tracker singleton
    health.reset()

    runs_dir = DATA_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    gemini_key = os.getenv("GEMINI_API_KEY")
    mistral_key = os.getenv("MISTRAL_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    is_github_actions = bool(os.getenv("GITHUB_ACTIONS"))
    has_backend_url = bool(os.getenv("BACKEND_API_URL"))

    has_any_key = bool(gemini_key or mistral_key or groq_key)

    briefs = []
    result_state = {}
    min_briefs = int(os.getenv("MIN_BRIEFS", "3"))

    if not has_any_key:
        if is_github_actions or has_backend_url:
            raise RuntimeError(
                "Execution aborted: No LLM API keys (GROQ_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY) found. "
                "Simulation mode is strictly prohibited in CI or connected backend environments."
            )
        logger.warning("No API keys found and running in local dev. Running in SIMULATION mode...")
        briefs = [
            {
                "category": "Career & Learning",
                "title": "Modern React Portfolio Template",
                "description": "**A high-performance, responsive React portfolio template built with Tailwind CSS was launched.**\n\nWhat happened: This open-source template includes built-in SEO optimization, a dark-mode toggle, and a section for GitHub integrations designed to help students stand out.",
                "why_it_matters": "Enables tech students and early-career developers to spin up a professional portfolio in minutes, boosting their job search readiness.",
                "who_cares": "CS students building portfolios, job-seeking software engineers.",
                "verdict": "INTEGRATE",
                "source_url": "https://github.com/learn-to-code/portfolio-template"
            },
            {
                "category": "Cool Tool",
                "title": "HTTPie visual API Client",
                "description": "**HTTPie released a web client focused on learning API request structures.**\n\nWhat happened: It offers an intuitive visual request editor and clean response parsing that makes testing endpoints and learning REST API concepts simple.",
                "why_it_matters": "Provides a zero-setup, highly visual alternative to Postman, making it perfect for beginners learning web development.",
                "who_cares": "React beginners, backend learners, web development students.",
                "verdict": "WATCH",
                "source_url": "https://github.com/httpie/httpie"
            }
        ]
        result_state = {"raw_signals": [], "candidates": [], "researched_candidates": [], "vetted_candidates": [], "final_briefs": briefs}
    else:
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

        try:
            result_state = graph.invoke(initial_state)
            briefs = result_state.get("final_briefs", [])
        except Exception as exc:
            logger.error(f"LangGraph execution exception: {exc}")
            health.mark_fallback("graph", str(exc))
            degraded_path = runs_dir / f"{date_str}.degraded.json"
            snapshot = build_run_snapshot(date_str, {}, [], failure_reasons=[f"Workflow execution exception: {exc}"])
            with open(degraded_path, "w") as f:
                json.dump(snapshot, f, indent=2)
            sys.exit(1)

    elapsed_time = time.time() - start_time
    run_budget = float(os.getenv("RUN_BUDGET_SECONDS", "900"))

    # ==========================================
    # Publication Quality Gate
    # ==========================================
    failure_reasons = []

    # 1. Health hard fallbacks check
    if health.has_fallbacks:
        failure_reasons.append(f"Pipeline marked hard fallbacks: {health.fallbacks}")

    # Build evidence and candidate URLs
    evidence_by_url = {}
    candidate_urls = set()
    for c in result_state.get("researched_candidates", []):
        url = c.get("url")
        if url:
            candidate_urls.add(url)
            evidence_by_url[url] = f"{c.get('description', '')} {(c.get('detailed_content') or '')[:MAX_EVIDENCE_CHARS]}"

    # 2. Per-brief validation and soft filtering
    if briefs:
        surviving_briefs = []
        for b in briefs:
            b_violations = validate_briefs([b], evidence_by_url=evidence_by_url, candidate_urls=candidate_urls)
            if b_violations:
                msg = f"Dropped brief '{b.get('title')}': {'; '.join(b_violations)}"
                logger.warning(f"Gate validation dropped brief: {msg}")
                health.add_degradation("gate", msg)
            else:
                surviving_briefs.append(b)
        briefs = surviving_briefs

    # 3. Brief count check vs MIN_BRIEFS (distinguish genuine quiet day)
    # A genuine quiet day has no hard fallbacks, no LLM errors, and zero briefs because models legitimately returned 0 candidates
    is_genuine_quiet_day = (
        not health.has_fallbacks
        and health.llm_errors_count == 0
        and len(briefs) == 0
        and (
            health.counts.get("skeptic_passed", 0) == 0
            or (health.counts.get("skeptic_passed", 0) > 0 and health.counts.get("verified", 0) == 0)
        )
    )

    if len(briefs) < min_briefs and not is_genuine_quiet_day:
        failure_reasons.append(
            f"Insufficient briefs: produced {len(briefs)} briefs (minimum required: {min_briefs}). "
            f"Not a quiet day (fallbacks={health.fallbacks}, llm_errors={health.llm_errors_count})."
        )

    # 4. Runtime budget check
    if elapsed_time > run_budget:
        failure_reasons.append(f"Execution runtime {elapsed_time:.1f}s exceeded RUN_BUDGET_SECONDS ({run_budget}s).")

    # Handle Gate Verdict
    publish_gate_mode = os.getenv("PUBLISH_GATE", "strict").lower()

    if failure_reasons:
        logger.error(f"[GATE REJECTION] Pipeline produced degraded output for {date_str}!")
        for r in failure_reasons:
            logger.error(f"  - {r}")

        degraded_path = runs_dir / f"{date_str}.degraded.json"
        snapshot = build_run_snapshot(date_str, result_state, briefs, failure_reasons)
        with open(degraded_path, "w") as f:
            json.dump(snapshot, f, indent=2)
        logger.error(f"Saved degraded run snapshot to {degraded_path}")

        if publish_gate_mode == "warn":
            logger.warning("PUBLISH_GATE=warn configured: publishing degraded output anyway despite failures.")
        else:
            logger.error("Failing loud: blocking publication, archive updates, and email dispatch.")
            sys.exit(1)

    # Gate PASSED: Publish output
    logger.info(f"Publication gate passed successfully ({len(briefs)} briefs). Publishing for {date_str}...")

    # Write data/runs/YYYY-MM-DD.json
    run_path = runs_dir / f"{date_str}.json"
    snapshot = build_run_snapshot(date_str, result_state, briefs)
    with open(run_path, "w") as f:
        json.dump(snapshot, f, indent=2)
    logger.info(f"Saved run telemetry snapshot to {run_path}")

    # Append to history.json (skip in simulation mode to avoid polluting history)
    if not has_any_key:
        logger.info("Simulation mode: skipping history, archive, and email dispatch.")
        return

    append_to_history(briefs, date_str)

    # Generate and save Markdown archive
    md_text = build_markdown_brief(briefs, date_str)

    # Hierarchical archive path: YYYY/MM/DD.md using pre-computed date_str
    parts = date_str.split("-")
    year_dir = ARCHIVE_DIR / parts[0]
    month_dir = year_dir / parts[1]
    month_dir.mkdir(parents=True, exist_ok=True)

    day_file_path = month_dir / f"{parts[2]}.md"
    with open(day_file_path, "w") as f:
        f.write(md_text)
    logger.info(f"Saved Markdown archive to {day_file_path}")

    # Also save as latest.md
    latest_md_path = HISTORY_FILE_PATH.parent / "latest.md"
    with open(latest_md_path, "w") as f:
        f.write(md_text)
    logger.info(f"Saved latest brief to {latest_md_path}")

    # Trigger subscription email dispatch via FastAPI webhook if configured
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
                "published_at": datetime.now(timezone.utc).isoformat(),
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
