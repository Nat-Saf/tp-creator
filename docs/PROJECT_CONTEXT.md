# tp-creator - project context and decision record

Purpose of this file: Claude Code has no access to the design conversations
that produced this project. This document is the complete transfer of that
context: what the system is, every binding decision and its rationale, what
already exists, and what is pending. Treat it as authoritative history;
docs/DESIGN.md and docs/SOFTWARE.md remain authoritative for interfaces.

## 1. What this project is

An independent agent unit ("TP creator") that converts natural-language
instructions into validated FANUC TP robot programs (.ls source), for a
FANUC R-30iB Mate Plus controller (LR Mate 200iD/7L robot). RoboGuide V9.40
HandlingPRO (and V10) is the simulation environment. Output is reviewed by a
human; the unit never deploys (FTP to controller is a future, human-gated
step, out of scope for v0).

It is designed as one tool in a larger future system: a main orchestrator
will route between capability tools (TP creator, robot-control class, widget
creator). Today there is no main orchestrator; a tier-2 caller (GUI/console,
zero LLM) plays that role behind the same contract.

Strategic context: NL -> vendor-native FANUC TP/LS deployable to real
controllers has very thin commercial competition; the validator grounded in
the actual controller manual targets zero errors in generated output.

## 2. Architecture in one paragraph

Request (contract JSON) -> runtime (no AI: level-A contract checks, persists
inputs, drives the loop, enforces budgets) -> LLM #1 (intake: scope + gap
policy; parameter resolution from the reg/IO table notes; tool selection;
error diagnosis; mandatory post-pass semantic audit) -> generate_program tool
(deterministic prompt renderer -> LLM #2, a stateless fresh-context codegen
emitting .ls text) -> deterministic three-layer validator (grammar ->
existence -> limits) -> on fail, structured error JSON back to LLM #1 for
bounded retries; on pass, LLM #1 audit -> output store (.ls + report) ->
Response. RAG (docs + curated examples) feeds the renderer's DOCS section;
retrieval happens BEFORE generation. Full diagrams: DESIGN.md Fig 1-4,
SOFTWARE.md Fig 1-4.

## 3. Binding decisions and why (chronological, deduplicated)

1. Two-LLM split. LLM #1 = workflow brain of this unit (literacy, not
   fluency; short primer, no RAG in its context -> small-local-model
   capable). LLM #2 = clean-room single-shot codegen; all its FANUC fluency
   arrives in the assembled prompt. Rationale: context hygiene,
   reproducible retries, per-role model choice, independent testability.
2. Deterministic validator, not LLM judgment. All validation is membership
   testing against closed sets (instruction keywords, per-family grammar
   walks, symbol table, limits). "Expected" = the enumerable legal
   continuations at the failure position. Hallucinations cannot escape:
   everything outside the sets is an error by definition. LLM self-review
   was explicitly rejected (shared blind spots, non-determinism).
3. Existence vs correctness split (user-driven correction). Validator layer 2
   answers ONLY "does this index exist" (plus the exists-but-uninitialized
   diagnosis). "Is it the RIGHT index per the pendant notes" is semantics =
   LLM #1's audit, which runs after EVERY pass, unconditionally.
4. Loop ownership: LLM #1 decides, runtime enforces. Validator can block,
   auditor can retry (same budget), only the human rejects. Audit findings
   may trigger a regeneration but never withhold delivery. (Agreed in
   conversation; DESIGN.md v1.4 amendment pending - see section 7.)
5. Renderer is code, not LLM. LLM #1 authors fields (params, program name,
   notes, fix guidance); a Jinja2 renderer authors the document in fixed
   section order: SYSTEM, CELL, DOCS, EXAMPLE?, TASK, NOTES, PREVIOUS+FIX?.
   No-leakage rule: table/config reach the prompt verbatim from the stores.
6. Suggestion policy (bounded): grammar layer only, edit distance <= 2 to a
   UNIQUE legal token, never for symbols, never auto-applied - sole consumer
   is LLM #1 and everything revalidates.
7. Intake gate, two levels: A = runtime mechanical contract validation
   (schema, limits-override attempt, no usable table source) with pre-written
   friendly rejects; B = LLM #1 reasoning (scope, sufficiency) returning
   rejected/needs_clarification THROUGH the runtime. The runtime never
   reasons. Clarification is front-loaded before generation when possible.
8. Contract statelessness: clarification = status needs_clarification +
   questions; caller re-calls with answers. answers accepts
   {"reply": "<raw user text>"} - LLM #1 asked the question and interprets
   the raw reply (tier-2 callers cannot map text to keys). Structured
   {key: value} also valid.
9. reg_io_v1 CSV (Appendix A of DESIGN.md): five columns
   type,index,comment,initialized,value; '#' metadata header (schema,
   cell_id, scanned_at); category/direction are DERIVED from type at parse
   time, never stored (cannot contradict). Dump ALL indexes including
   uncommented ones. value rides along unused in v1. Single-parser rule:
   callers relay bytes; only stores/table.py parses (via reg_io.py).
10. Table source hierarchy (no scan provided): fresh scan > cached CSV for
    the SAME cell_id within max_table_age (staleness measured from the CSV's
    own scanned_at) > default_index_map from static config (mapping marked
    unverified + mandatory review advisory) > else ask. Never silently mixed;
    report always carries table_source + mapping_confidence.
11. Config split: defaults (speed, term, frames, settle) are user policy -
    overridable per request; limits (max speed/wait) are the safety floor -
    dev-owned, never overridable, enforced at level A AND at the GUI layer.
12. RAG: parameters live in unit-owned rag_config.yaml (top_k=5,
    score_threshold, max_context_chars, chunk_strategy logical|fixed).
    Profiles: online (OpenAI-compatible gateway embeddings
    text-embedding-3-small + Pinecone index fanuc-tp-online, dim 1536,
    cosine) and local (Ollama nomic-embed-text + Chroma, future). One index
    per profile; query embedded with the SAME model as the index (asserted).
    Request.rag_backend selects the profile; caller never sends RAG params.
13. Example programs (example_ls): stored in the session store first;
    syntax-only validator pre-check at intake with friendly feedback BEFORE
    the loop; on pass, a symbol report drives LLM #1's foreign-register
    mapping via notes; renderer inserts the example VERBATIM from the file
    (an LLM re-typing 40 lines will silently "fix" one).
14. Envelope rule (caller side): the caller fills the envelope, the unit
    reads the letter. Every Request field is fillable without reading the
    prompt; anything requiring understanding was excluded from the schema.
    Hence tier-2 caller needs zero LLM. Tiers: 1 file CLI, 2 console/GUI
    (current), 3 main orchestrator (future, same contract).
15. User-facing language rule: questions/reasons/advisories are plain
    friendly sentences naming the concrete need (e.g. "I need a
    clarification: can you load an updated IO and registers map for cell
    line3_fanuc1? The one I have is 3 days old.").
16. IR schema (tpagent/ir.py): Pydantic v2, 48 instruction types + 19 motion
    options + 12 helpers (79 models), from HandlingTool V9.40 Ch.7. NOT in
    the v0 runtime loop. Roles: source for RAG instruction cards; future
    structured-generation path (program.schema.json for guided decoding);
    taxonomy reference for validator FAMILIES. Supersedes the old
    fanuc-tp-gen stubs (Phase-B rename debt is moot).
17. Corpus layout: corpus/raw/ (3 FANUC PDFs, provenance only, proprietary -
    internal GitLab only), corpus/prepared/ (extracted markdown, one file per
    instruction family, '##' per instruction = the logical chunks the indexer
    reads), corpus/examples/ (5-10 hand-verified .ls).
18. Model deployment: hybrid start (LLM #1 = Claude Sonnet API; LLM #2 =
    mock now, API for smoke, local Qwen2.5-Coder-32B on the planned RTX 5090
    32GB build later). Fully-local single-model option: Qwen3-Coder-30B-A3B
    both roles. All swaps are env changes (TP_LLM1/TP_LLM2).

## 4. What already exists (do not rewrite - migrate)

- prototype/ : working tier-2 caller + mock unit. contract.py (level-A
  complete), reg_io.py (parser, tested against the template), app_state.py
  (envelope + state, tkinter-free), gui.py (Chat|Program|Report|Settings),
  console.py, app_config.yaml, rag_config.yaml, reg_io_v1_template.csv
  (25 rows, edge cases on purpose). mock_unit.py stands in for the unit and
  DISSOLVES in Phase 7 per SOFTWARE.md sec 11 (its _emit() program becomes a
  fixture; the file survives only as the mock backend for conversation e2e).
- ir/ : ir.py + program.schema.json (verified: registry 48 types; six
  negative validators caught; JSON schema 85 definitions).
- docs/ : DESIGN.md (v1.3), SOFTWARE.md (v2.1), the Claude Code guide docx.
- Bugs already found and fixed in the prototype (now regression assertions
  for the Phase 7 e2e): (a) the article "a" in "pick a part" matched
  "fixture A" and skipped the clarification - fixture matching requires the
  phrase "fixture <letter>"; (b) the "gently" -> settle 1.0s inference was
  lost across the clarification round-trip - inferences persist in the
  session. Also verified: scan relayed once per session; overrides sent only
  when changed from baseline; limit overrides blocked at GUI AND level A.

## 5. The canonical example (used in docs, tests, fixtures)

Cell line3_fanuc1. Table: PR1 home, PR5 conveyor pick, PR6 conveyor approach,
PR7 fixture A approach, PR8 fixture A place, PR9 fixture B place, PR10
uninitialized/uncommented; RO[1] gripper close, DI[3] part present.
Prompt: "Pick a part from the conveyor and place it on fixture A. Close the
gripper gently." -> params resolved from notes; "gently" -> settle 1.0s
(default 0.5); draft v1 seeded errors: line 8 "WAIT 1.0sec" (grammar,
suggestion "WAIT   1.00(sec)") and PR[10] on lines 5+9 (existence); retry 1
fixes both -> pass -> audit advisory "no approach before place - PR[7]
available"; report carries scan_used, table_source, effective_defaults,
positions with note evidence, inferred, retries=1. Ambiguous "the fixture"
(no letter) -> needs_clarification: "Which fixture should I place the part
on - fixture A (PR[8]) or fixture B (PR[9])?"

## 6. Environment facts

- Windows + PowerShell + PyCharm; Python 3.11; venv at .venv.
- GitLab: gitlab.il.innoviz.tech, group operations/automation-team.
- Online RAG stack mirrors the user's prior "medium-rag" project (same
  OpenAI-compatible gateway; known gotchas: gateway base-path 401/404,
  Pinecone dimension must equal 1536 for text-embedding-3-small).
- Hebrew-locale Excel splits CSV on ';' - the reg_io CSV is viewed via
  Data > From Text/CSV, never re-saved from Excel.
- Robot: FANUC LR Mate 200iD/7L, R-30iB Mate Plus, RoboGuide V9.40 + V10
  (COM registration is last-writer-wins - verify binding before COM use;
  COM/FTP work is future scope, not v0).

## 7. Pending / future (named, not started)

- DESIGN.md v1.4 amendment: loop-ownership subsection + audit-retry policy
  (behavior already agreed and encoded in CLAUDE.md; paperwork pending).
- Robot-class scanner emitting reg_io_v1 over the controller web/FTP
  interface (the CSV format was designed so this is a dump loop).
- Local profile activation (Ollama + Chroma index; TP_LLM* swap) on the
  planned RTX 5090 build; GBNF/guided decoding via program.schema.json.
- RoboGuide dry-run as validator layer 4; FTP deploy behind human approval.
- Main orchestrator (tier 3): planner LLM + capability registry; replaces
  the tier-2 caller behind the SAME contract.

## 8. Working style (matters for how you respond)

- One phase per request; STOP after each and wait for the gate. The user
  reviews diffs and pushes back directly - do not batch extra changes.
- Concise, directive communication; usable drafts over lengthy clarification.
- Plan mode for Phases 2 and 6. Known plan corrections to expect: token walk
  per instruction family, NOT one giant regex per line; audit-triggered
  retries never withhold delivery.
