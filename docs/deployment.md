# Deploying to production

**Stack:** Vercel (frontend) + Render (backend + Postgres, free tier).

## Known limitations of this setup (free tier, chosen deliberately for now)

- **Render's free Postgres expires 30 days after creation**, then is deleted 14 days after that
  unless upgraded to a paid plan. Set a reminder, or upgrade before then if you want to keep the
  data (org, scenarios, call history, scores) beyond ~6 weeks.
- **The backend's filesystem is ephemeral on the free plan** — any product manuals uploaded to the
  knowledge base are lost whenever the service restarts, redeploys, or spins down from inactivity.
  Re-upload manuals as needed, or migrate `backend/app/services/storage.py` to S3-compatible object
  storage later if this becomes a real problem (see `docs/api-integrations.md` for context).
- **Free web services spin down after 15 minutes idle** — the first request after a quiet period
  takes about a minute to wake back up.

None of this affects Anthropic/Deepgram/ElevenLabs — those are unrelated to Render's plan tier.

## One-time setup

### 1. Push this repo to GitHub

Handled by Claude once you provide an (empty) GitHub repo URL.

### 2. Deploy the backend + database on Render

1. Go to the [Render dashboard](https://dashboard.render.com) → **New +** → **Blueprint**.
2. Connect the GitHub repo. Render will detect `render.yaml` at the repo root and show a preview
   of what it's about to create: a `salescoach-db` Postgres instance and a `salescoach-backend` web
   service, both on the free plan.
3. Before confirming, Render will prompt for the environment variables marked `sync: false` in
   `render.yaml`. Paste in:
   - `ANTHROPIC_API_KEY`
   - `DEEPGRAM_API_KEY`
   - `ELEVENLABS_API_KEY`
4. Click **Apply**. Render provisions the database, builds the Docker image, runs
   `alembic upgrade head` automatically (baked into the container's start command — see
   `backend/Dockerfile`), then starts the API.
5. Once live, copy the backend's public URL (something like
   `https://salescoach-backend.onrender.com`) — you'll need it in step 3.

### 3. Deploy the frontend on Vercel

1. Go to the [Vercel dashboard](https://vercel.com/new) and import the same GitHub repo.
2. When configuring the project, set **Root Directory** to `frontend`.
3. Add an environment variable: `NEXT_PUBLIC_API_URL` = the Render backend URL from step 2.5.
4. Deploy. Copy the resulting Vercel URL (e.g. `https://your-app.vercel.app`).

### 4. Point the backend's CORS at the deployed frontend

Back in the Render dashboard, open the `salescoach-backend` service → **Environment**, and update:

```
CORS_ORIGINS=["https://your-app.vercel.app"]
```

(Include `http://localhost:3000` too if you still want local dev to be able to hit the deployed
backend — comma-separate multiple origins as a JSON list.) Save — Render redeploys automatically.

### 5. Verify

Visit the Vercel URL, register a new organization, create a scenario, and run a practice call —
this exercises the frontend, backend, database, and all three external APIs end to end.

## Ongoing deploys

Both Vercel and Render auto-deploy on every push to the connected branch — no manual redeploy step
needed after the initial setup. Database migrations run automatically on every backend deploy via
the Docker container's start command.
