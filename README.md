# DailyDiff ⚡

> **We scan the noise. Five things survive.**  
> An autonomous multi-agent tech intelligence pipeline built with **LangGraph**, **FastAPI**, and **React**. Designed for computer science students and early-career software engineers: it turns developer chatter into up to five fact-checked briefs every Monday, Wednesday, and Friday.

🌐 **Live Deployment:** [https://dailydiff.in](https://dailydiff.in)

[![Live Website](https://img.shields.io/badge/Live_Site-dailydiff.in-00E5FF?style=flat&logo=vercel&logoColor=white)](https://dailydiff.in)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-teal.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/frontend-React%2019%20%2B%20Vite-61dafb.svg)](https://vitejs.dev/)
[![LLM Chain](https://img.shields.io/badge/LLM-Groq%20gpt--oss%20%E2%86%92%20Mistral-blueviolet.svg)](https://groq.com/)
[![Tests](https://img.shields.io/badge/tests-75%20passed-brightgreen.svg)](tests/)

---

## 🌟 Why DailyDiff?

Developer feeds are saturated with corporate PR announcements, repetitive framework patch notes, and speculative academic research. **DailyDiff** automates the editorial triage:

1. **Scrapes raw ecosystem signals** from GitHub search, GitHub releases (React, Next.js, FastAPI, Tailwind CSS, Go), Hacker News, Dev.to, freeCodeCamp, Product Hunt, and Reddit `/r/webdev`.
2. **Filters out enterprise fluff & repeats** by deduplicating against every previously published URL, then asking an LLM to keep only items that are new, substantial, and useful.
3. **Scrapes source documentation** (GitHub READMEs or page text, capped at 1,800 characters) to ground every claim.
4. **Fact-checks, analyzes, and writes** in one batched LLM call per stage, using a Groq → Mistral fallback chain.
5. **Enforces a fail-closed publish gate**: if an agent fails or too few briefs pass the rule checks, nothing is published and no email is sent.
6. **Empirically evaluated** with live LLM calls, Wilson confidence intervals, planted hallucination traps, and prompt-injection cases.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    %% Subgraph 1: Signal Ingestion
    subgraph Sources["🌐 1. Raw Developer Ecosystem Sources"]
        direction TB
        S1["🐙 GitHub Search & Releases"]
        S2["📰 Hacker News (Top 15)"]
        S3["💻 Dev.to & freeCodeCamp RSS"]
        S4["🚀 Product Hunt & Reddit /r/webdev"]
    end

    %% Subgraph 2: Multi-Agent Intelligence Core
    subgraph Pipeline["🧠 2. LangGraph Multi-Agent Pipeline (linear)"]
        direction TB
        N1["🔍 Node 1: Scout<br/>Sequential HTTP fetches (~60 raw signals)"]
        N2["🛡️ Node 2: Skeptic (1 LLM call)<br/>URL dedup vs history + relevance filter (≤ 10 candidates)"]
        N3["📚 Node 3: Researcher<br/>README / page scraper (≤ 1,800 chars)"]

        subgraph LLMLayer["⚡ Provider Fallback Chain (30s timeout each)"]
            LLM1["Groq openai/gpt-oss-120b"]
            LLM2["Groq qwen/qwen3.8-27b"]
            LLM3["Groq openai/gpt-oss-20b"]
            LLM4["Mistral mistral-small-latest"]
            LLM1 -.->|on error| LLM2 -.->|on error| LLM3 -.->|on error| LLM4
        end

        N4["🔬 Node 4: Verifier (1 batched call)<br/>Checks claims against scraped evidence"]
        N5["📊 Node 5: Analyst (1 batched call)<br/>why_it_matters, who_cares, verdict (WATCH / INTEGRATE / READ)"]
        N6["✍️ Node 6: Editor (1 batched call)<br/>Up to 5 briefs, one per category, bold lead sentence"]

        N1 --> N2
        N2 --> N3
        N3 --> N4
        N4 --> N5
        N5 --> N6

        LLMLayer -.->|Inference| N2
        LLMLayer -.->|Inference| N4
        LLMLayer -.->|Inference| N5
        LLMLayer -.->|Inference| N6
    end

    %% Subgraph 3: Fail-Closed Publish Gate
    subgraph GateSection["🛡️ 3. Fail-Closed Publish Gate (run_agent.py)"]
        direction TB
        QG{"Publish Gate"}
        Inv["Per-brief rule checks (checks.py):<br/>• Required fields, valid category & verdict<br/>• Bold lead sentence, no TL;DR label<br/>• HTTPS source URL that was a candidate<br/>• No generic filler text<br/>• Every number found in the evidence<br/>Run level: no node failures, ≥ 3 briefs survive"]
        QG --- Inv
    end

    %% Subgraph 4: Publication & Delivery
    subgraph Delivery["🚀 4. Publication & Delivery"]
        direction TB
        D_Git["🗂️ data/history.json + data/archive/ (committed by CI)"]
        D_UI["💻 React 19 + Vite site (dailydiff.in)<br/>Static history cache + live API merge"]
        D_Email["📬 FastAPI /api/notify-subscribers<br/>Brevo → Gmail SMTP → Resend"]
    end

    %% Subgraph 5: Safety
    subgraph Safety["🛑 Blocked Run"]
        FailNode["⚠️ Publication Blocked<br/>data/runs/YYYY-MM-DD.degraded.json<br/>Exit code 1 • No emails"]
    end

    %% Connections
    Sources --> N1
    N6 --> QG
    QG ==>|✅ PASS| D_Git
    QG ==>|✅ PASS| D_Email
    D_Git --> D_UI
    QG -->|❌ FAIL| FailNode

    %% Styling
    classDef sourceStyle fill:#1e293b,stroke:#475569,stroke-width:1px,color:#f8fafc;
    classDef agentStyle fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef llmStyle fill:#1e1b4b,stroke:#818cf8,stroke-width:1px,color:#e0e7ff;
    classDef gateStyle fill:#1e293b,stroke:#f59e0b,stroke-width:2px,color:#fef3c7;
    classDef passStyle fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#ecfdf5;
    classDef failStyle fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fef2f2;

    class S1,S2,S3,S4 sourceStyle;
    class N1,N2,N3,N4,N5,N6 agentStyle;
    class LLM1,LLM2,LLM3,LLM4 llmStyle;
    class QG,Inv gateStyle;
    class D_Git,D_UI,D_Email passStyle;
    class FailNode failStyle;
```

### Pipeline Nodes

| Stage | Node | File | Responsibility |
|:---|:---|:---|:---|
| **1** | **Scout** | [`backend/app/agents/scout.py`](backend/app/agents/scout.py) | 5 GitHub repository searches (recently pushed, mostly created in the last 45 days), latest releases of 5 tracked repos, HN top 15, and RSS/Atom feeds. Look-back window is 2 days (3 on Mondays). |
| **2** | **Skeptic** | [`backend/app/agents/skeptic.py`](backend/app/agents/skeptic.py) | Drops any URL already in `data/history.json`, keeps the first 45 signals (descriptions cut to 200 chars), shows the model the last 7 editions' titles, and asks for the IDs to keep. Caps output at 10 candidates. |
| **3** | **Researcher** | [`backend/app/agents/researcher.py`](backend/app/agents/researcher.py) | GitHub: raw `README.md` from `main`/`master`, falling back to repo metadata. Other links: visible page text via BeautifulSoup. Capped at `MAX_EVIDENCE_CHARS = 1800`. Records the content source per URL. |
| **4** | **Verifier** | [`backend/app/agents/verifier.py`](backend/app/agents/verifier.py) | Drops candidates with no usable evidence (`empty`, `description_only`, `api_fallback`; releases are exempt), then **1 batched call** marks each VALID / INVALID. Only VALID items continue. |
| **5** | **Analyst** | [`backend/app/agents/analyst.py`](backend/app/agents/analyst.py) | **1 batched call** adds `why_it_matters`, `who_cares`, and a verdict (`WATCH`, `INTEGRATE`, `READ`). Items with missing or invalid output are dropped with a warning. |
| **6** | **Editor** | [`backend/app/agents/editor.py`](backend/app/agents/editor.py) | **1 batched call** selects up to 5 items, one per category (`Tech Shift`, `Cool Tool`, `Career & Learning`, `Ecosystem Update`, `Watchlist`), and writes a bold lead sentence. |
| **Gate** | **Publish Gate** | [`backend/run_agent.py`](backend/run_agent.py) | Runs the rule checks from [`backend/app/checks.py`](backend/app/checks.py) on each brief, drops failures and duplicate categories, then publishes or blocks. |

---

## 🛡️ Reliability & Fault-Tolerance Principles

- **Fail-closed nodes**: every LLM node catches its own failure, records it in [`run_health.py`](backend/app/run_health.py), and returns an empty list. Any recorded failure blocks publication.
- **Retries**: API errors (429, 413, timeouts) are not retried by the app. The provider chain moves on to the next model instead. Malformed JSON or a wrong output shape is retried **exactly once** with a "return only valid JSON" reminder ([`models.py`](backend/app/agents/models.py)).
- **Provider fallback chain**: Groq `openai/gpt-oss-120b` → `qwen/qwen3.8-27b` → `openai/gpt-oss-20b` → Mistral `mistral-small-latest`. Each model has a 30s timeout, and SDK retries are off. The primary Groq model and the Mistral model can be overridden with `GROQ_MODEL` / `MISTRAL_MODEL`.
- **Free-tier pacing**: to stay under Groq's 8,000 tokens-per-minute limit, the pipeline sleeps **35s before Verifier, 30s before Analyst, and 50s before Editor**. Set `SKIP_PIPELINE_PAUSE=1` to disable (pauses are skipped automatically under pytest).
- **Four LLM calls per run**: Skeptic, Verifier, Analyst, and Editor make one call each, plus a retry if the JSON was malformed.
- **Prompt-injection hardening**: scraped text is wrapped in tags the model is told to treat as data. HTML comments are stripped and `<` / `>` are escaped (`escape_untrusted`).
- **Publish gate rules** (per brief, [`checks.py`](backend/app/checks.py)):
  1. All required fields present: category, title, description, why_it_matters, who_cares, verdict, source_url.
  2. Category is one of the 5 designated categories; verdict is `WATCH`, `INTEGRATE`, or `READ`.
  3. Description starts with a bold sentence (`**...**`) and contains no `TL;DR:` / `TLDR:` label.
  4. Source URL is HTTPS and matches a researched candidate (ignoring `utm_*` params and trailing slashes).
  5. No generic filler text.
  6. Every version, multiplier (`10x`), percentage, `k/m/b` count, or `N+` figure in the title, description, or why_it_matters appears in the source evidence (title + description + scraped text).
- **Run-level decision**: briefs that fail are dropped, duplicate categories are removed, and at most 5 are kept. Publication is **blocked** (degraded snapshot, exit code 1) if any node failed, if every brief was dropped, or if fewer than `MIN_BRIEFS` (default 3) survive. If the pipeline produced nothing *and* nothing errored, the run is treated as a quiet day and an empty edition is recorded.
- **Same-day retries**: the workflow runs at 09:00 IST, then again at 11:00 and 13:00 IST. Each run first checks whether today's edition is already published, and stops if it is (or only resends a pending email). Progress is saved per step in `data/runs/state/YYYY-MM-DD.json`, so a retry continues where the last run stopped:

  | What happened | Next run starts at |
  |:---|:---|
  | API or bad-JSON error in a step | That step (finished steps are reused) |
  | Verifier approved fewer than `MIN_BRIEFS` items | Scout, with today's rejected URLs skipped by the Skeptic |
  | Analyst kept fewer than `MIN_BRIEFS` items | Analyst |
  | Gate kept fewer than `MIN_BRIEFS` briefs | Editor |

  On a restart, a Verifier that finds nothing new counts as a failure, not a quiet day. If the 13:00 run also fails, no edition is sent that day.
- **Email delivery**: before notifying subscribers, the runner wakes the backend (`GET /api/status` every 10s, for up to 120s, to cover Render's cold start). Only HTTP 200 from `/api/notify-subscribers` counts as sent. Otherwise the email stays `pending` in the state file, the run exits 1, and the next retry resends it without re-running the pipeline. "Sent" means the backend accepted the request; delivery failures inside the backend (Brevo/SMTP) are not visible to the pipeline.
- **Audit snapshots**: every run writes `data/runs/YYYY-MM-DD.json` (or `.degraded.json`) with stage counts, content sources, models used, LLM call count, node durations, hard failures, warnings, and the final briefs. CI commits `data/` even when the run fails.

---

## 📊 Live Evaluation Harness & Results

The evaluation harness in [`tests/evals/`](tests/evals/) makes **live LLM calls** against two hand-built datasets. Rates come with Wilson score 95% confidence intervals.

- [`golden_dataset.json`](tests/evals/golden_dataset.json): 25 cases (18 expected KEEP, 7 expected REJECT), 15 of them with an expected Analyst verdict.
- [`planted_errors.json`](tests/evals/planted_errors.json): 13 traps (2 exaggerations, 2 wrong numbers, 2 unsupported features, 2 empty-evidence cases, 5 prompt injections).
- G-Eval Usefulness and Faithfulness scores come from an uncalibrated LLM judge ([`judge.py`](tests/evals/judge.py)) that uses the same provider chain.

### Latest Recorded Run

> [!IMPORTANT]
> The stored results ([`tests/evals/results/latest.json`](tests/evals/results/latest.json)) were recorded on **2026-10-15**. That is before the Groq model switch (Oct 19) and the Skeptic/Researcher token budgets (Oct 21), so they do not reflect the current configuration.

```text
================================================================================
Node         | Metric                         | Count & Rate
--------------------------------------------------------------------------------
Skeptic      | Accuracy                       | 16/25 = 64% (CI: roughly 45–80%)
Skeptic      | Always-KEEP Baseline           | 18/25 = 72% (CI: roughly 52–86%)
Skeptic      | Precision                      | 10/11 = 91% (CI: roughly 62–98%)
Skeptic      | Recall                         | 10/18 = 56% (CI: roughly 34–75%)
Skeptic      | Scope Drift Filtered           | 6/7 = 86%   (CI: roughly 49–97%)
Verifier     | Bad Items Caught               | 14/16 = 88% (CI: roughly 64–97%)
Verifier     | Good Items Wrongly Rejected    | 5/22 = 23%  (CI: roughly 10–43%)
Verifier     | Prompt Injections Succeeded    | 2/5 = 40%
Analyst      | Verdict Match (Ref-based)      | 13/15 = 87% (CI: roughly 62–96%)
Analyst      | G-Eval Usefulness Avg          | 0.49 / 1.0  (>= 0.7: 3/14 = 21%)
Editor       | Rule Checks Passed             | 5/5 briefs on every rule
Editor       | G-Eval Faithfulness Avg        | 0.96 / 1.0
Pipeline     | Briefs Produced                | 0 of 12 frozen inputs
Pipeline     | Bad Items Leaked               | 0/6
Pipeline     | Gate Decision                  | WOULD PUBLISH (quiet-day path, 0 briefs)
Pipeline     | Total Duration                 | 4.16s (Skeptic + Verifier only)
================================================================================
```

> [!NOTE]
> In that run the end-to-end pipeline eval produced **no briefs**: the Verifier passed none of the Skeptic's picks, so Analyst and Editor never ran. "0/6 leaked" and "WOULD PUBLISH" are therefore trivially true for that run. The Editor numbers come from the separate Editor eval, which feeds 5 known-good golden cases through the real Analyst and Editor.

### Prompt Engineering Progression

Taken from the stored runs [`before_prompts.json`](tests/evals/results/before_prompts.json), [`after_prompts.json`](tests/evals/results/after_prompts.json), and [`latest.json`](tests/evals/results/latest.json):

| Metric | Baseline (Oct 14) | Prompts Restored (Oct 15) | Latest (Oct 15) |
|:---|:---|:---|:---|
| **Skeptic Precision** | 76% (13/17) | 100% (14/14) | **91% (10/11)** |
| **Skeptic Scope Drift Filtered** | 43% (3/7) | 100% (7/7) | **86% (6/7)** |
| **Verifier Bad Claims Caught** | 94% (15/16) | 94% (15/16) | **88% (14/16)** |
| **Verifier Prompt Injections Succeeded** | 1/5 | 1/5 | **2/5** |
| **Analyst Verdict Match** | 93% (14/15) | 87% (13/15) | **87% (13/15)** |
| **Editor Numeric Grounding** | 60% (3/5) | 60% (3/5) | **100% (5/5)** |
| **Editor G-Eval Faithfulness** | 0.54 | 0.64 | **0.96** |
| **Pipeline Gate Decision** | `BLOCKED` (5 briefs) | `BLOCKED` (4 briefs) | `WOULD PUBLISH` (0 briefs) |

> [!NOTE]
> **Why honest metrics matter:** real open-weights models make mistakes. An evaluation suite claiming "100% pass rates" on prompt injections and fact-checking suggests simulated or seeded data. [`tests/test_no_fake_results.py`](tests/test_no_fake_results.py) fails the build if simulation patterns appear in the repo.

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- A free API key from [Groq Console](https://console.groq.com/) and/or [Mistral AI](https://console.mistral.ai/). At least one is required.

### 2. Installation

```bash
git clone https://github.com/shlokbam/DailyDiff.git
cd DailyDiff

# Set up Python virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install backend dependencies (pytest is installed separately)
pip install -r backend/requirements.txt pytest

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 3. Environment Configuration

Create a `.env` file in the project root (loaded by [`backend/app/config.py`](backend/app/config.py)):

```env
# LLM providers: at least one key is required (chain: Groq models -> Mistral)
GROQ_API_KEY=gsk_your_groq_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
# Optional model overrides
# GROQ_MODEL=openai/gpt-oss-120b
# MISTRAL_MODEL=mistral-small-latest

# Optional: raises GitHub API rate limits for Scout and Researcher
GITHUB_TOKEN=your_github_token

# Subscriber database: leave UNSET to use local SQLite (backend/subscribers.db).
# When set, it must be a PostgreSQL connection string (e.g. Neon).
# DATABASE_URL=postgresql://user:password@host/dbname

# Subscriber notification (run_agent.py -> FastAPI)
BACKEND_API_URL=http://localhost:8000
NOTIFY_SECRET_TOKEN=your_secure_secret_token

# Optional: email delivery, tried in this order: Brevo -> Gmail SMTP -> Resend.
# If none succeeds, the email HTML is written to logs/.
BREVO_API_KEY=your_brevo_api_key
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
RESEND_API_KEY=your_resend_api_key

# Optional: pipeline tuning
# MIN_BRIEFS=3
# SKIP_PIPELINE_PAUSE=1

# Optional: LangSmith tracing
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your_langsmith_key
# LANGCHAIN_PROJECT=DailyDiff
```

### 4. Running Offline Unit Tests

75 offline tests cover the rule checks, the publish gate, retry & resume, email retry, fail-closed node behavior, JSON retry logic, prompt escaping, feed parsing, API auth, and the anti-simulation guard. No live API calls are made:

```bash
PYTHONPATH=backend pytest tests -m "not live" -q
```

### 5. Running the Pipeline Locally

```bash
PYTHONPATH=backend python backend/run_agent.py
```

This writes to `data/` (run snapshot, `history.json`, archive markdown). It notifies subscribers only if `BACKEND_API_URL` is set and the gate passes.

### 6. Running the Live Evaluation Benchmark

```bash
python tests/evals/run_evals.py
```

Run it from the repository root. Results are written to `tests/evals/results/run_<timestamp>.json` and `latest.json`, and mirrored, together with both datasets, into `frontend/public/`. The run exits with code 1 if any case errored, which is likely on Groq's free tier because of rate limits.

### 7. Starting the Web Application

> 🚀 **Production**: the frontend is live at **[https://dailydiff.in](https://dailydiff.in)**, backed by the API at `https://dailydiff.onrender.com`.

**Backend API (FastAPI):**
```bash
export PYTHONPATH=backend
uvicorn app.main:app --reload --port 8000
```

| Method | Endpoint | Purpose |
|:---|:---|:---|
| `GET`/`HEAD` | `/api/status` | Health check |
| `POST` | `/api/subscribe` | Add a subscriber (`{"email": ...}`) |
| `POST` | `/api/unsubscribe` | Remove a subscriber and send a confirmation email |
| `GET` | `/api/unsubscribe?email=...` | Unsubscribe via link (returns an HTML page) |
| `GET`/`HEAD` | `/api/briefs/latest` | Most recent edition |
| `GET` | `/api/briefs/archive?page=1&limit=10` | Editions, newest first |
| `GET` | `/api/briefs/{YYYY-MM-DD}` | Edition for a date |
| `POST` | `/api/notify-subscribers` | Email all subscribers (requires `X-Auth-Token: $NOTIFY_SECRET_TOKEN`) |

Editions are read from `data/history.json`; the database stores subscribers only.

**Frontend (React + Vite):**
```bash
cd frontend
npm run dev
```
Open **`http://localhost:5173/`**. On `localhost` the app calls `http://localhost:8000/api`; elsewhere it calls the Render backend. It first renders from the static `frontend/public/data/history.json`, then merges in editions from the live API. The **How It's Made** tab explains the architecture, and the **Evaluations** tab shows the scorecard and case inspectors from `frontend/public/eval_results.json`.

---

## ⚙️ CI/CD

| Workflow | Trigger | What it does |
|:---|:---|:---|
| [`thrice_weekly_brief.yml`](.github/workflows/thrice_weekly_brief.yml) | Cron `30 3`, `30 5`, `30 7 * * 1,3,5` (09:00, 11:00, 13:00 IST, Mon/Wed/Fri) and manual dispatch | Installs deps with `uv`, runs `backend/run_agent.py`, then commits and pushes any changes under `data/` (including the day's state file), even when the run is blocked. The two later runs exit immediately once the day is done. |
| [`evals.yml`](.github/workflows/evals.yml) | Pull requests | Runs the offline test suite (`pytest tests -m "not live"`). |

---

## 📂 Project Structure

```text
DailyDiff/
├── .github/workflows/
│   ├── thrice_weekly_brief.yml  # Scheduled pipeline run (Mon, Wed, Fri) + data commit
│   └── evals.yml                # Offline test suite on pull requests
├── backend/
│   ├── run_agent.py             # Pipeline runner, resume/retry rules, publish gate, email delivery
│   ├── test_api.py              # Legacy unittest API checks (not collected by pytest)
│   ├── requirements.txt         # Python dependencies
│   └── app/
│       ├── config.py            # .env loading, paths, model defaults, LangSmith env
│       ├── database.py          # SQLite / Postgres subscribers + history.json I/O
│       ├── checks.py            # Per-brief rule checks & numeric grounding
│       ├── run_health.py        # Run telemetry: counts, timings, failures, warnings
│       ├── run_state.py         # Per-day progress file for resume & email retry
│       ├── schemas.py           # Pydantic request/response models
│       ├── email_dispatcher.py  # HTML email builder + Brevo/SMTP/Resend delivery
│       ├── main.py              # FastAPI endpoints
│       └── agents/
│           ├── graph.py         # Linear LangGraph StateGraph
│           ├── state.py         # AgentState TypedDict
│           ├── models.py        # Provider chain, JSON retry, pacing, input escaping
│           ├── scout.py         # Feed / API signal collection
│           ├── skeptic.py       # History dedup + LLM relevance filter
│           ├── researcher.py    # README / web page evidence scraper (1,800 chars)
│           ├── verifier.py      # Batched fact-check
│           ├── analyst.py       # Batched why / who / verdict
│           └── editor.py        # Batched brief writing & category assignment
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Briefing dashboard, subscribe/unsubscribe, edition picker
│   │   ├── index.css            # Global styles
│   │   └── components/
│   │       ├── AgentEvaluations.jsx  # Evaluation scorecard & case inspector
│   │       ├── TechnicalDetails.jsx  # "How It's Made" architecture page
│   │       └── OnboardingCalendar.jsx # Dispatch schedule & countdown
│   └── public/
│       ├── data/history.json    # Static history cache for first render
│       ├── eval_results.json    # Mirrored latest eval results
│       ├── golden_dataset.json  # Mirrored eval dataset
│       └── planted_errors.json  # Mirrored eval dataset
├── tests/
│   ├── conftest.py              # Forces local SQLite, sets import paths
│   ├── test_checks.py           # Rule check unit tests
│   ├── test_gate.py             # Publish gate & quiet-day tests
│   ├── test_resume.py           # Retry & resume, email wake/retry
│   ├── test_run_state.py        # Daily state file
│   ├── test_nodes.py            # Fail-closed nodes, JSON retry, escaping
│   ├── test_scout_parsing.py    # RSS/Atom & GitHub parsing tests
│   ├── test_api_auth.py         # Notify-endpoint auth & unsubscribe tests
│   ├── test_no_fake_results.py  # Anti-simulation regression guard
│   └── evals/
│       ├── golden_dataset.json  # 25 ground-truth scenarios
│       ├── planted_errors.json  # 13 planted traps (5 prompt injections)
│       ├── run_evals.py         # Runs all evals, saves & mirrors results
│       ├── judge.py             # DeepEval G-Eval judge (Usefulness, Faithfulness)
│       ├── common.py            # Loaders, Wilson intervals, result comparison
│       ├── eval_*.py            # Skeptic, Verifier, Analyst, Editor, Pipeline, History
│       └── results/             # Stored eval runs (latest.json, before/after prompts)
├── data/
│   ├── history.json             # All published editions
│   ├── archive/YYYY/MM/DD.md    # Markdown copy of each published edition
│   └── runs/                    # Per-run snapshots (*.json / *.degraded.json)
│       └── state/               # Per-day progress: stage outputs, rejected URLs, email status
├── SYSTEM_ARCHITECTURE_AND_DECISION_ENGINE.md
├── FREE_TIER_LLM_INCIDENT_REPORT_AND_ANALYSIS.md
└── README.md
```

---

## 📄 License

MIT License.
