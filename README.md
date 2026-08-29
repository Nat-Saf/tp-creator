# TP Creator

Plain words in → **validated FANUC TP program** out.

TP Creator is an AI agent that writes robot programs (.LS files) for a FANUC
R-30iB cell. A planner model maps your words to the cell's real registers and
IO through their pendant notes, a code model writes the program, and a
**deterministic three-layer validator** (grammar → register existence →
safety limits) checks every draft before anything is delivered. A mandatory
audit adds human-review advisories, and every model call is traced in the
`steps` array you can inspect in the GUI.

![Architecture](docs/architecture.png)

The topology is a hub: the **Runtime** enforces the loop mechanics (retry
budgets, every draft → Validator, every pass → LLM1-Audit) while the models
only decide strategy. **RAG-Embed** runs offline to index our own-words TP
syntax notes (`corpus/prepared/`) into Pinecone; **RAG-Retrieve** queries
them at request time. All state lives in Supabase - the deployment is fully
serverless.

## Try it

Open the root URL, type a task, press **Run Agent**. The demo cell
(`line3_fanuc1`) understands these pendant-note words:

| Say... | Cell entity |
|---|---|
| home | PR[1] |
| conveyor pick / conveyor approach | PR[5] / PR[6] |
| fixture A (approach / place) | PR[7] / PR[8] |
| fixture B place | PR[9] |
| gripper close / gripper open | RO[1] / RO[2] |
| gripper closed feedback | RI[1] |
| part present / conveyor running | DI[3] / DI[4] |
| green lamp | DO[7] |
| cycle count / part counter | R[1] / R[3] |

Example prompts:

1. `pick a part from the conveyor and put it on fixture A, gently`
2. `pick a part from the conveyor and put it on the fixture` - the agent
   asks *which* fixture; answer in the same box (the GUI sends the whole
   conversation as context).
3. `create a pick and place program with a middle stop that triggers the
   camera on the green lamp output for 1 second`

Each answer shows the report (table source, inferences, safety advisories)
above the program, plus the collapsible **steps trace** - every model call
with its module name, prompt and response.

## API

| Endpoint | Purpose |
|---|---|
| `GET /` | the GUI |
| `POST /api/execute` | `{"prompt": "..."}` → `{"status","error","response","steps"}` |
| `GET /api/agent_info` | description, prompt template, two real recorded runs |
| `GET /api/model_architecture` | the architecture diagram (PNG) |
| `GET /api/team_info` | team details |
| `GET /api/health` | `{"ok": true}` |

## Local development

```
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.template .env    # then fill the keys
.venv\Scripts\python.exe -m tpagent.stores.seed        # load the demo cell
.venv\Scripts\python.exe -m uvicorn api.index:app --port 8000
```

Open http://127.0.0.1:8000. The whole pytest suite runs **offline** (mock
provider + mock database):

```
.venv\Scripts\python.exe -m pytest -q
```

Useful dev commands: `python -m tpagent.validator.verdict <file.ls> [--scan
<reg_io.csv>]` validates any program; `python -m tpagent.rag.index` rebuilds
the Pinecone index from `corpus/prepared/`; `python -m tpagent.architecture`
regenerates the diagram; `scripts/build_agent_info.py` refreshes the recorded
examples.

Development defaults to mock models (`TP_LLM2=mock:tests/fixtures/v1.ls`);
live models run only for explicit smoke tests. The FANUC manuals used as
provenance for `corpus/prepared/` are **not** in this repository - the
prepared notes are our own summaries.

## Deploy (Vercel)

Import the repo, add the `.env` variable names in Project → Settings →
Environment Variables (with `TP_LLM1`/`TP_LLM2` set to the live
`llmod:<model>` values), and every push to `main` deploys.
