# CodeSentinel (AgentX)

AI-powered autonomous code review platform with a 9-agent LangGraph-orchestrated architecture.

## Quick Start

### Option 1: Start Backend First (Recommended)

```bash
# Terminal 1: Start the backend
cd backend
./start.sh
# OR manually:
# python3 -m venv venv && source venv/bin/activate
# pip install -r requirements.txt
# uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Backend will run at: http://localhost:8000
API docs: http://localhost:8000/docs

```bash
# Terminal 2: Start the frontend
npm install
npm run dev
```

Frontend will run at: http://localhost:3000

### Option 2: Docker Compose

```bash
docker compose up
```

## Architecture

### Frontend (Next.js 14 + TypeScript)
- `/` - Landing page
- `/dashboard` - Start new runs, view stats
- `/runs` - List all runs
- `/runs/[runId]` - Real-time pipeline progress
- `/issues` - All issues across runs
- `/analytics` - Statistics and trends

### Backend (FastAPI + Python)
- `GET /api/v1/health` - Health check
- `POST /api/v1/runs` - Start code review
- `GET /api/v1/runs` - List runs
- `GET /api/v1/runs/{id}` - Run details
- `DELETE /api/v1/runs/{id}` - Cancel run
- `GET /api/v1/stats` - Statistics
- `WebSocket /ws/runs/{id}` - Real-time updates

### 9-Agent Pipeline

1. **Orchestrator** - Validates requests, manages state
2. **Repository Intelligence** - Clones repository, builds context
3. **Code Analysis** - AST analysis, bug detection
4. **Security Scanner** - OWASP, secrets, vulnerabilities
5. **Root Cause Analysis** - Causal chains, impact assessment
6. **Fix Generator** - AI-powered patch generation
7. **Validation Agent** - Reviews fixes, scores confidence
8. **Verification Agent** - Runs tests, checks regressions
9. **PR Creation** - Creates GitHub pull requests

## Environment Variables

### Frontend (.env)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### Backend (backend/.env)
```env
DATABASE_URL=sqlite+aiosqlite:///./codesentinel.db
GEMINI_API_KEY=your-gemini-api-key
GITHUB_TOKEN=your-github-token
CORS_ORIGINS=["http://localhost:3000"]
DEBUG=true
```

## Troubleshooting

### "Backend Offline" shows on dashboard

The backend server is not running. Start it:

```bash
cd backend
./start.sh
```

Or manually:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Port 8000 already in use

Kill the existing process:

```bash
lsof -ti:8000 | xargs kill -9
```

### Module import errors

Make sure you're in the backend directory when running uvicorn:

```bash
cd backend
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, ShadCN UI, Framer Motion
- **Backend**: FastAPI, Python, LangGraph, Google Gemini
- **Database**: PostgreSQL (Supabase) or SQLite (development)
