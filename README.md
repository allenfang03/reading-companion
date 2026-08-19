# Spoiler-Safe Reading Companion

A local web app that helps readers keep track of EPUB novels they're partway through, without ever revealing anything past their current position.

## Tech Stack
- **Backend**: Python (FastAPI)
- **Database**: SQLite
- **Frontend**: React
- **LLM**: Anthropic API (Claude)

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Add your Anthropic API key to .env
# Edit backend/.env and set ANTHROPIC_API_KEY=your-key-here

uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/books/upload` | Upload EPUB, returns `book_id` |
| `GET` | `/books` | List all books |
| `GET` | `/sessions/{token}` | Get session by token |
| `POST` | `/sessions/set-position` | Set reading position |
| `GET` | `/recap` | Get recap since last read |
| `GET` | `/character` | Look up character |

## Core Principle

The LLM must never receive text from *after* the reader's current position. This is enforced architecturally via positional filtering, not just prompting.
