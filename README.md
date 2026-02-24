# Financial Document Analyzer

A multi-agent system for analyzing financial documents (PDFs) using CrewAI and GPT-4. Upload a quarterly report or financial statement, and get back detailed analysis including verification, metrics extraction, investment recommendations, and risk assessment.

## What it does

- Reads PDF financial documents (10-K, quarterly reports, etc.)
- Runs 4 AI agents that each specialize in different analysis
- Stores results in PostgreSQL 
- Has a simple web UI + REST API

## Setup

1. Clone and add your API keys to `.env`:
```bash
cp .env.example .env
# edit .env with your OPENAI_API_KEY and SERPER_API_KEY
```

2. Run with Docker:
```bash
docker-compose up --build
```

3. Open http://localhost:8000 and upload a PDF

That's it. The database tables get created automatically on first run.

## How to use

### Web UI
Go to http://localhost:8000, upload PDF, optionally add a specific question, click analyze.

### API
```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@quarterly_report.pdf" \
  -F "query=What are the key financial risks?"
```

Response includes:
- `verification` - document authenticity check
- `financial_analysis` - key metrics and trends
- `investment_recommendations` - buy/hold/sell thesis
- `risk_assessment` - identified risks and mitigations

### Check API health
```bash
curl http://localhost:8000/health
```

## Architecture

4 CrewAI agents working sequentially:
1. **Verifier** - checks document is legit and complete
2. **Financial Analyst** - extracts metrics, analyzes trends
3. **Investment Advisor** - gives investment recommendation
4. **Risk Assessor** - identifies financial/operational risks

Results get saved to PostgreSQL (`analysis` and `analysis_results` tables).

Background jobs go through Celery + Redis.

## Stack

- Python 3.11
- FastAPI 
- CrewAI 0.130.0
- OpenAI GPT-4 Turbo
- PostgreSQL 15
- Redis (for Celery)
- Docker

## Files

```
main.py          - FastAPI app, API endpoints
agents.py        - CrewAI agent definitions  
task.py          - Task definitions for each agent
tools.py         - PDF reader tool
db_models.py     - SQLAlchemy models
celery_app.py    - Celery configuration
worker.py        - Celery worker
index.html       - Web UI
```

## Bugs I fixed

The original code had several issues:

1. **Import errors** - CrewAI 0.130+ changed import paths (`from crewai import Agent` not `from crewai.agents`)
2. **Tool pattern wrong** - Had to use `BaseTool` from `crewai.tools` with `_run()` method
3. **Agents couldn't find files** - Fixed by pre-reading PDF content server-side and injecting into prompts
4. **SQLAlchemy issues** - JSONB import path changed, `metadata` is reserved keyword
5. **Missing validation** - Added PDF header checks, file size limits
6. **No database persistence** - Added PostgreSQL storage for analysis results
7. **Generic error handling** - Added proper HTTP status codes

## Notes

- PDF content is truncated to ~15KB before sending to agents (keeps costs down)
- Each analysis takes 30-60 seconds depending on document size
- Flower dashboard at http://localhost:5555 for monitoring Celery tasks

## Environment variables

See `.env.example` for all options. Main ones:
- `OPENAI_API_KEY` - your OpenAI key
- `SERPER_API_KEY` - for web search (optional)
- `DATABASE_URL` - PostgreSQL connection string
