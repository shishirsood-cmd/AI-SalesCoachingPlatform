# AI-Powered Sales Coaching Platform

See [`.claude/plans`](../../.claude/plans) (or ask Claude) for the full architecture and phased build plan, [`docs/api-integrations.md`](docs/api-integrations.md) for what every external API call does and why that specific service was chosen, and [`docs/deployment.md`](docs/deployment.md) for how to deploy this to Vercel + Render. This repo now covers **Phases 0-5** of that plan: auth + RBAC, scenario/rubric builder + knowledge base, a push-to-talk voice conversation with an AI customer persona, post-call scoring against the scenario's rubric, and dashboards for both roles — all live-tested end-to-end with Anthropic + Deepgram. Only **Phase 6 (stretch)** — mining real call recordings to suggest scenarios — remains.

Manual uploads are parsed, chunked, embedded locally (via `fastembed`, no API key required), and stored in Postgres/`pgvector`, then retrieved at conversation time to ground the AI customer's answers in real product facts instead of having it hallucinate.

**Required API keys** (in `backend/.env`):
```
ANTHROPIC_API_KEY=sk-ant-...      # powers the AI customer persona + evaluator
DEEPGRAM_API_KEY=...              # speech-to-text for the rep's voice input
ELEVENLABS_API_KEY=...            # text-to-speech for the AI's voice reply
```
Restart the backend after changing any of these. Each integration fails independently and gracefully:
- Missing/invalid **Anthropic** key or no credit balance → the call fails to start with a clear error (nothing silently breaks).
- Missing/invalid **Deepgram** key → sending a voice message fails with a clear error; typing still works.
- Missing/invalid **ElevenLabs** key, or a free-tier account (their API blocks premade voices without a paid plan — upgrade at their Plans & Billing) → the call still works fully, just without audio playback; the rep reads replies as text. This is by design (voice output is best-effort).

## Prerequisites

- Node.js 20+
- Python 3.12+
- PostgreSQL 16+ with the `pgvector` extension available, **or** Docker + Docker Compose

## Backend + database

Two ways to run Postgres locally — pick one.

**Option A — Docker** (matches how this will run in the cloud):
```bash
cp backend/.env.example backend/.env   # then fill in JWT_SECRET; keep DATABASE_URL host as `db`
docker compose up -d db backend
docker compose exec backend alembic upgrade head
```

**Option B — Homebrew Postgres** (what this session used, since Docker wasn't installed on this machine):
```bash
brew install postgresql@17 pgvector
brew services start postgresql@17
createuser -s coach
psql -d postgres -c "ALTER USER coach WITH PASSWORD 'coach';"
psql -d postgres -c "CREATE DATABASE salescoach OWNER coach;"
psql -d salescoach -c "CREATE EXTENSION IF NOT EXISTS vector;"

cd backend
cp .env.example .env   # set DATABASE_URL host to `localhost` instead of `db`, and fill in JWT_SECRET
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API runs at http://localhost:8000 (docs at `/docs`).

## Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

App runs at http://localhost:3000.

## Try it out

1. Go to `/register-org` to create an organization — this creates the first Team Lead account and shows an invite code.
2. Go to `/signup` and use that invite code to create a Sales Rep account.
3. Log in as either to see the role-specific dashboard. Team Leads land on `/admin`, Sales Reps on `/practice`; each route redirects away if the logged-in user has the wrong role.
4. As the Team Lead, create a scenario (persona, objections, difficulty, call type, and a rubric whose criteria weights must sum to 100), and upload a product manual (`.pdf` or `.txt`) to the knowledge base — its ingestion status updates from `processing` to `ready` once it's chunked and embedded.
5. As the Sales Rep, go to `/practice`, pick a scenario, and start a practice call. Click **🎤 Start speaking**, say something, click **⏹ Stop & send** — your speech is transcribed, the AI customer replies in character (raising the scenario's objections, referencing the uploaded manual when relevant), and its reply plays back as audio if ElevenLabs is configured. A text input is always available as a fallback.
6. Click **End call**, then wait a few seconds — a scorecard appears with an overall score, a per-criterion breakdown (score + specific feedback tied to what was actually said), strengths, and areas for improvement, all generated from the transcript against the scenario's rubric.
7. Back on `/practice`, a "Your progress" strip shows score history across past calls. As the Team Lead on `/admin`, a "Team analytics" section rolls up average scores by rep, by scenario, and by rubric criterion (weakest skills first) — sorted worst-first so it doubles as a coaching priority list.

Note: the first manual upload after a fresh install downloads a small local embedding model (~130MB, one-time, requires network access) — later uploads are fast.

