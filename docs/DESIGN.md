**TP Creator Agent**

**Design Document**

*Natural language to validated FANUC TP/LS programs — an independent
agent unit*

Version 1.3 · July 2026 · caller tier + reg_io_v1 format · companions:
Software Architecture, Claude Code Build Guide

**Contents**

**0 Revision notes (v1.1)**

**1 Purpose and scope**

**2 System context and contract**

**2b Intake gate and the clarification loop**

**2c Missing-scan strategy (table sources)**

**2d The caller side: tiers and the envelope rule**

**3 Architecture overview and data flow**

**4 Module specifications (data in / data out)**

> 4.1 Runtime
>
> 4.2 LLM \#1 — orchestrator
>
> 4.3 Static config
>
> 4.4 Reg/IO table store
>
> 4.5 RAG service
>
> 4.6 Session store (memory)
>
> 4.7 Prompt renderer
>
> 4.8 LLM \#2 — code generator
>
> 4.9 Validator
>
> 4.10 LLM \#1 semantic audit
>
> 4.11 Output store

**5 The retry handshake (LLM \#2 ↔ validator)**

**6 User-provided example programs**

**7 Configuration policy**

**8 End-to-end trace**

**9 Model deployment options**

**Appendix A — reg_io_v1 interchange format**

0 Revision notes

v1.3 (this revision)

- **reg_io_v1 interchange format (Appendix A).** The scan is now a
  five-column CSV relayed verbatim; the contract’s scan field, Section
  2c, the table store (4.4) and the validator existence layer (4.9) were
  updated accordingly, including the new ‘exists but uninitialized’
  diagnosis enabled by the initialized flag.

- **Caller side specified (Section 2d).** Tier model (CLI → console/GUI
  v0 without any LLM → main orchestrator), the envelope rule that makes
  a zero-LLM caller sufficient, and the app_config.yaml /
  rag_config.yaml ownership split. A reference console + GUI
  implementation exists.

- **answers relaxation.** answers now accepts {reply: “\<raw text\>”};
  LLM \#1, which asked the question and holds it in the session,
  interprets the raw reply. Structured {key: value} remains valid for
  tier-3 callers.

- **RAG parameters externalized (Section 4.5).** rag_config.yaml is the
  unit-owned home of top-k, score threshold, context cap and chunking
  parameters, with one profile (and one index) per backend.

- **Figure 1 / Section 4.10 retitled.** The review box now reads ‘LLM
  \#1 semantic audit’ with the caption stating it is the same LLM \#1
  instance in a later turn — not a third model.

v1.2

- **Two-level rejection clarified (Section 2b).** The runtime performs
  only mechanical contract checks against predefined parameters; scope
  and sufficiency judgments belong to LLM \#1’s intake turn and are
  returned through the runtime. The runtime never reasons.

- **User-facing language rule added (Section 2b).** Every string that
  can reach a human — questions, rejection reasons, advisories — is
  phrased by LLM \#1 in plain, friendly, self-contained language naming
  the concrete thing needed.

- **Figure 1 completed.** User block added above the main orchestrator;
  the example syntax pre-check now has its own dashed arrow from the
  session store into the validator; the semantic review shows its inputs
  (params, table notes, program); the output box connects back to the
  runtime, which returns every response (fixes the dead end).

- **Notation.** The § section symbol was replaced by the word ‘Section’
  throughout.

v1.1

Changes traceable to the first design review:

- **Runtime made explicit.** It now appears in Figure 1; the scan is
  persisted by the runtime, never loaded by LLM \#1 (fixes the
  diagram/text mismatch).

- **Missing-scan strategy added (Section 2c).** Source hierarchy scan →
  cached table → default index map, with a hard staleness rule and
  per-program table_source reporting.

- **Intake gate added (Section 2b).** Clarification loops with the
  caller before generation; out-of-scope requests are rejected (new
  status value).

- **Validator scope renamed: existence, not correctness.** The validator
  answers only ‘does this index exist’; whether it is the right index is
  LLM \#1’s semantic review, which is now mandatory after every pass
  (Section 4.9, Section 4.10).

- **No-leakage rule stated (Section 4.7).** One writer (runtime),
  read-only readers; the renderer never accepts table/config content
  from LLM \#1 output.

- **Embedding outsourced and online-first (Section 4.5).** Embedding
  model + vector DB drawn as an external service; v1 uses the online
  stack (OpenAI-compatible gateway + Pinecone), local later, routed per
  request via rag_backend.

- **Example .ls placed in the session store** (visible in Figure 1) and
  given a syntax-only pre-check at intake with early user feedback
  (Section 6).

- **LLM \#1 sized for local.** Short primer only, no RAG reading in its
  context (chunks route to the renderer); the semantic review is an
  audit task suitable for a small model (Section 4.2, Section 9).

1 Purpose and scope

The TP creator agent converts a natural-language instruction (“pick a
part from the conveyor and place it on fixture A”) into a validated
FANUC TP program in .ls source form, ready for human review. It is
designed as an independent, self-contained unit with one
request/response contract, so that today it can be driven directly from
a GUI or CLI, and later it can sit behind a main project orchestrator
alongside other tools (robot class, widget creator) without any internal
change.

In scope: intent extraction, parameter resolution from cell data,
retrieval-grounded code generation, deterministic validation, bounded
self-correction, semantic audit, versioned output with a review report.

Out of scope (by design): scanning the robot (the reg/IO table is
provided per session by the caller), deploying to the controller (FTP is
a future, human-gated step), editing safety limits at runtime, and
cross-session learning.

**The single design principle:** LLMs are used wherever understanding is
required (interpret, infer, generate, decide flow); deterministic code
is used wherever guarantees are required (parse, check, assemble,
store); a human owns anything irreversible on real hardware.

2 System context and contract

The unit exposes one operation: create-or-revise a TP program.
Everything crossing the unit boundary is one of the two payloads below.
Clarification is expressed as a returned status, never as a direct
dialog — this is what makes the unit composable behind any caller.

Request (caller → unit)

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>{</p>
<p>"prompt": "Pick a part from the conveyor and place it on fixture A.
Close the gripper gently.",</p>
<p>"cell_id": "line3_fanuc1",</p>
<p>"scan": "# schema: reg_io_v1\n# cell_id: line3_fanuc1\n# scanned_at:
...\ntype,index,...\nPR,5,conveyor pick,TRUE,...",</p>
<p>// OPTIONAL (Section 2c when absent).</p>
<p>// A reg_io_v1 CSV (Appendix A) relayed VERBATIM -</p>
<p>// the caller never parses it (single-parser rule).</p>
<p>"config_overrides": { "speed": "80mm/sec" }, // optional; DEFAULTS
ONLY, never limits</p>
<p>"rag_backend": "online", // "online" (v1) | "local" - set by the
caller's config</p>
<p>"example_ls": null, // optional user-provided reference program (full
text)</p>
<p>"revision_of": null, // draft_id when the user asks for a change</p>
<p>"answers": {} // replies to a previous needs_clarification.</p>
<p>// {"reply": "&lt;raw user text&gt;"} is accepted: LLM #1</p>
<p>// asked the question and interprets the raw reply.</p>
<p>// {key: value} also valid (tier-3 callers).</p>
<p>}</p></td>
</tr>
</tbody>
</table>

Response (unit → caller)

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>{</p>
<p>"status": "ok | needs_clarification | rejected | failed",</p>
<p>"draft_id": "d7f3_v2",</p>
<p>"program_ls": "/PROG PICK_PLACE_A ... /END", // inline text</p>
<p>"file_ref": "out/d7f3/PICK_PLACE_A_v2.ls", // stored copy</p>
<p>"report": {</p>
<p>"scan_used": "2026-07-04T10:42:00",</p>
<p>"table_source": "scan", // scan | cache(&lt;age&gt;) |
default_map</p>
<p>"mapping_confidence": "verified", // verified | unverified
(default_map runs)</p>
<p>"effective_defaults": { "speed": "80mm/sec", "term": "FINE", "utool":
1, "uframe": 1 },</p>
<p>"positions": { "PR[5]": "note 'conveyor pick'", "PR[8]": "note
'fixture A place'" },</p>
<p>"inferred": [ { "text": "gently", "decision": "gripper settle 1.0s
(default 0.5s)" } ],</p>
<p>"retries": 1,</p>
<p>"advisories": [ "no approach move before place; PR[7] is available"
]</p>
<p>},</p>
<p>"questions": [] // needs_clarification only; ALWAYS plain
friendly</p>
<p>// language, e.g. "I need a clarification: can you</p>
<p>// load an updated IO and registers map for cell</p>
<p>// line3_fanuc1? The one I have is 3 days old."</p>
<p>}</p></td>
</tr>
</tbody>
</table>

The caller (today: GUI/CLI; later: main orchestrator) is responsible for
relaying questions to the user and re-calling with answers, for
presenting the program and report for human review, and for the
freshness of the scan it supplies (the timestamp comes from the CSV
itself, not from the caller’s honesty). The unit echoes scan_used in
every report so the reviewer always knows which mapping the program was
built against.

2b Intake gate and the clarification loop

Before any generation, incoming requests pass a two-level gate. The
levels differ in who decides — and only one of them can reason:

| **Level**               | **Decided by**       | **Checks**                                                                                                         | **Nature**                                                                                                                                                                             |
|-------------------------|----------------------|--------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A — contract validation | Runtime (code)       | request schema well-formed; config_overrides touches no limits key; a usable table source exists per Section 2c    | Mechanical accept/reject against predefined parameters. No reasoning, no LLM. Failures return status rejected with a fixed, pre-written friendly message.                              |
| B — intake reasoning    | LLM \#1 (first turn) | in scope (a TP-program request at all)? task family recognizable? required parameters present or safely derivable? | Judgment. Off-scope → rejected with a reason LLM \#1 phrases; gaps → needs_clarification with concrete questions. Returned through the runtime — the runtime routes, it never decides. |

The clarification loop: the caller relays questions to the user and
re-calls with answers; each iteration is a full contract round-trip, so
the unit stays stateless toward its caller. Mid-loop clarification still
exists as a fallback (an ambiguity can surface only after retrieval),
but the intent is front-loading: raw-data misses are caught at intake.

User-facing language rule

Every string that can reach a human — questions, rejection reasons,
advisories — must be phrased in plain, friendly, self-contained language
that names the concrete thing needed and why. Status codes are for
machines; sentences are for people. LLM \#1 authors these strings (for
level-A rejects, the fixed messages are pre-written by the developer to
the same standard).

| **Not acceptable**                  | **Required style**                                                                                                                     |
|-------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| need clarification, requesting scan | “I need a clarification: can you load an updated IO and registers map for cell line3_fanuc1? The one I have is 3 days old.”            |
| ambiguous target: PR\[8\]\|PR\[9\]  | “Which fixture should I place the part on — fixture A (PR\[8\]) or fixture B (PR\[9\])?”                                               |
| rejected: out of scope              | “I can only create FANUC TP programs. This looks like a general robot-configuration question — the main assistant can help with that.” |

2c Missing-scan strategy (table sources)

The operator will not always provide a fresh scan. The table used for a
session comes from exactly one of three sources, in strict priority,
never silently mixed:

| **Priority** | **Source**                                             | **Rule**                                                                                                                        | **Report marking**                                                                                        |
|--------------|--------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| 1            | Fresh scan in the request                              | persisted verbatim, timestamped                                                                                                 | table_source: scan; mapping_confidence: verified                                                          |
| 2            | Cached table (the last reg_io_v1 CSV kept per cell_id) | same cell_id only, and age ≤ max_table_age from static config, measured from the CSV’s own scanned_at header; otherwise refused | table_source: cache(\<age\>); verified + advisory noting the age                                          |
| 3            | Default index map                                      | dev-owned conventions in static config (e.g. PR\[1\]=home, RO\[1\]=gripper); positions cannot be trusted, only indexes          | table_source: default_map; mapping_confidence: unverified + mandatory advisory: review mapping before use |

If none of the three is available (unknown cell, no cache, no default
map), intake returns needs_clarification requesting a scan. The
staleness rule exists precisely to prevent the failure the review
flagged: an old mapping from a previous session being trusted as if
fresh. A cached table never crosses cell_id boundaries, never exceeds
max_table_age, and its age is always visible to the human reviewer in
the report.

2d The caller side: tiers and the envelope rule

**The envelope rule:** the caller fills the envelope; the unit reads the
letter. The Request schema was filtered by one test — can a program fill
this field without reading the prompt? Fields that pass (identifiers,
file contents relayed verbatim, held conversation state, configuration)
are in the schema; anything requiring understanding (task type, target
registers, speeds, intent) was deliberately excluded and pushed inside
the unit to LLM \#1’s intake. This is why no LLM is needed on the caller
side until real multi-tool routing exists.

| **Field**        | **Auto-filled from**                                                                                       | **When**                   |
|------------------|------------------------------------------------------------------------------------------------------------|----------------------------|
| prompt           | the textbox, verbatim — never parsed, rewritten or ‘prepared’                                              | every send                 |
| cell_id          | app setting (chosen once, or per-station config)                                                           | session start              |
| scan             | reg_io_v1 CSV auto-loaded from a known path; later fetched by the robot class; relayed once, unit persists | first request of a session |
| config_overrides | the Settings panel — only values the user actually changed from baseline                                   | every send                 |
| rag_backend      | deployment config; the user never sees it                                                                  | every send                 |
| example_ls       | file contents if the user attaches a .ls; else null                                                        | when attached              |
| revision_of      | held state: last draft_id, cleared by ‘New program’; LLM \#1 backstops a forgotten reset                   | every send                 |
| answers          | held state: if the last response was needs_clarification, the next message ships as {reply: text}          | automatic                  |

Three caller tiers, replaceable behind the same contract:

- **Tier 1 — file CLI.** One contract call from a JSON file. Enough for
  tests, useless for conversation.

- **Tier 2 — console / GUI v0, zero LLM (current).** A conversational
  shell holding exactly two pieces of state (last draft, pending
  question) plus configuration. A reference implementation exists
  (console + tkinter GUI with Chat / Program / Report / Settings tabs)
  and lives entirely outside the unit, importing nothing but the
  contract. It also serves as the boundary-enforcement test: the day any
  caller reaches around the contract into unit internals, the violation
  is visible.

- **Tier 3 — main orchestrator (future).** Planner LLM, capability
  registry, robot class, scan-freshness policy. It replaces tier 2
  behind the same contract; nothing in the unit moves.

Configuration ownership on the caller side

| **File**        | **Owner**                                                                         | **Contents**                                                                                                                      | **Reaches the unit as**                                |
|-----------------|-----------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| app_config.yaml | caller / GUI                                                                      | cell_id, scan path, rag_backend, unit transport (direct \| http), overridable-defaults baseline                                   | Request fields, mechanically                           |
| rag_config.yaml | the unit (GUI may edit it as a developer convenience, ownership stated in the UI) | backend profiles (online: gateway embeddings + Pinecone; local: Ollama + Chroma), chunking and retrieval parameters — Section 4.5 | never in a request; only rag_backend selects a profile |

3 Architecture overview and data flow

<img src="media/db4fdbe2c27c80f41ec57ad6a4d9d9659ebfdea6.png"
style="width:4.58333in;height:6.9375in" />

*Figure 1 — The TP creator unit (v1.2). The user talks to the main
orchestrator, never to the unit directly. The runtime is the entry
component, the only writer of stores, and the return path for every
response (the output box hands the result back to it). The dashed arrow
from the session store to the validator is the example syntax pre-check;
small dashed stubs list what the validator and the audit read. The ‘LLM
\#1 semantic audit’ box is the same LLM \#1 instance in a later turn,
drawn separately because it is a distinct step. The embedding model +
vector DB is an outsourced service. Renderer inputs are detailed in
Figure 2.*

The numbered flow:

- **① Request in / intake loop** — the contract JSON enters the runtime,
  which performs the mechanical level-A checks (Section 2b). Scope and
  gap judgments are NOT made here — they happen at LLM \#1’s intake turn
  (step ③) and are returned through the runtime. Clarification may
  iterate with the caller before generation.

- **② Inputs persisted** — the runtime (no LLM) writes the table per the
  Section 2c source hierarchy and stores the example .ls in the session
  store; the example gets an immediate syntax-only pre-check (the dashed
  session-store → validator arrow in Figure 1), and failures are
  returned as friendly feedback before the loop starts (Section 6).

- **③ LLM \#1 intake and params** — reads the table (notes) and
  effective defaults, resolves parameters, applies the gap policy:
  default / infer / ask.

- **④ Retrieval** — LLM \#1 authors the query string; the outsourced
  embedding service embeds it and the vector DB returns top-k chunks
  (online in v1, Section 4.5). Chunks route to the renderer, not through
  LLM \#1’s context.

- **⑤ Params out** — LLM \#1 invokes generate_program: params, program
  name, notes, fix guidance on retries.

- **⑥ Prompt assembled** — the renderer builds the LLM \#2 prompt from
  fixed sections (Figure 2).

- **⑦ Draft to validator** — LLM \#2 returns raw .ls; the runtime hands
  it to the validator with the table key-set and the limits.

- **⑧ Errors back** — a failing verdict returns to LLM \#1 for bounded
  diagnosis and retry.

- **⑨ Semantic review — always** — every passing program is audited by
  LLM \#1 for mapping correctness and intent (Section 4.10); a syntactic
  pass alone is not enough, exactly because the validator checks
  existence, not correctness.

- **⑩ Store and respond** — the output is handed back to the runtime,
  which returns every response shape — program + report, questions, or
  rejection — to the caller.

4 Module specifications

For each module: its role, exactly what flows in, exactly what flows
out, and what it must never do. “Runtime” below means plain code in the
unit — the glue that calls everything else.

4.1 Runtime

|       |                                                                                                                                                                                                                                                           |
|-------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Role  | Session loop and glue (now explicit in Figure 1 as the unit’s entry component). Receives the request, persists the scan, drives the LLM \#1 tool loop, calls the validator after every draft, enforces retry bounds, writes outputs, shapes the response. |
| In    | Contract request; tool-call outputs from LLM \#1; drafts from LLM \#2; verdicts from the validator.                                                                                                                                                       |
| Out   | Contract response; files in the session and output stores.                                                                                                                                                                                                |
| Never | Makes semantic decisions. If a branch requires judgment, it belongs to LLM \#1; if it requires correctness, to the validator.                                                                                                                             |

4.2 LLM \#1 — orchestrator

The workflow brain of this unit only (not a general orchestrator). It
needs TP literacy, not TP fluency: what a motion instruction is made of,
what the register classes mean, which parameters each task family
requires. That literacy comes from a ~2-page domain primer in its system
prompt plus per-intent parameter checklists and few-shot extraction
examples; instruction-level syntax deliberately lives elsewhere (in LLM
\#2’s assembled prompt).

|       |                                                                                                                                                                                                                                                          |
|-------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Role  | Extract intent; resolve parameters from the reg/IO table notes and effective defaults; decide ask-vs-default for gaps; author program name and notes; call tools; diagnose validator errors; run the semantic review; decide retry/re-retrieve/escalate. |
| In    | System prompt (domain primer); user prompt; reg/IO table; effective defaults + limits; RAG results it requested; verdict JSONs; session history (previous drafts, decisions); user answers on revision calls.                                            |
| Out   | Structured JSON only: params object, program_name, notes, rag queries, fix guidance on retries, questions for needs_clarification, semantic advisories.                                                                                                  |
| Never | Writes TP code; writes the LLM \#2 prompt document; judges code correctness (that is the validator’s job); fills safety-critical gaps silently (positions, payloads → questions instead).                                                                |

**Sized for local:** LLM \#1 is deliberately kept small-model-capable.
Its knowledge arrives as a short system-prompt primer; RAG chunks never
enter its context (they route to the renderer); its outputs are
structured JSON; and its two judgment tasks — intake triage and the
semantic audit — are comparison/extraction work, not generation. This
keeps the future fully-local configuration (Section 9) realistic.

**Gap policy:** safe defaults come from config (speed, termination,
frames); inferable values come from table notes (“conveyor” → PR\[5\]
‘conveyor pick’) with judgment applied to wording (“gently” → longer
settle); genuinely missing safety-critical data is returned as a
question — never invented.

4.3 Static config

|       |                                                                                                                                                         |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| Role  | Developer-owned policy file shipped with the unit. Two sections with different rules: defaults (session-overridable) and limits (immutable at runtime). |
| In    | Edited only by the developer, in Git.                                                                                                                   |
| Out   | Effective defaults → LLM \#1 and the renderer’s CELL section; limits → the validator’s layer 3 and the CELL section.                                    |
| Never | Written by any LLM or by the caller. config_overrides may override defaults per session; nothing overrides limits.                                      |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p># static_config.yaml</p>
<p>defaults: { speed: "100mm/sec", pick_speed: "50mm/sec", term:
"FINE",</p>
<p>utool: 1, uframe: 1, gripper_settle_sec: 0.5 }</p>
<p>limits: { max_speed_mmsec: 250, max_wait_sec: 10 }</p>
<p>retry: { max_attempts: 3 }</p>
<p>table: { max_table_age_hours: 72 } # cache freshness bound (see
2c)</p>
<p>default_index_map: # used ONLY when no scan and no cache</p>
<p>PR: { 1: "home" }</p>
<p>IO: { "RO[1]": "gripper close" }</p></td>
</tr>
</tbody>
</table>

4.4 Reg/IO table store

|       |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Role  | The per-session symbol table: registers and IO points with their pendant notes. The unit never scans; the runtime materializes the table from one of the three Section 2c sources (scan / cache / default map), parsing the reg_io_v1 CSV (Appendix A) with the single parser in the system — callers relay bytes. Derived fields (category REG/IO, direction in/out) are computed from type at parse time, never stored in the file, so they can never contradict it. The store records source, the CSV’s own scanned_at, and the resulting mapping confidence. |
| In    | scan object from the request (step ②).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Out   | Verbatim register list → renderer CELL section (the whitelist LLM \#2 must use); key set → validator layer 2 (membership); notes → LLM \#1 (natural-language → address mapping, e.g. PR\[5\] ‘conveyor pick’).                                                                                                                                                                                                                                                                                                                                                   |
| Never | Edited by an LLM; paraphrased on its way into the prompt (verbatim insertion by code).                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

4.5 RAG service

The embedding model and the vector database are an outsourced service,
drawn outside the unit in Figure 1. Version 1 runs fully online,
mirroring the proven medium-rag stack: an OpenAI-compatible gateway for
embeddings plus Pinecone for storage/search. A local backend (Ollama
embeddings + Chroma) is a planned second profile; the caller’s
configuration selects the route and passes it per request as rag_backend
— the unit executes whichever route it is told.

**Parameters live in rag_config.yaml (unit-owned):** retrieval — top_k
(default 5), score_threshold, max_context_chars (hard cap on the DOCS
text handed to the renderer); indexing — chunk_strategy (logical: one
instruction family or one worked example per chunk, preferred for TP
docs; fixed: sliding window with chunk_size_chars /
chunk_overlap_chars). One profile per backend, each with its own index
and its embedding model recorded in the collection metadata.

Two phases, both deterministic code. Offline indexing: the FANUC TP
manual and curated .ls examples are chunked by logical unit, embedded,
and stored. Online retrieval: LLM \#1 authors only the query string; the
service embeds it and returns top-k chunks straight to the runtime for
the renderer’s DOCS section. Hard invariants: queries are embedded with
the same model as the index, and each backend keeps its own index —
vectors from different embedding models are incompatible, so online and
local never share a collection.

|       |                                                                                                                                  |
|-------|----------------------------------------------------------------------------------------------------------------------------------|
| In    | Query string from an LLM \#1 tool call, e.g. “L motion PR approach RO ON WAIT”; k (default 4–6).                                 |
| Out   | Chunk texts + ids + scores → runtime → renderer DOCS section (verbatim) and back to LLM \#1 when it asked for its own reasoning. |
| Never | Generates text; filters by meaning (that is LLM \#1’s call); embeds with a different model than the index.                       |

4.6 Session store (memory)

The unit’s working memory for one program-creation task, kept as plain
files. It is deliberately not cross-session learning: it remembers
everything about this task and nothing about previous tasks. (The
accumulated logs do become a future asset — a corpus for mining few-shot
examples or fine-tuning LLM \#2 — but that is an offline activity, not
runtime memory.)

<table>
<colgroup>
<col style="width: 18%" />
<col style="width: 81%" />
</colgroup>
<tbody>
<tr class="odd">
<td>Contents</td>
<td><p>drafts/ (v1..vn raw .ls)</p>
<p>verdicts/ (validator JSON per draft)</p>
<p>params_history.json (per attempt)</p>
<p>decisions.log (LLM #1 diagnoses)</p>
<p>example.ls + example_report.json (when provided; shown in Figure 1
inside the runtime-owned stores)</p></td>
</tr>
<tr class="even">
<td>Serves</td>
<td><p>PREVIOUS + FIX prompt sections on retries</p>
<p>revision_of across contract calls</p>
<p>diffs for user review</p>
<p>the escalation rule: same error class twice → stop retrying, change
strategy</p></td>
</tr>
</tbody>
</table>

4.7 Prompt renderer

Deterministic code (templates), and the most misunderstood block: it is
not “a container for a prompt LLM \#1 wrote”. LLM \#1 authors fields;
the renderer authors the document. Same inputs produce a byte-identical
prompt — that is what makes retries comparable, tests meaningful, and
the register whitelist tamper-proof (it reaches LLM \#2 verbatim from
the store, never filtered through a model).

**No-leakage rule:** static config and the reg/IO table have exactly one
writer (the runtime) and read-only readers. LLM \#1 reads them to
decide; the renderer reads them to emit verbatim. The renderer never
accepts table or config content from LLM \#1’s output — so a stale or
paraphrased copy inside LLM \#1’s context can at worst mislead a
parameter (caught by review), but can never alter the whitelist or
limits LLM \#2 and the validator see.

<img src="media/31cd350fb0a54115792f09edcbe6ceb5677fc698.png"
style="width:5in;height:6.03125in" />

*Figure 2 — Prompt assembly. Purple sections are authored by LLM \#1,
teal sections are pulled verbatim from stores, gray is fixed text.
Dashed sections appear only when relevant (example provided; retry).*

| **Section**    | **Source**              | **Content**                                                                                              |
|----------------|-------------------------|----------------------------------------------------------------------------------------------------------|
| SYSTEM         | fixed text              | Role, hard output rules: emit one complete .ls program, no markdown, no commentary.                      |
| CELL           | config + table          | Effective defaults, limits, and the full register/IO whitelist with notes — “use ONLY these”.            |
| DOCS           | RAG store               | Top-k documentation chunks and examples, verbatim.                                                       |
| EXAMPLE        | session store           | User-provided reference program, verbatim, with adaptation instructions (only when supplied).            |
| TASK           | LLM \#1                 | The params JSON.                                                                                         |
| NOTES          | LLM \#1                 | program_name, header comment, per-step comments to embed as /ATTR COMMENT and ! lines.                   |
| PREVIOUS + FIX | session store + LLM \#1 | Prior draft verbatim + the validator errors + LLM \#1’s fix guidance; “change nothing else”. Retry only. |

4.8 LLM \#2 — code generator

|       |                                                                                                                                                                                                                                     |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Role  | Single-shot TP/LS emission. Stateless by design: fresh context per call, no tools, no memory, no knowledge that a validator exists. All its FANUC fluency arrives in the assembled prompt (CELL whitelist + DOCS chunks + EXAMPLE). |
| In    | The rendered prompt document, nothing else.                                                                                                                                                                                         |
| Out   | Raw .ls text → runtime (which stores it as draft vN and forwards to the validator).                                                                                                                                                 |
| Never | Talks to the validator; sees conversation history; chooses registers outside the CELL whitelist without being caught one step later.                                                                                                |

4.9 Validator

**Scope, stated precisely:** layer 2 answers existence, not correctness.
‘Does PR\[8\] exist in this cell’s table’ is set membership —
mechanical, free, and something an LLM genuinely misses in a 40-line
program. ‘Is PR\[8\] the right fixture for this task’ is semantics — the
validator cannot answer it and does not claim to; that judgment belongs
to LLM \#1’s semantic review, which runs after every pass (Section
4.10). The validator’s table access is therefore read-only key-set
access; it never interprets notes.

Deterministic three-layer sieve. It never predicts what LLM \#2 meant —
all validation is membership testing against closed sets, which is why
hallucinations it “cannot anticipate” are caught anyway: everything not
in the sets is an error by definition. TP is a closed language: a finite
instruction list, a finite grammar per instruction, and a finite
per-cell symbol table.

<img src="media/87c5821e7dc61bae52e51f86113d75b16389a311.png"
style="width:5.67708in;height:4.17708in" />

*Figure 3 — The three-layer sieve. Layer 2 checks existence only —
correctness of the chosen index is LLM \#1’s review. Only a draft
passing all three layers produces a pass verdict.*

Worked examples of “how does it know what was expected”

- **Invented instruction.** “GRIP_SOFT RO\[1\] ;” — the first token is
  looked up in the family dictionary {J, L, C, WAIT, IF, SELECT, CALL,
  JMP, LBL, R\[, PR\[, RO\[, DO\[, UFRAME_NUM, UTOOL_NUM, !, …}.
  GRIP_SOFT is not a member → error listing the legal keyword set. The
  validator has no idea what GRIP_SOFT means and does not need to.

- **Invented option inside a legal instruction.** “L PR\[5\] 100mm/sec
  FINE Grip ;” — the motion grammar walks token by token: target matches
  the PR pattern, the speed unit is in {mm/sec, cm/min, msec, sec, %},
  FINE is in {FINE, CNT0–100}; at position 5 the legal continuations are
  the motion-options set {Offset, Tool_Offset, ACC, TB, TA, …} or
  end-of-line. “Grip” is in neither → error citing the column and that
  exact set. At every position of a grammar walk the legal next tokens
  are enumerable by construction — that is what a grammar is.

- **Invented symbol.** Every PR\[n\]/R\[n\]/RO\[n\]/DI\[n\]/DO\[n\] in
  the file is regex-extracted and set-differenced against the table
  keys. PR\[10\] with table {1,5,6,7,8,9} → error carrying the known set
  and its notes. The reg_io_v1 initialized flag adds a second, distinct
  diagnosis: ‘PR\[10\] exists but is uninitialized and unlabeled — did
  you mean PR\[6\]?’ is a different error than ‘PR\[10\] does not
  exist’, and LLM \#1 repairs them differently. This is why the robot
  class must dump ALL indexes, including uncommented ones.

- **Legal syntax, illegal value.** “L PR\[5\] 400mm/sec FINE ;” parses
  and resolves cleanly; layer 3 compares 400 against max_speed_mmsec 250
  → error.

Error JSON

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>{ "verdict": "fail", "draft_id": "v1",</p>
<p>"errors": [</p>
<p>{ "layer": "grammar", "line": 8, "col": 9, "found": "1.0sec",</p>
<p>"expected_form": "WAIT &lt;t&gt;.00(sec)", "suggestion": "WAIT
1.00(sec)" },</p>
<p>{ "layer": "symbol", "line": 5, "ref": "PR[10]",</p>
<p>"message": "PR[10] not in reg_io_table (scan 10:42)",</p>
<p>"known_pr": {"1":"home","5":"conveyor pick","6":"conveyor
approach",</p>
<p>"7":"fixture A approach","8":"fixture A place","9":"fixture B place"}
} ],</p>
<p>"stats": { "mn_lines": 14, "parsed_ok": 12, "limits_ok": true }
}</p></td>
</tr>
</tbody>
</table>

Suggestion policy (bounded on purpose)

- Grammar layer only, and only when the found token has edit distance ≤
  2 to exactly one member of the legal set at that position (mm/s →
  mm/sec). Ambiguous → field omitted.

- Never for symbols: the validator must not guess which PR the model
  meant — it supplies the known list with notes and LLM \#1 makes the
  semantic call.

- Never applied automatically. The only consumer is LLM \#1, and
  whatever LLM \#1 produces is validated again — so the worst case of a
  wrong suggestion is one wasted retry, not a wrong program.

4.10 LLM \#1 semantic audit

This is the same LLM \#1 instance in a later turn of its loop — not a
third model; Figure 1 draws it as a separate box only because it is a
distinct step with distinct inputs. Mandatory: it runs after every
validator pass, unconditionally — a syntactic pass says nothing about
whether the mapping is right. LLM \#1 performs one audit turn using what
the parser structurally cannot see: did the program use the right
registers per the notes (PR\[8\], not PR\[9\]); did the requested
defaults and overrides actually land in the code; is the step sequence
sane (grip after arrival, approach before place, no place before pick).
Output is a list of advisories in the report. It is an auditor, not a
gate: it flags, the human decides. The moment it can silently block or
approve, LLM judgment has been reintroduced as ground truth.

4.11 Output store

|       |                                                                                                                                                                                                                                                                          |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Role  | Terminal artifact storage: out/\<session\>/\<PROGRAM\>\_vN.ls + report.json. The response carries the program inline and the file reference; the caller decides presentation (the intended flow: the main orchestrator exposes program + report to the user for review). |
| Audit | Session store + output store together give the full trail: prompt → drafts → verdicts → decisions → final file.                                                                                                                                                          |

5 The retry handshake (LLM \#2 ↔ validator)

The handshake is mediated and asymmetric by design. LLM \#2 is stateless
— prompt in, text out, gone; it does not know a validator exists. The
validator does not know an LLM produced its input. The only shared
language is the error JSON, and the only component that interprets it is
LLM \#1. That seam is a data format, not a relationship — which is why
either side can be swapped independently (LLM \#2: API model ↔ local
model; validator: add layers) with zero impact on the other.

<img src="media/a220931c2c87001d4b0555a6faa011fc00be00a2.png"
style="width:5.67708in;height:4.84375in" />

*Figure 4 — One failing attempt and one passing retry. All arrows are
runtime-mediated calls; LLM \#2 and the validator never address each
other.*

- **Bounded:** retry.max_attempts (3) from config. Exceeded → status
  failed with the last verdict attached.

- **Escalation rule:** same error class twice → LLM \#1 stops retrying
  blindly and changes strategy: re-retrieve documentation for the
  failing instruction, or return a question. This rule is only possible
  because the session store remembers attempt 1.

- **Reproducible retries:** the retry prompt is the original prompt plus
  exactly two appended sections (PREVIOUS, FIX). Nothing else moves, so
  a retry differs from its predecessor in precisely the errors being
  fixed.

6 User-provided example programs

The caller may pass example_ls — a reference TP program the user wants
the result to resemble. Handling pipeline:

- **Store first.** The runtime persists it to the session store before
  any LLM sees it.

- **Syntax pre-check with early feedback.** At intake the validator runs
  over the example in syntax-only mode (grammar layer; symbols and
  limits are skipped — it comes from a foreign cell). If syntax fails,
  the unit returns feedback to the user immediately, before the loop
  starts: fix the example, or confirm it should be used only as a loose
  style reference.

- **Symbol report.** On a clean syntax pass, a second run produces the
  example report: which registers/IOs the example uses and which do not
  exist in this cell — the input to the mapping step.

- **LLM \#1 extracts and maps.** It reads example + report, extracts the
  reusable part (structure, ordering conventions, option usage) and maps
  foreign symbols to local ones via notes (example’s PR\[12\] ‘pick pos’
  → this cell’s PR\[5\] ‘conveyor pick’), asking via questions when a
  mapping is genuinely ambiguous.

- **Renderer inserts verbatim.** The EXAMPLE section carries the stored
  file text inserted by code — LLM \#1 never re-types it, because a
  model copying 40 lines will occasionally ‘fix’ one silently — with the
  instruction: match this structure and style; use only the registers in
  CELL.

- **Gates unchanged.** The generated output passes the same validator as
  always. The example influences style; it never bypasses correctness.

7 Configuration policy

| **Aspect**       | **Defaults**                                                                        | **Limits**                               |
|------------------|-------------------------------------------------------------------------------------|------------------------------------------|
| Examples         | speed, pick speed, termination, tool/frame numbers, settle times                    | max speed, max wait, envelope            |
| Owner            | developer baseline; user policy                                                     | developer only                           |
| Runtime override | yes — config_overrides per session (relayed by the main orchestrator from the user) | never                                    |
| Read by          | LLM \#1, renderer CELL section                                                      | validator layer 3, renderer CELL section |
| Reviewable       | get_defaults contract query; report echoes effective_defaults per program           | visible in reports, not editable         |

Rationale: defaults are policy the user legitimately owns, so they flow
through the front door like data. Limits are the safety floor the
validator enforces — a user-editable safety floor is not one, so limits
are part of the unit’s identity.

8 End-to-end trace (condensed)

**Prompt:** “Pick a part from the conveyor and place it on fixture A.
Close the gripper gently.”

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>[0] intake: in-scope; scan present -&gt; table_source=scan; no
questions</p>
<p>[1] request in; scan persisted (10:42)</p>
<p>[2] LLM #1: intent pick_and_place; table lookups:</p>
<p>conveyor-&gt;PR[5] (unique), fixture A-&gt;PR[8] (unique),
gripper-&gt;RO[1]</p>
<p>"gently" -&gt; settle 1.0s (default 0.5s); all params resolved, no
questions</p>
<p>[3] RAG: "J L PR motion RO ON WAIT pick place" -&gt; 4 chunks</p>
<p>[4] generate_program(params) -&gt; renderer -&gt; LLM #2 -&gt; draft
v1</p>
<p>[5] validator v1: FAIL</p>
<p>grammar line 8: "WAIT 1.0sec" expected WAIT &lt;t&gt;.00(sec)</p>
<p>symbol line 5,9: PR[10] not in table (known: 1,5,6,7,8,9)</p>
<p>[6] LLM #1 diagnosis (attempt 1/3): syntax slip + invented
register;</p>
<p>retry with errors attached, whitelist re-emphasized</p>
<p>[7] renderer: original prompt + PREVIOUS(v1) + FIX(2 errors) -&gt;
LLM #2 -&gt; v2</p>
<p>diff: PR[10]-&gt;PR[6] (2 lines), WAIT 1.00(sec)</p>
<p>[8] validator v2: PASS (14/14 lines)</p>
<p>[9] semantic review (always runs): advisory - no approach before
place; PR[7] available</p>
<p>[10] response: status ok, v2 inline + file_ref + report</p>
<p>(defaults applied, "gently"-&gt;1.0s, 1 retry, advisory)</p></td>
</tr>
</tbody>
</table>

If the user then asks “add the approach via PR\[7\]”, the caller sends a
new request with revision_of = v2; LLM \#1 patches one param and the
user reviews a two-line diff. The clarification branch works the same
way: with an ambiguous “fixture” (PR\[8\] and PR\[9\] both match), the
unit returns needs_clarification asking, in plain language, “Which
fixture should I place the part on — fixture A (PR\[8\]) or fixture B
(PR\[9\])?” instead of guessing — placing on the wrong fixture is a
physical-world error, not a guessable default.

9 Model deployment options

Both LLM roles sit behind narrow interfaces (a tool-calling chat loop; a
single-shot completion), so the model choice is configuration, not
architecture. On a 32 GB RTX 5090 workstation at Q4_K_M quantization, a
32B dense model costs ~19–20 GB, so two of them do not co-reside; the
practical configurations:

| **Configuration**          | **LLM \#1**                            | **LLM \#2**                   | **Notes**                                                                                                                                                                         |
|----------------------------|----------------------------------------|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Hybrid (recommended start) | Claude Sonnet (API)                    | Qwen2.5-Coder-32B local       | Frontier judgment where it matters (tool use, JSON discipline, low volume); local for the high-volume, privacy-relevant codegen. RAG + whitelist carry TP correctness either way. |
| Fully local, two models    | Qwen3-14B (~9 GB) or Qwen3-30B-A3B MoE | Qwen2.5-Coder-32B (~20 GB)    | 14B + 32B ≈ 29 GB — fits with KV headroom, tight. Serve via Ollama (simplest) or vLLM (JSON-schema guided decoding for LLM \#1’s structured output).                              |
| Fully local, one model     | Qwen3-Coder-30B-A3B                    | same model, different prompts | Simplest ops; viable because the validator gates correctness and the renderer constrains inputs. The factory-floor / no-internet configuration.                                   |

Note that the design keeps LLM \#1’s job inside a small model’s envelope
on purpose (short primer, no RAG context, structured output, audit-style
review) — so the fully-local rows above are credible, not aspirational.

The mock-LLM \#2 integration test (Software Architecture document,
tests/test_e2e_mock.py) runs unchanged against any backend — that is how
retry-convergence of a local model is benchmarked against the API before
committing.

Appendix A — reg_io_v1 interchange format

The wire format between the robot-class scanner (producer), the caller
(verbatim relay), and the unit’s runtime (the single parser). CSV was
chosen over JSON because the data is flat tabular, human-reviewable in a
spreadsheet (mapping review is a first-class activity in this design),
trivially producible by a dump loop, and diff-friendly for
cache-vs-fresh comparison.

Dialect and rules

- UTF-8, comma delimiter, double-quote quoting, header row required.
  Lines starting with \# are metadata, stripped before CSV parsing.
  Excel is a viewer for this file, not an editor.

- Metadata header: \# schema: reg_io_v1 (missing/foreign → level-A
  reject with a friendly message), \# cell_id, \# scanned_at (the
  timestamp of record — staleness math uses this, not the caller’s
  word).

- Five columns: type, index, comment, initialized, value. category
  (REG/IO) and direction (in/out) are deliberately NOT columns — both
  derive from type in the parser, so file and derivation can never
  contradict.

- Type enum v1: registers R, PR, SR, PL; IO DI, DO, RI, RO, UI, UO, SI,
  SO, GI, GO, AI, AO. Unknown types are kept and flagged, not rejected
  (forward compatibility).

- initialized: TRUE/FALSE for registers (an uninitialized PR shows \* on
  the pendant), ‘-’ for IO. Enables the ‘exists but not targetable’
  validator diagnosis.

- Dump ALL indexes, including rows with empty comments — the existence
  check needs the full index population, and ‘unlabeled’ is a different
  fact than ‘nonexistent’.

- value: free text, quoted; PR values carry a C: (Cartesian) or J:
  (Joint) prefix. The unit ignores this column in v1 — it rides along
  because the scanner gets it for free, and future consumers (envelope
  checks, RoboGuide layer) will want it. Dropping it later costs
  nothing; adding it later costs a robot-class change.

Example

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p># schema: reg_io_v1</p>
<p># cell_id: line3_fanuc1</p>
<p># scanned_at: 2026-07-04T10:42:00</p>
<p>type,index,comment,initialized,value</p>
<p>PR,1,home,TRUE,"J: 0.0,0.0,0.0,0.0,-90.0,0.0"</p>
<p>PR,5,conveyor pick,TRUE,"C: 512.3,-104.7,88.0,180.0,0.0,45.0"</p>
<p>PR,6,conveyor approach,TRUE,"C:
512.3,-104.7,188.0,180.0,0.0,45.0"</p>
<p>PR,8,fixture A place,TRUE,"C: 291.0,220.5,95.0,180.0,0.0,90.0"</p>
<p>PR,9,fixture B place,TRUE,"C: 291.0,-220.5,95.0,180.0,0.0,-90.0"</p>
<p>PR,10,,FALSE,</p>
<p>R,3,part counter,TRUE,12</p>
<p>SR,2,"recipe name, active",TRUE,PICKPLACE_A</p>
<p>DI,3,part present,-,ON</p>
<p>RO,1,gripper close,-,OFF</p>
<p>UI,5,,-,ON</p>
<p>F,12,cycle active flag,-,OFF</p></td>
</tr>
</tbody>
</table>

The example rows exercise the edge cases on purpose: an uninitialized,
uncommented PR (10); a comma inside a quoted comment (SR\[2\]);
unlabeled-but-real entries (UI\[5\]); and a type outside the v1 enum (F)
that a compliant parser keeps and flags.
