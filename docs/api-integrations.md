# External API & Service Integrations

This document lists every third-party API/service this platform calls out to, exactly where each is
called in the code, and why that specific tool was picked over the alternatives that were considered.

| Service | Used for | Network call? |
|---|---|---|
| [Anthropic Claude](#1-anthropic-claude--conversation--evaluation) | AI customer persona conversation + post-call evaluation | Yes |
| [Deepgram](#2-deepgram--speech-to-text) | Transcribing the rep's spoken voice input | Yes |
| [ElevenLabs](#3-elevenlabs--text-to-speech) | Synthesizing the AI customer's spoken replies | Yes |
| [fastembed](#4-fastembed--local-embeddings-for-rag) | Embedding product manuals + queries for RAG | No (local, one-time model download) |
| [PostgreSQL + pgvector](#5-postgresql--pgvector--storage) | Relational data + vector similarity search | N/A (infra, not a third-party API) |

---

## 1. Anthropic Claude — conversation + evaluation

**Where:**
- Shared client: [`backend/app/services/anthropic_client.py`](../backend/app/services/anthropic_client.py) — lazily-constructed `AsyncAnthropic` singleton, reused by both call sites below
- AI customer persona: [`backend/app/services/conversation.py`](../backend/app/services/conversation.py) — `generate_ai_turn()` (line 49), prompt built by `build_system_prompt()` (line 13)
- Post-call evaluation: [`backend/app/services/evaluation.py`](../backend/app/services/evaluation.py) — `evaluate_session()` (line 87)

**Called from** [`backend/app/api/routes/sessions.py`](../backend/app/api/routes/sessions.py):
- `create_session` (line 92) — generates the opening line when a call starts
- `send_message` (line 128) — text-mode reply
- `send_voice_message` (line 180) — reply to a transcribed voice message
- `create_evaluation` (line 230) — post-call scorecard

**API calls made:**
- `client.messages.create()` — plain completion for conversation turns (`max_tokens=300`)
- `client.messages.create()` with `tools=[EVALUATION_TOOL]` and `tool_choice={"type": "tool", "name": "submit_evaluation"}` — forces a structured JSON response for evaluation, rather than parsing free text out of a prose reply

**Why Claude:**
- One model does both jobs (persona roleplay *and* structured evaluation) via different system prompts — no need to integrate a second LLM provider just for scoring.
- Forced tool-use gives reliable, schema-shaped JSON output for the evaluator without a fragile "ask nicely for JSON and hope" prompt — this matters because the evaluation result is parsed and written straight into the database (`overall_score`, `criteria_scores`, `strengths`, `areas_for_improvement`).
- Strong instruction-following for staying in character as a customer persona across many turns without breaking role — this was the main quality bar for the conversation engine and was verified live (see transcript examples in earlier session history).
- The project's whole coaching-quality argument (nuanced, evidence-based feedback that quotes what the rep actually said) depends on strong reasoning quality in the evaluator, not just cheap classification — favored a frontier model over a smaller/cheaper one here.

**Known quirk:** Claude's tool-call output occasionally appends a stray trailing quote character to free-text fields (observed specifically on the `summary` field, reproduced twice independently). Rather than fight it with prompt engineering, it's handled defensively in code — see `_strip_stray_quote()` and `_sanitize_result()` in `evaluation.py` (lines 113, 123).

**Failure handling:** `anthropic.APIStatusError` / `APIConnectionError` are caught and re-raised as a plain `RuntimeError` with a clean message (e.g. "Your credit balance is too low..."), which the route layer turns into a `503` instead of a raw `500`.

---

## 2. Deepgram — speech-to-text

**Where:** [`backend/app/services/voice.py`](../backend/app/services/voice.py) — `transcribe_audio()` (line 9)

**Called from:** `send_voice_message` in [`sessions.py`](../backend/app/api/routes/sessions.py) (line 161) — the endpoint the rep's mic recording is POSTed to.

**API call made:** `POST https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true`, raw audio bytes in the body, `Authorization: Token <key>` header. Plain `httpx` REST call — no SDK.

**Why Deepgram over alternatives (OpenAI Whisper API, Google Speech-to-Text, AssemblyAI):**
- Accurate out of the box for conversational speech with `smart_format` (punctuation, casing) with zero tuning — verified directly against a real synthesized speech sample and matched the source almost word-for-word.
- Simple, well-documented REST endpoint that doesn't require a heavyweight SDK — kept the dependency footprint small (this is a plain `httpx` call, not a Deepgram client library).
- Supports low-latency streaming, which was the original plan for a full-duplex real-time call feel; the project later deliberately scoped down to push-to-talk (record → send whole clip → transcribe) for build simplicity, so only the pre-recorded `/listen` endpoint is used today. Streaming remains a documented future upgrade path with the same provider if the interaction model changes.
- Generous free tier made it practical to verify live during development without a paid commitment up front.

**Why REST instead of streaming:** the interaction model is push-to-talk, not continuous — the rep records a full utterance and sends it once, so there's no ongoing audio stream to feed into Deepgram's WebSocket API. This was a deliberate scope decision (see `docs`/plan history): full-duplex streaming adds real complexity (interruption/barge-in handling, partial-transcript merging) that wasn't worth the risk for an MVP being built without the ability to test live audio hardware during initial implementation.

**Failure handling:** missing key or a non-2xx response raises `RuntimeError`, surfaced to the rep as a clean error on the voice-message endpoint; typing still works as a fallback regardless.

---

## 3. ElevenLabs — text-to-speech

**Where:** [`backend/app/services/voice.py`](../backend/app/services/voice.py) — `synthesize_speech()` (line 34)

**Called from:** a small wrapper, `_maybe_synthesize()`, in [`sessions.py`](../backend/app/api/routes/sessions.py) (line 25), used by:
- `create_session` (line 102) — opening line audio, only when the client asks for voice mode
- `send_voice_message` (line 191) — audio for every AI reply

**API call made:** `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}` with `model_id: eleven_turbo_v2_5`, `xi-api-key` header, `Accept: audio/mpeg`. Returns raw MP3 bytes, which the route base64-encodes onto the session response for the frontend to play back directly (no server-side audio storage).

**Why ElevenLabs over alternatives (OpenAI TTS, Google/Azure/AWS Polly):**
- Noticeably more natural-sounding, emotionally expressive voices — this matters specifically because the product's core value proposition is realism (a rep should feel like they're talking to an actual frustrated/skeptical customer, not a robotic IVR voice).
- `eleven_turbo_v2_5` is optimized for low latency, keeping the turn-based back-and-forth from feeling sluggish.
- Simple REST API, no SDK dependency required (same pattern as Deepgram — kept via `httpx`).

**Why this integration is best-effort, not required:** TTS is treated as an enhancement layer on top of a fully-functional text conversation, not a hard dependency — `_maybe_synthesize()` swallows any `RuntimeError` from ElevenLabs and returns `None` rather than failing the whole request. This was a deliberate design choice made *before* any ElevenLabs key existed, specifically so the conversation and evaluation engines could be built and tested end-to-end without blocking on the slowest-to-provision credential. It also means account-level restrictions on the ElevenLabs side (see below) degrade gracefully instead of breaking calls.

**Known current limitation:** ElevenLabs blocks API access to premade/library voices entirely on free-tier accounts (`402 paid_plan_required: "Free users cannot use library voices via the API"`) — confirmed directly against the live API. This is a billing/plan restriction on the connected account, not a code issue; upgrading to a paid ElevenLabs plan resolves it with no code changes.

---

## 4. fastembed — local embeddings for RAG

**Where:** [`backend/app/services/embeddings.py`](../backend/app/services/embeddings.py) — `embed_texts()` (line 18), model: `BAAI/bge-small-en-v1.5` (line 7)

**Called from:**
- [`backend/app/services/ingestion.py`](../backend/app/services/ingestion.py) — embeds each chunk of an uploaded product manual at ingestion time
- [`backend/app/services/retrieval.py`](../backend/app/services/retrieval.py) — `retrieve_relevant_chunks()` (line 11) embeds the live conversation query to find relevant manual excerpts via cosine distance

**Why a local model instead of a hosted embeddings API (OpenAI, Voyage AI):**
- No API key required — this was the deciding factor. The RAG/knowledge-base feature (Phase 1) was built and fully verified end-to-end *before* any Anthropic/Deepgram/ElevenLabs keys existed, and a local embedding model meant that work didn't have to stall waiting on yet another credential.
- Runs as ONNX (via `fastembed`), which is meaningfully lighter than pulling in `sentence-transformers` + PyTorch for the same job — smaller install, faster cold start.
- Quality is more than adequate at this scale: a capstone-sized knowledge base of a handful of product manuals doesn't need frontier embedding quality, just good-enough semantic matching, and `bge-small-en-v1.5` (384 dimensions) is a well-regarded small embedding model for exactly this kind of workload.
- Clean upgrade path if needed later: Voyage AI is Anthropic's own recommended embeddings partner and would be a natural swap if retrieval quality or scale ever demands it — the retrieval/ingestion code only touches `embed_texts()`, so that swap is a one-file change.

**Trade-off accepted:** the very first manual upload after a fresh install pays a one-time ~130MB model download from Hugging Face; every upload after that is fast and fully offline.

---

## 5. PostgreSQL + pgvector — storage

**Not a third-party API**, but the storage counterpart to the embeddings decision above, so it's worth explaining here: manual chunks and their embeddings live in a `vector` column (via the `pgvector` extension) in the same Postgres database as every other table (users, scenarios, sessions, evaluations).

**Why pgvector over a dedicated vector database (Pinecone, Weaviate, Qdrant):**
- One database for both relational and vector data — no second system to provision, secure, back up, or pay for separately.
- The retrieval need here is small-scale (similarity search over a handful of uploaded manuals per org), well within what pgvector handles comfortably; a dedicated vector DB's extra scaling headroom isn't needed at this size.
- Keeps local development and eventual cloud deployment simpler: one connection string, one migration tool (Alembic), one thing to back up.

---

## Shared design pattern: graceful degradation

Every live external API in this list can fail independently (missing key, no credit/quota, plan restriction, network error) without taking the rest of the app down with it:

- **Anthropic down/unfunded** → the call fails to start or the next reply fails, with a specific error message surfaced to the rep — nothing else breaks.
- **Deepgram down/misconfigured** → sending a voice message fails with a clear error; typing still works.
- **ElevenLabs down/misconfigured/free-tier** → the call proceeds normally with text-only replies; this is treated as best-effort by design, not a failure.

This was a deliberate choice made while building Phases 2-3 without any of these keys in hand yet — each integration point had to degrade cleanly so the rest of the product could be built, demoed, and verified independently of which credentials happened to be available at the time.
