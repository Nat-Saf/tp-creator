"""Vercel serverless entry point (FastAPI ASGI app).

vercel.json rewrites every request to this function; FastAPI does the
routing on the original path. No agent logic yet - only the course
scaffold endpoints.

Local run:
    .venv\\Scripts\\python.exe -m uvicorn api.index:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="TP Creator")

# PLACEHOLDERS - fill real values before submission.
# Schema is exact per docs/project.pdf (GET /api/team_info); batch is 1.
TEAM_INFO = {
    "group_batch_order_number": "1_<ORDER#>",
    "team_name": "<TEAM_NAME>",
    "students": [
        {"name": "<STUDENT_1_NAME>", "email": "<STUDENT_1_EMAIL>"},
        {"name": "<STUDENT_2_NAME>", "email": "<STUDENT_2_EMAIL>"},
    ],
}

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TP Creator</title>
</head>
<body>
  <h1>TP Creator - coming online</h1>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/api/team_info")
def team_info() -> dict:
    return TEAM_INFO


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
