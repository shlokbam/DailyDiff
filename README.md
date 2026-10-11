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
2. **Skeptic Agent (Deduplication Node)**: Performs algorithmic URL deduplication against `data/history.json` and evaluates raw findings with LLM hype filtering to drop duplicate topics or non-technical noise.
3. **Research Agent**: Crawls target URL codebases, documentation, or release notes to pull raw descriptions and README summaries.
4. **Verifier Agent**: Fact-checks claims against the raw documentation to ensure they are fully supported.
5. **Analyst Agent**: Evaluates the update's direct utility for developers, generating `Why It Matters`, `Who Cares`, confidence levels, and actionable verdicts (`WATCH`, `INTEGRATE`, `READ`).
6. **Editor Agent**: Curation engine that selects the top $\le 5$ developments and maps them to briefing categories. It trims jargon (using **ELI5** rules) and prepends a bold, 1-sentence **TL;DR** to the summary.
7. **Publisher Agent**: Saves JSON and Markdown briefs in chronological directories and pushes them back to GitHub.

---

## 💻 Tech Stack & Infrastructure

* **Backend Engine**: Python 3.12, LangGraph, LangChain, FastAPI, Uvicorn, PostgreSQL (Neon Pooler) / SQLite.
* **Primary AI Engine**: Mistral AI (`open-mixtral-8x22b` / `mistral-small-latest`) as the primary generator to avoid tight RPM constraints, with Google Gemini (`gemini-3.5-flash`) as the automatic fail-safe fallback.
* **Frontend Client**: Vite + React, Vanilla CSS with custom glassmorphism tokens — deployed live at **[https://dailydiff.in](https://dailydiff.in)**.
* **Deployment & Scheduling**:
  * **Domain**: Custom domain `dailydiff.in` connected via Vercel DNS.
  * **Backend App**: Hosted on Render.
  * **Email Dispatcher**: Authenticated Brevo API sending from `briefs@dailydiff.in` (with SMTP & Resend fallbacks).
  * **Orchestration Runner**: Scheduled via GitHub Actions (`.github/workflows/thrice_weekly_brief.yml`) running at **03:30 UTC** (Mon, Wed, Fri), credited directly to maintainer GitHub contributions.
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
├── tests/                       # Evaluation & Benchmark Test Suites
│   ├── conftest.py              # Pytest session hooks & DB persistence
│   └── evals/                   # Node-by-Node Evals & DeepEval Suite
│       ├── golden_dataset.json  # 25 curated test cases across 6 archetypes
│       ├── deepeval_judge.py    # Custom DeepEvalBaseLLM judge
│       ├── deepeval_metrics.py  # G-Eval metrics (SingleTurnParams)
│       ├── deepeval_adapter.py  # LLMTestCase adapter
│       ├── test_deepeval_nodes.py # Official DeepEval Pytest test runner
│       ├── eval_skeptic.py      # Skeptic node evaluation
│       ├── eval_verifier.py     # Verifier anti-hallucination evaluation
│       ├── eval_analyst.py      # Analyst utility evaluation
│       ├── eval_editor.py       # Editor curation & formatting evaluation
│       └── run_all_evals.py     # Comprehensive orchestrator runner
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

# Email dispatch (Brevo API primary sending from custom domain)
BREVO_API_KEY=your_brevo_api_key_here
SMTP_EMAIL=briefs@dailydiff.in
SMTP_PASSWORD=your_smtp_password_optional

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

---

## 📊 LLM Agent Evaluation Framework & DeepEval Suite

DailyDiff features a production-grade LLM evaluation framework built with **DeepEval**, **G-Eval (LLM-as-a-Judge)**, and custom heuristic metrics to benchmark every pipeline node before shipping to subscribers.

### 1. The Golden Dataset (`tests/evals/golden_dataset.json`)
A benchmark dataset of **25 hand-crafted test cases** covering realistic developer updates across 6 key archetypes:
* **`positive_student_utility`** (10 cases): High-utility tools and libraries (e.g., *Diagrams as Code*, *Open WebUI*, *Immich*, *Coolify*, *Hoppscotch*).
* **`positive_developer_framework`** (1 case): Core web tooling releases (*TanStack Router*).
* **`positive_edge_tutorial`** (1 case): Actionable developer deep dives (*Coding Agent fix loops*).
* **`negative_enterprise_fluff`** (4 cases): Abstract research, academic theory, or enterprise press releases (*Oracle M&A*, *Raft leases*).
* **`negative_duplicate_release`** (3 cases): Patch releases with URLs matching `data/history.json` to verify zero duplicate coverage.
* **`negative_adversarial_fake`** (3 cases): Unsupported marketing hype, fabricated claims, and empty repos (*QuantumPy*, *AutoDev*, *ZeroCostDB*).

Each case provides strict multi-node ground truth:
```json
{
  "id": "eval_case_001",
  "category_target": "Cool Tool",
  "archetype": "positive_student_utility",
  "input_signal": { ... },
  "ground_truth": {
    "skeptic": { "expected_decision": "KEEP", "is_student_relevant": true },
    "verifier": { "expected_status": "VALID", "are_claims_supported": true },
    "analyst": { "expected_verdict": "INTEGRATE", "expected_audience_keywords": [...] },
    "editor": { "expected_category": "Cool Tool", "must_prepend_bold_summary": true }
  }
}
```

---

### 2. Node-by-Node Evaluation Architecture

| Node | Evaluator Script | Core Metrics Measured | Target Threshold |
| :--- | :--- | :--- | :--- |
| **Skeptic** | `tests/evals/eval_skeptic.py` | Accuracy, Precision, Recall, F1 Score, History Deduplication Rate | $\ge 90\%$ Precision, $100\%$ Dedup |
| **Verifier** | `tests/evals/eval_verifier.py` | Adversarial Hype Catch Rate, False Rejection Rate, Groundedness | $100\%$ Catch Rate, $< 5\%$ False Rejection |
| **Analyst** | `tests/evals/eval_analyst.py` | Verdict Accuracy, Audience Specificity Rate, Practicality Score (1-5) | $\ge 90\%$ Verdict Match, $> 3.5 / 5$ Practicality |
| **Editor** | `tests/evals/eval_editor.py` | Bold Lead Compliance, Forbidden Label Defense (No "TL;DR:"), Category Diversity, Readability (1-5) | $100\%$ Format Compliance, $> 80\%$ Diversity |

---

### 3. DeepEval & G-Eval CI/CD Integration (`tests/evals/test_deepeval_nodes.py`)
Implemented using the official **DeepEval** testing pattern:
* **`LLMTestCase` Data Contracts**: Maps inputs, actual LLM outputs, expected benchmark targets, and scraped documentation contexts (`retrieval_context`).
* **G-Eval Metrics (`SingleTurnParams`)**: Multi-step evaluation criteria with LLM-as-a-Judge scoring (0.0 to 1.0) and explainable chain-of-thought reasoning:
  * `Skeptic Candidate Relevance [GEval]` (threshold: 0.70)
  * `Verifier Technical Groundedness [GEval]` (threshold: 0.70)
  * `Analyst Practical Takeaway & Audience [GEval]` (threshold: 0.70)
  * `Editor ELI5 Readability & Tone [GEval]` (threshold: 0.70)
* **Pytest CI Assertions**: Uses `assert_test(test_case, [metric])` for native terminal and GitHub Actions integration.

```bash
# Run the official DeepEval CI test suite
FAST_EVAL=1 .venv/bin/deepeval test run tests/evals/test_deepeval_nodes.py
```

---

### 4. Database Persistence & Run History
Every evaluation execution (whether single node or full suite) automatically saves into the database (`eval_runs` table in Neon Cloud Postgres / SQLite):
* **FastAPI Endpoints**:
  * `GET /api/evals/history`: Returns chronological history of benchmark runs.
  * `GET /api/evals/latest`: Fetches the latest evaluation scorecard.
  * `GET /api/evals/{run_id}`: Inspects exact test cases, outputs, and reasoning from any past run.
* **Persistent Schema**:
  * `run_type`: `full_suite`, `deepeval_ci`, `skeptic`, `verifier`, `analyst`, `editor`
  * `composite_score`, `total_cases`, `pass_rate`, `summary_json`, `raw_report_json`, `created_at`

---

### 5. Interactive Frontend Dashboard
DailyDiff includes a dedicated **Evaluations Dashboard** at `http://localhost:5173`:
* **Database Run Selector**: Switch between past runs directly from a dropdown to compare prompt versions or model releases.
* **Filterable Case Browser**: Filter benchmark items by `All`, `Passed`, or `Failed/Flagged`.
* **DeepEval LLMTestCase Inspector**: Inspect raw JSON payloads (`input`, `actual_output`, `expected_output`, `context`) for each test case.
* **Clean Dark Glassmorphic Design**: Typography and SVG badge indicators with zero emojis.

---

### 6. Running Evaluations Locally

```bash
# Run individual node evaluations
FAST_EVAL=1 python tests/evals/eval_skeptic.py
FAST_EVAL=1 python tests/evals/eval_verifier.py
FAST_EVAL=1 python tests/evals/eval_analyst.py
FAST_EVAL=1 python tests/evals/eval_editor.py

# Run the complete orchestrated evaluation suite (persists to DB & syncs frontend)
FAST_EVAL=1 python tests/evals/run_all_evals.py

# Run DeepEval CI/CD test runner
FAST_EVAL=1 deepeval test run tests/evals/test_deepeval_nodes.py
```
*(Set `FAST_EVAL=1` to run in sub-second benchmark evaluation mode; omit to run against live model APIs).*

