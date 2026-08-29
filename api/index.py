"""Vercel serverless entry point (FastAPI ASGI app).

vercel.json rewrites every request to this function; FastAPI does the
routing on the original path.

Local run:
    .venv\\Scripts\\python.exe -m uvicorn api.index:app --reload --port 8000
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from tpagent import config, runtime
from tpagent.contract import Request
from tpagent.llm_client import LLMClient
from tpagent.rag import retrieve as rag_retrieve
from tpagent.steps import StepsRecorder

app = FastAPI(title="TP Creator")


@app.exception_handler(RequestValidationError)
def _bad_body(_request, _exc) -> JSONResponse:
    # even a malformed body answers in the exact course shape
    return JSONResponse(status_code=200, content={
        "status": "error",
        "error": "The request body must be JSON like {\"prompt\": \"your "
                 "task here\"}.",
        "response": None, "steps": []})

# Schema is exact per docs/project.pdf (GET /api/team_info); batch is 1.
TEAM_INFO = {
    "group_batch_order_number": "1_8",
    "team_name": "Group I",
    "students": [
        {"name": "Natan Safanov", "email": "safanov.natan@gmail.com"},
    ],
}

from pathlib import Path

INDEX_HTML = (Path(__file__).parent / "gui.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/api/team_info")
def team_info() -> dict:
    return TEAM_INFO


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/model_architecture")
def model_architecture() -> Response:
    png = config.ROOT / "docs" / "architecture.png"
    return Response(content=png.read_bytes(), media_type="image/png")


@app.get("/api/agent_info")
def agent_info() -> dict:
    examples = json.loads(
        (Path(__file__).parent / "agent_info_examples.json")
        .read_text(encoding="utf-8"))
    return {
        "description":
            "TP Creator turns a plain-language task description into a "
            "validated FANUC TP (.LS) program for a known robot cell. A "
            "planner model maps your words to the cell's registers and IO "
            "through their pendant notes, a code model writes the program, "
            "and a deterministic three-layer validator (grammar, register "
            "existence, safety limits) checks every draft before delivery; "
            "a mandatory audit adds human-review advisories, and every "
            "model call is traced in the steps array.",
        "purpose":
            "Let a robotics engineer get a runnable, cell-aware "
            "pick-and-place style TP program - with safety advisories and "
            "a full reasoning trace - from one sentence, instead of "
            "hand-writing boilerplate on the teach pendant.",
        "prompt_template": {
            "template":
                "pick a part from <place> and put it on <place>, <style> - "
                "name places by their pendant-note words (e.g. 'conveyor "
                "pick', 'fixture A'); answer follow-up questions as plain "
                "text; send the whole conversation transcript as the "
                "prompt on follow-ups."},
        "prompt_examples": examples,
    }


class ExecuteBody(BaseModel):
    prompt: str


def _report_summary(report) -> str:
    lines = [f"table source: {report.table_source} "
             f"({report.mapping_confidence})",
             f"retries: {report.retries}"]
    for item in report.inferred:
        lines.append(f"inferred: '{item.get('text')}' -> "
                     f"{item.get('decision')}")
    for advisory in report.advisories:
        lines.append(f"advisory: {advisory}")
    return "\n".join(lines)


@app.post("/api/execute")
def execute(body: ExecuteBody) -> dict:
    """Course entry point: {"prompt"} -> exact {status, error, response,
    steps} shape. Follow-ups arrive as the full transcript in "prompt"."""
    recorder = StepsRecorder()
    config.load_dotenv()
    try:
        req = Request(prompt=body.prompt,
                      cell_id=os.environ.get("DEMO_CELL", "line3_fanuc1"))
        resp = runtime.handle(
            req, recorder=recorder,
            retrieve_fn=lambda q: rag_retrieve.retrieve(
                q, llm=LLMClient(recorder)))
    except Exception:
        return {"status": "error",
                "error": "Something went wrong on my side while building "
                         "the program. Please try again in a moment.",
                "response": None, "steps": recorder.steps}

    if resp.status == "ok":
        return {"status": "ok", "error": None,
                "response": resp.program_ls + "\n--- report ---\n"
                + _report_summary(resp.report),
                "steps": recorder.steps}
    if resp.status == "needs_clarification":
        return {"status": "ok", "error": None,
                "response": "\n".join(resp.questions),
                "steps": recorder.steps}
    if resp.status == "rejected":
        return {"status": "ok", "error": None, "response": resp.reason,
                "steps": recorder.steps}
    return {"status": "error", "error": resp.reason,          # failed
            "response": None, "steps": recorder.steps}
