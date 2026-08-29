# tp-creator - rules for every session

## Read first
- docs/DESIGN.md (Design Document v1.3) and docs/SOFTWARE.md (SW Architecture
  v2.1) are LAW. When code and spec disagree, say so and STOP - never silently
  improvise an interface.
- docs/PROJECT_CONTEXT.md holds the full project history, all decisions and the
  current state. Read it at the start of a session when context seems missing.
- Build order and per-phase prompts: the user follows the Claude Code Guide
  (docs/Learn_ClaudeCode_TPAgent_Guide_v2.0.docx). One phase = one request =
  one green pytest gate. STOP after each phase and wait.

## Environment
- Python 3.11, Windows, PowerShell, PyCharm. venv at .venv; always invoke
  .venv\Scripts\python.exe explicitly, never bare `python`.
- GitLab: gitlab.il.innoviz.tech / operations/automation-team/tp-creator.
- Never commit: .env, .venv/, sessions/, out/, cache/, chroma/, __pycache__/.

## Architecture rules (SOFTWARE.md sec 4 - violations are bugs)
- Imports point DOWNWARD only. apps/ imports contract.py ONLY.
- llm1/llm2 and validator/ NEVER import each other.
- reg_io.py has exactly one importer: stores/table.py (single-parser rule).
- Vendor SDKs live only in llm1.py, llm2.py, rag/. Backend swap = env change.
- Determinism: validator and renderer make no LLM calls, no network, no
  randomness. Same inputs => identical outputs (snapshot-tested).
- No-leakage: the renderer takes table/config from the stores, never from
  LLM #1 output. GenerateArgs has no field that could carry them.

## Loop ownership (agreed, binding)
- LLM #1 decides strategy; the runtime enforces mechanics: retry budget
  (max_attempts), same-error-class-twice escalation, and the unconditional
  edges: every draft -> validator; every pass -> LLM #1 audit; only
  finalize() returns a Response.
- Validator can block, auditor can retry (spending the same budget),
  only the human rejects. Audit findings never withhold delivery.

## Config policy
- static_config defaults are overridable per request via config_overrides;
  limits NEVER are. Reject limit overrides at level A (contract validation).
- rag_config.yaml is unit-owned; one index per embedding profile (online |
  local) - vectors from different embedding models never share a collection.

## Language rule
- Every user-facing string (questions, rejection reasons, advisories) is a
  plain, friendly, self-contained sentence naming the concrete thing needed.
  Status-code language never reaches a human.

## Testing discipline
- Every phase ends green: .venv\Scripts\python.exe -m pytest -q before moving
  on. tests/fixtures/reg_io_v1_template.csv and v1.ls are canonical fixtures.
- TP_LLM2=mock:tests/fixtures/v1.ls is the development default. Live tokens
  only at the guide's Phase 7 smoke, deliberately.

## Course delivery rules (override where conflicting)
- Target: Vercel serverless (Python/FastAPI). NO local filesystem writes except
  /tmp; ALL persistence via Supabase (stores layer). Any api call < 300 s.
- LLM provider: LLMod.ai ONLY (OpenAI-compatible; LLMOD_BASE_URL/KEY).
  Budget $9 TOTAL: temperature 0, max_tokens capped per role, retries <= 2,
  never add an LLM call without stating its purpose and cost. TP_LLM2=mock
  for all development; live models only for explicit smoke tests.
- MODULE NAME REGISTRY (use EXACTLY these, everywhere - diagram, steps[],
  descriptions): Runtime, LLM1-Intake, LLM1-Audit, Renderer, LLM2-Codegen,
  Validator, RAG-Embed, RAG-Retrieve, Stores.
- steps[] traces EVERY LLM-provider call (chat AND embeddings), in order:
  {"module": <registry name>, "prompt": {...}, "response": {...}}.
  The recorder wraps the client - no call can bypass it.
- /api/execute response shape is EXACT: {"status","error","response","steps"}.
  needs_clarification maps to status "ok" with response = the friendly
  question; internal failures map to status "error" + human-readable error.
- Public GitHub: corpus/raw/ NEVER committed; no keys in code or docs;
  prepared/ contains own-words summaries only.
