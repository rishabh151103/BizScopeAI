# BizScopeAI

BizScopeAI is a local business-investigation assistant. Gemma handles the
conversation and investigation state, Qwen structures requests for new
evidence, and registered Python analytics provide reproducible numerical
results.

## Local deployment

This setup is for one trusted workstation. The application does not yet have
user authentication or tenant-level data isolation; keep both servers bound to
`127.0.0.1`. Do not expose them to a company network or the public internet.

### Requirements

- Python 3.10 or newer
- PostgreSQL 14 or newer, running locally
- Ollama with `gemma3:4b` and `qwen3:4b` available

### Setup

1. Create and activate a virtual environment, then install dependencies:

   ```powershell
   py -3.10 -m venv venv
   .\venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Create a local PostgreSQL database and user, then copy `.env.example` to
   `.env`. Set `DATABASE_URL` to that database. Keep `.env` private; it is
   ignored by Git.

3. Start Ollama and ensure the configured models are installed:

   ```powershell
   ollama pull gemma3:4b
   ollama pull qwen3:4b
   ```

4. Create or upgrade the database tables:

   ```powershell
   python -m Backend.init_db
   ```

5. Start the local app from the project root:

   ```powershell
   python -m uvicorn Backend.main:app --host 127.0.0.1 --port 8000
   ```

Open `http://127.0.0.1:8000/` in a browser. The single-page frontend is served
by FastAPI and uses local JavaScript/CSS assets; no Node, npm, or globally
installed React is required. The former Streamlit interface remains available
as a fallback:

```powershell
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

## Operations

- `GET /health/live` checks that the API process responds.
- `GET /health/ready` checks that PostgreSQL responds.
- The web frontend uses `POST /chat/stream` (server-sent events) to show
  Gemma's answer as it is generated. Analysis and hypothesis checks still run
  first; the stream keeps the browser informed during that work. `POST /chat`
  remains available for JSON clients such as the Streamlit fallback.
- CSV uploads are limited by `BIZSCOPE_MAX_UPLOAD_MB` (50 MB by default).
- Ollama calls time out after `BIZSCOPE_OLLAMA_TIMEOUT_SECONDS` (300 seconds
  by default); connecting to the local server times out after 5 seconds.
  Structured calls retry validation and transient service failures once, but
  do not repeat a timed-out model call. User-facing text allows 768 output
  tokens by default; if a stream reaches its limit or ends before Ollama's final
  chunk, BizScopeAI requests up to two continuations and logs the completion
  reason. Text prompts use an 8192 token context by default; tune
  `BIZSCOPE_LLM_NUM_CTX` and these settings for the workstation's available
  memory and model speed.
- Uploaded datasets are stored under `BIZSCOPE_DATA_DIR` (the project
  `uploads/` directory by default). Back up this directory with the database.
- Each API response includes an `X-Request-ID`. Server logs include that ID,
  route, status, and duration; they do not include chat text, CSV contents, or
  model response text.
- Schema changes run from ordered SQL files in `Backend/migrations/`. Applied
  migration checksums are recorded, and editing an already-applied migration
  stops startup; add a new migration file for later schema changes.
- Back up and restore the database, uploaded CSV files, and Streamlit chat
  history together. Stop both application processes first so the snapshot is
  consistent. The archive is encrypted with Windows DPAPI for the current
  Windows account. It can be restored only under that account on the same
  Windows installation; keep a separate recovery plan if the workstation or
  account is lost. Create one with:

  ```powershell
  .\venv\Scripts\python.exe -m scripts.backup_restore backup .\backups\bizscopeai.bai
  ```

  Restore replaces the configured PostgreSQL database and requires the upload
  and chat-history paths in `.env` to match the paths saved in the backup. Move
  the current upload directory and chat-history file aside first, then confirm
  the database name from `DATABASE_URL` explicitly:

  ```powershell
  .\venv\Scripts\python.exe -m scripts.backup_restore restore .\backups\bizscopeai.bai --confirm-database bizscopeai
  ```

  Replace `bizscopeai` with the actual database name. Restore refuses a nonempty
  upload directory or an existing chat-history database to prevent overwrites.
- The live Ollama E2E test is opt-in because it makes several slow local model
  calls. Run it with:

  ```powershell
  $env:RUN_LIVE_OLLAMA_E2E='1'
  python -m pytest Evaluation/test_main/test_full_e2e.py -q
  ```

## Before team or network deployment

Before allowing network or team access, add authentication and per-user or
organization ownership to datasets and investigations, then enforce ownership
on every API route. Also encrypt backups, monitor application and model health,
define retention and incident procedures, and rehearse recovery on a separate
database. Until those controls exist, keep this pilot bound to localhost and do
not use it for shared access from a networked host.
