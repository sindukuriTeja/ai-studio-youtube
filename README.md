# AI Film Studio

Turn a one-line idea into a short AI-generated film: a RAG step grounds/refines your
idea against 16,621 real TV episode loglines, Claude writes the script and shot
list, Runway (Gen-4.5) generates a video clip per scene, ElevenLabs generates the
narration, and ffmpeg stitches everything into one final video.

## Pipeline

0. **RAG inspiration** (`backend/services/rag_service.py`, optional) — your idea is
   embedded and matched against 16,621 existing TV episode loglines stored in
   Pinecone (filterable by genre: comedy/drama/horror/scifi). Claude then uses the
   closest matches as grounding to draft a few tighter, more original loglines; the
   best one becomes the actual premise handed to the script writer in step 1. This
   step is skipped automatically if `PINECONE_API_KEY` isn't set — the raw idea is
   used as-is.
1. **Claude** (`backend/services/claude_service.py`) turns the (possibly RAG-refined)
   idea into a title, logline, and a list of scenes, each with narration text and a
   video-generation prompt.
2. **Runway** (`backend/services/runway_service.py`) generates a text-to-video clip
   for each scene using the Gen-4.5 model.
3. **ElevenLabs** (`backend/services/elevenlabs_service.py`) generates narration
   audio for each scene.
4. **ffmpeg** (`backend/services/video_assembly.py`) muxes each clip with its
   narration (padding whichever track is shorter) and concatenates all scenes into
   `final_film.mp4`.

All of this is orchestrated as a background job (`backend/jobs.py`) and exposed
through a small FastAPI app (`backend/main.py`) with a browser UI (`frontend/`).

The RAG step (step 0) began life as a separate standalone project
(`tv_loglines_rag_system/`) — a Pinecone + Claude retrieval-augmented generator for
TV loglines. It's now merged in under `backend/services/rag/` (Pinecone client,
data loader, Claude logline generator) and `backend/services/rag_service.py` (the
facade the film pipeline calls). `scripts/ingest_loglines.py` is the one-time data
loader for (re)populating the Pinecone index from JSONL files, ported from that
project's `ingest.py`.

## Setup

1. Install [ffmpeg](https://ffmpeg.org/download.html) and make sure `ffmpeg` and
   `ffprobe` are on your PATH.
2. Install Python 3.10+.
3. Copy `.env.example` to `.env` and fill in your keys:
   - `ANTHROPIC_API_KEY` — Claude (required)
   - `RUNWAYML_API_SECRET` — Runway (required)
   - `ELEVENLABS_API_KEY` — ElevenLabs (required)
   - `PINECONE_API_KEY` — Pinecone, for the RAG inspiration step (optional; the
     pipeline just skips step 0 and uses your raw idea if this is blank)
4. If you want the RAG inspiration step and don't already have a populated
   Pinecone index named `tv-loglines`, put the genre JSONL files in
   `LOGLINE_DATA_DIR` (default `./tv_loglines_dataset`) and run
   `python scripts/ingest_loglines.py` once.

## Run

macOS / Linux:
```bash
./run.sh
```

Windows:
```
run.bat
```

Then open http://localhost:8000 in your browser.

## Troubleshooting

**Error: `'typing.Union' object has no attribute '__discriminator__' and no __dict__ for setting new attributes`**

This means you're running on **Python 3.14**. Python 3.14 made `typing.Union` immutable,
which breaks a caching trick used by the generated Anthropic/OpenAI-style SDKs (including
the `anthropic` package this project uses) — not a bug in this project's code. The SDK-side
fix hasn't shipped yet, so the workaround is to run on Python 3.11, 3.12, or 3.13.

`run.bat` / `run.sh` now auto-detect and prefer 3.13/3.12/3.11 if installed. If you only have
3.14, install an older version (e.g. `winget install Python.Python.3.12` on Windows, or
`brew install python@3.12` on macOS) and re-run `run.bat`/`run.sh` — it'll pick it up
automatically. If it still falls back to 3.14, delete the `.venv` folder first so it gets
rebuilt with the right interpreter.

## Notes & costs

- Runway video generation and ElevenLabs narration are paid API calls billed to
  your accounts. Each "Generate Film" click creates real, billable requests —
  there is no dry-run/mock mode built in.
- Because your API keys were pasted into a chat conversation to build this
  project, treat them as potentially exposed. Consider rotating them (generating
  new keys and revoking the old ones) in the Anthropic, Runway, and ElevenLabs
  dashboards, then updating `.env`.
- The original standalone RAG project (`tv_loglines_rag_system/config.py`) had a
  live Pinecone key and a live Anthropic key hardcoded as fallback default values
  in source. Both should be treated as exposed and rotated — this merged version
  only reads keys from environment variables, no hardcoded fallbacks.
- `.env` is already in `.gitignore` — never commit it if you put this project
  under version control.

## API

- `POST /api/films` — start a generation job. Body: `FilmRequest` (see
  `backend/models.py`). Optional `genre` field (`comedy`/`drama`/`horror`/`scifi`)
  scopes the RAG inspiration step to that genre.
- `GET /api/films/{job_id}` — poll job status/progress. Once the RAG step runs,
  the response includes `refined_logline` (what was actually sent to the script
  writer) and `inspired_by` (the similar existing loglines that grounded it).
- `GET /api/films/{job_id}/download` — download the finished film.
- `GET /api/health` — checks that the three required API keys are configured, and
  reports `rag_enabled` (whether Pinecone is configured for the inspiration step).
