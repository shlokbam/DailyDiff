# 🚀 DailyDiff — Autonomous Tech Curation Platform

> **We scan the noise. Five things survive.**

**DailyDiff** is an autonomous multi-agent research and editorial curation platform designed for **students and software developers**. 

Instead of overwhelming readers with dense mathematical papers, machine learning theories, or marketing hype, DailyDiff utilizes custom AI agents to scour the web for **developer utility tools, open-source releases (Show HN), self-hosted applications, and framework updates (FastAPI, React, Tailwind)**. It cleans up the jargon into plain English, prepends a bold **TL;DR** to every item, and serves it on a sleek, glassmorphic React timeline.

The system dispatches responsive, personalized briefings to email subscribers every Monday, Wednesday, and Friday morning.

---

## 🛠️ The Architecture & Agentic Workflow

```mermaid
graph TD
    Start([GitHub Actions Scheduler / Mon-Wed-Fri 03:30 UTC]) --> Scout[Scout Agent]
    Scout --> Deduplicate{Skeptic / Deduplication Engine}
    Deduplicate -- Novel Dev Update --> Research[Research Agent]
    Deduplicate -- Duplicate / Math Hype --> Archive[Archive & Drop]
    Research --> Verify[Verifier Agent]
    Verify --> Vet{Claims Valid in README?}
    Vet -- Yes --> Analyze[Analyst Agent]
    Vet -- No / Exaggerated --> Drop[Drop Candidate]
    Analyze --> Editor[Editor Agent]
    Editor --> Publisher[Publisher Agent]
    Publisher --> GitCommit[Commit & Push data/ to Git]
    Publisher --> Notify[Trigger API Notify Webhook]
    Notify --> Send[SMTP / Resend Dispatcher]
    Send --> End([Subscribers' Inboxes])
```

### The Agentic Pipeline (LangGraph)
1. **Scout Agent**: Periodically crawls active feeds:
   * **GitHub Search API**: Fetches popular repositories matching `self-hosted`, `web-development`, `developer-experience`, and `productivity` topics.
   * **Hacker News (YCombinator) API**: Scrapes top stories, prioritizing `Show HN` submissions.
   * **Dev.to Feed**: Scrapes trending frontend and backend programming tutorials.
   * **GitHub Releases API**: Monitors version releases of core dev frameworks (`react`, `next.js`, `fastapi`, `tailwindcss`, `django`, `go`).
2. **Skeptic Agent (Deduplication Node)**: Compares today's raw findings against titles/descriptions inside `data/history.json` to filter out duplicate updates or hype.
3. **Research Agent**: Crawls target URL codebases, documentation, or release notes to pull raw descriptions and README summaries.
4. **Verifier Agent**: Fact-checks claims against the raw documentation to ensure they are fully supported.
5. **Analyst Agent**: Evaluates the update's direct utility for developers, generating `Why It Matters`, `Who Cares`, confidence levels, and actionable verdicts (`WATCH`, `INTEGRATE`, `READ`).
6. **Editor Agent**: Curation engine that selects the top $\le 5$ developments and maps them to briefing categories. It trims jargon (using **ELI5** rules) and prepends a bold, 1-sentence **TL;DR** to the summary.
7. **Publisher Agent**: Saves JSON and Markdown briefs in chronological directories and pushes them back to GitHub.

---

## 💻 Tech Stack & Infrastructure

* **Backend Engine**: Python 3.12, LangGraph, LangChain, FastAPI, Uvicorn, PostgreSQL (Neon Pooler) / SQLite.
* **Primary AI Engine**: Mistral AI (`open-mixtral-8x22b` / `mistral-small-latest`) as the primary generator to avoid tight RPM constraints, with Google Gemini (`gemini-3.5-flash`) as the automatic fail-safe fallback.
* **Frontend Client**: Vite + React, Vanilla CSS with custom glassmorphism tokens.
* **Deployment & Scheduling**:
  * **Backend App**: Hosted on Render.
  * **Frontend Client**: Hosted on Vercel.
  * **Orchestration Runner**: Scheduled via GitHub Actions (`.github/workflows/thrice_weekly_brief.yml`) running at **03:30 UTC** (Mon, Wed, Fri).
  * **Database Layer**: SQLite locally (`subscribers.db`); shifts automatically to **Neon Cloud Postgres** when `DATABASE_URL` is set in production.

---

## 📂 Project Structure

```text
DailyDiff/
├── .github/
│   └── workflows/
│       └── thrice_weekly_brief.yml # Cron Scheduler (Mon, Wed, Fri at 03:30 UTC)
├── backend/                     # Python FastAPI & LangGraph Engine
│   ├── app/
│   │   ├── agents/              # LangGraph Agent nodes & states
│   │   │   ├── models.py        # Mistral-to-Gemini Fallback Wrapper
│   │   │   ├── scout.py         # HN, Dev.to, GitHub scraper routines
│   │   │   ├── skeptic.py       # Hype filter & deduplication
│   │   │   ├── verifier.py      # Technical assertions fact-checker
│   │   │   ├── analyst.py       # Developer impact analyst
│   │   │   └── editor.py        # ELI5 & TL;DR editor
│   │   ├── config.py            # Environment configurations
│   │   ├── database.py          # Dynamic SQLite / PostgreSQL switcher
│   │   ├── email_dispatcher.py  # Gmail SMTP & Resend HTML mailer
│   │   ├── main.py              # FastAPI Web routes
│   │   └── schemas.py           # Pydantic validation structures
│   ├── requirements.txt         # Package dependencies
│   ├── run_agent.py             # Agent pipeline runner script
│   └── test_api.py              # Backend endpoint tests
├── frontend/                    # Vite + React Client Dashboard
│   ├── src/
│   │   ├── App.jsx              # Timeline dashboard UI
│   │   ├── index.css            # Custom CSS Glassmorphic design tokens
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── data/                        # Git-Based CMS Database
│   ├── history.json             # Combined archive of historical briefings
│   ├── latest.md                # Latest compiled markdown report
│   └── archive/                 # Chronological YYYY/MM/DD.md briefings
└── .python-version              # Production Python environment pin (3.12)
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites Setup

Create a `.env` file in the root directory:
```env
# AI Models Keys
MISTRAL_API_KEY=your_mistral_key_here
GEMINI_API_KEY=your_gemini_studio_key_here

# Neon Database (Leave empty to default to local subscribers.db SQLite)
DATABASE_URL=postgresql://neondb_owner:password@ep-host-pooler.aws.neon.tech/neondb?sslmode=require

# Email dispatch (Brevo API primary or Google SMTP fallback settings)
BREVO_API_KEY=your_brevo_api_key_here
SMTP_EMAIL=yourname@gmail.com
SMTP_PASSWORD=16_character_google_app_password

# Authentication Webhook token (For GHA runner to verify endpoints)
NOTIFY_SECRET_TOKEN=generate_any_secure_string_here
BACKEND_API_URL=http://localhost:8000
```

> [!TIP]
> **Brevo API Key (Recommended for Render)**: Sign up at **[Brevo.com](https://www.brevo.com)**, go to **SMTP & API** on your dashboard, generate a free API key, and paste it into `BREVO_API_KEY`.
>
> **Google App Password**: In your Google Account settings, search for **App Passwords** under Security. Create an app named `DailyDiff` and copy the 16-character code into `SMTP_PASSWORD` (make sure 2FA is active on your Gmail).

---

### 2. Boot up the Backend

First, build your virtual environment and install dependencies:
```bash
# Create and activate environment
uv venv --python 3.12
source .venv/bin/activate

# Install dependencies
uv pip install -r backend/requirements.txt
```

Launch the FastAPI web service:
```bash
export PYTHONPATH=backend
uvicorn app.main:app --port 8000 --reload
```
The server will start at `http://localhost:8000`. You can inspect APIs at `/docs`.

---

### 3. Run the Agent Pipeline

To run the agent workflow and compile today's briefing locally:
```bash
export PYTHONPATH=backend
source .venv/bin/activate
python backend/run_agent.py
```
*(If no API keys are configured, the pipeline automatically falls back to **Simulation Mode** and creates simulated briefs to test folders, database commits, and SMTP emails).*

---

### 4. Start the React Client

Navigate into the frontend folder, install npm packages, and start the development server:
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

## 📬 Subscription & Unsubscription Flow

* **Subscription Flow**:
  1. **Register**: Users submit their emails on the Vercel dashboard.
  2. **Persistence**: The FastAPI server saves it dynamically in the SQLite database (local dev) or **Neon cloud Postgres** (production).
  3. **Trigger**: After compiling briefs, `run_agent.py` triggers the secure endpoint `POST /api/notify-subscribers` (signed with the header `X-Auth-Token` matching your secret token).
  4. **Mailing**: The backend compiles a responsive HTML newsletter template featuring the **TL;DR** lists and sends it using Google SMTP (with a fallback to **Resend API**).

* **Unsubscription Flow**:
  1. **Link Trigger**: Users click the "Unsubscribe" link at the footer of the HTML email template.
  2. **API Endpoint**: The request routes to `POST /api/unsubscribe` on the FastAPI server, removing their record from the active subscribers database.
  3. **Polite Email Confirmation**: The server immediately dispatches a polite confirmation email matching the brand's dark-mode glassmorphic theme to reassure the user they have been removed.

---

## 🧪 Testing the API

We write standard Pytest-compatible tests using `unittest`. Run the test suite:
```bash
export PYTHONPATH=backend
source .venv/bin/activate
python -m unittest backend/test_api.py
```
