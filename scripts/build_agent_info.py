"""Build api/agent_info_examples.json by ACTUALLY RUNNING two prompts
through /api/execute (course Phase 7): the canonical fixture-A prompt and
an ambiguous-fixture prompt that shows the clarification flow. Run with
live models; re-run after any quality tuning to refresh the examples.

    .venv/Scripts/python.exe scripts/build_agent_info.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.index import app
from tpagent import config, modules

# Owner decision (2026-08-30): the RECORDED EXAMPLES show the agent's
# chat steps only (intake, codegen, audit) - the embedding call would
# drown them in provider plumbing. Live /api/execute traces still record
# every provider call, chat AND embeddings (compacted), per the course
# rule; this filter applies to the agent_info showcase alone.
_HIDDEN = {modules.RAG_EMBED, modules.RAG_RETRIEVE}

config.load_dotenv()
os.environ["TP_LLM1"] = "llmod:NBUECSE-gpt-5-mini"
os.environ["TP_LLM2"] = "llmod:NBUECSE-gpt-5-mini"

PROMPTS = [
    "pick a part from the conveyor and put it on fixture A, gently",
    "pick a part from the conveyor and put it on the fixture",
]

client = TestClient(app)
examples = []
for prompt in PROMPTS:
    body = client.post("/api/execute", json={"prompt": prompt}).json()
    assert body["status"] == "ok", body
    examples.append({"prompt": prompt,
                     "full_response": body["response"],
                     "steps": [s for s in body["steps"]
                               if s["module"] not in _HIDDEN]})
    print(f"ran {prompt!r}: {len(body['steps'])} steps, "
          f"{len(body['response'])} chars")

out = ROOT / "api" / "agent_info_examples.json"
out.write_text(json.dumps(examples, indent=2), encoding="utf-8")
print(f"wrote {out.relative_to(ROOT)}")
