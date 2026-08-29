# TP Creator

AI agent that turns plain-language task descriptions into validated FANUC TP
programs. Course delivery target: FastAPI on Vercel serverless, Supabase for
persistence, Pinecone for vectors, LLMod.ai as the only LLM provider.

Status: scaffold only - the agent endpoints land in later phases.

## Endpoints (current)

| Route | Returns |
|---|---|
| `GET /` | minimal HTML page ("TP Creator - coming online") |
| `GET /api/team_info` | team/students JSON per the course spec (placeholders until filled) |
| `GET /api/health` | `{"ok": true}` |

## Run locally

```
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn api.index:app --reload --port 8000
```

Then open http://127.0.0.1:8000/ and http://127.0.0.1:8000/api/health.

## Deploy on Vercel (import)

1. Push this repository to GitHub (public repo; `corpus/raw/` and key files
   stay out via `.gitignore` - verify before pushing).
2. On https://vercel.com: **Add New… → Project → Import** the GitHub repo.
3. Leave Framework Preset as **Other**; no build command and no output
   directory - Vercel auto-detects `api/index.py` as a Python serverless
   function and installs `requirements.txt`.
4. `vercel.json` rewrites every path to `/api/index`, so the FastAPI app
   serves `/` and all `/api/*` routes.
5. Environment variables (Settings → Environment Variables) are added in a
   later phase (LLMOD_BASE_URL/KEY, Supabase, Pinecone); none are needed for
   this scaffold.
6. Deploy, then check `https://<your-app>.vercel.app/api/health`.

Before submission: fill the real order number, team name, and student
names/emails in the `TEAM_INFO` placeholder block in `api/index.py`.
