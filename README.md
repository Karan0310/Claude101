# Resume-Job Matcher Agent

An AI-powered agent that analyzes your resume and finds the best-fit jobs from Google Jobs, LinkedIn, and Indeed — complete with fit percentage scores, skill gap analysis, and a feedback loop evaluation system.

**Powered by Claude AI (Anthropic)**

---

## Features

- **Resume Parsing** — Upload PDF, DOCX, or TXT resumes; Claude extracts skills, experience, titles, and career profile
- **Multi-Source Job Search** — Searches Google Jobs, LinkedIn, and Indeed using targeted queries built from your resume
- **Fit Scoring** — Each job gets a 0–100% fit score with match reasons, skill gaps, and application tips
- **Feedback Loop** — Rate each recommendation; the agent evaluates its own precision and provides calibration insights
- **Web UI** — Clean drag-and-drop interface with real-time progress
- **CLI** — Run fully from the terminal with interactive feedback collection
- **Persistent Sessions** — SQLite database stores sessions and feedback for evaluation

---

## Architecture

```
resume-job-matcher/
├── main.py                   # CLI entry point (click + rich)
├── app.py                    # FastAPI web application
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── orchestrator.py       # Central agent coordinator
│   ├── resume_parser.py      # Claude-powered resume extraction
│   ├── job_searcher.py       # Google Jobs / LinkedIn / Indeed search
│   ├── job_matcher.py        # Claude fit scoring (concurrent)
│   └── feedback_loop.py      # Claude evaluation of recommendation quality
│
├── models/
│   └── schemas.py            # Pydantic data models
│
├── storage/
│   └── database.py           # SQLAlchemy async SQLite persistence
│
├── config/
│   └── settings.py           # Pydantic-settings configuration
│
└── web/
    ├── templates/            # Jinja2 HTML templates
    └── static/               # CSS styles
```

### Agent Pipeline

```
Upload Resume
     │
     ▼
[1] Resume Parser (Claude)
     → Extract: skills, experience, titles, keywords, preferred roles
     │
     ▼
[2] Job Searcher (SerpAPI + RapidAPI)
     → Google Jobs + LinkedIn + Indeed
     → Builds targeted queries from resume profile
     │
     ▼
[3] Job Matcher (Claude — concurrent)
     → For each job: calculates fit %, match reasons, gaps, tips
     → Sorted by fit score (highest first)
     │
     ▼
[4] Results Presented to User
     → Web UI or CLI with ranked job cards
     │
     ▼
[5] Feedback Loop (Claude)
     → User rates each recommendation
     → Agent evaluates precision, calibration error, patterns
     → Improvement suggestions for future searches
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/karan0310/claude101.git
cd claude101
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```env
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional — needed for real job search (demo mode used without these)
SERPAPI_KEY=your_serpapi_key        # https://serpapi.com (Google Jobs + Indeed)
RAPIDAPI_KEY=your_rapidapi_key      # https://rapidapi.com (LinkedIn Jobs)
```

### 3a. Run the Web App

```bash
python main.py web
```

Open http://localhost:8000 in your browser, upload your resume, and let the agent find jobs for you.

### 3b. Run the CLI

```bash
python main.py analyze path/to/resume.pdf
python main.py analyze resume.pdf --location "San Francisco" --max-results 15
python main.py analyze resume.pdf --keywords "startup, fintech" --no-remote
```

---

## API Keys

| Key | Provider | Purpose | Required? |
|-----|----------|---------|-----------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Resume parsing + job scoring | **Yes** |
| `SERPAPI_KEY` | [serpapi.com](https://serpapi.com) | Google Jobs + Indeed search | No (demo mode) |
| `RAPIDAPI_KEY` | [rapidapi.com](https://rapidapi.com) | LinkedIn Jobs search | No |

> **Demo Mode**: If no job search API keys are configured, the agent runs in demo mode with synthetic job listings so you can still see the full fit scoring and feedback loop in action.

---

## Feedback Loop Evaluation

After getting job recommendations, you can rate each one:

| Rating | Meaning |
|--------|---------|
| Perfect (🌟) | Exactly what I'm looking for |
| Good (👍) | I'd apply to this |
| Maybe (🤔) | Somewhat relevant |
| No (👎) | Not a match |

The agent then evaluates:

- **Precision** — What % of recommendations were actually relevant?
- **Calibration Error** — How far off were the predicted fit scores from actual relevance?
- **Patterns** — What types of jobs worked/didn't work?
- **Improvement Suggestions** — How to refine future searches?

---

## Web API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Upload page |
| `POST` | `/analyze` | Upload resume + run pipeline |
| `GET` | `/results/{session_id}` | View results |
| `POST` | `/feedback` | Submit job rating |
| `GET` | `/evaluate/{session_id}` | Get evaluation report |
| `GET` | `/health` | Health check |

---

## Development

```bash
# Run with hot reload
python main.py web --reload

# Format code
black .
isort .
```

---

## Requirements

- Python 3.11+
- Anthropic API key (required)
- SerpAPI key (optional — for real Google Jobs + Indeed search)
- RapidAPI key (optional — for LinkedIn Jobs search)
