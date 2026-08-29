**TP Creator Agent**

**Software Architecture & Design**

*From the frozen v1.3 architecture to code: processes, classes, module
contracts, and communication*

Version 2.1 · July 2026 · synced to Design Document v1.3 · Python 3.11+
/ Windows first

**Contents**

**0 Revision notes**

**1 Scope and reading guide**

**2 High-level architecture: processes and boundaries**

**3 Repository layout**

**4 Layer rules and dependencies**

**5 Core data model (classes)**

**6 Component specifications**

> 6.1 contract.py — types + level-A gate
>
> 6.2 reg_io.py — the single CSV parser
>
> 6.3 runtime.py — session loop
>
> 6.4 llm1.py + review.py + prompts/
>
> 6.5 renderer.py + templates/
>
> 6.6 llm2.py — backends
>
> 6.7 validator/ — three layers
>
> 6.8 rag/ — profiles
>
> 6.9 stores/ — table, session, output
>
> 6.10 apps/ — the tier-2 caller

**7 Communication: one contract call end to end**

**8 Data on disk**

**9 Configuration and environments**

**10 Testing strategy**

**11 Prototype-to-target migration map**

0 Revision notes

v2.1

- **Figure 1 corrected after review.** The unit-process view previously
  chained its components vertically, which wrongly read as a pipeline
  ending in ‘stores + RAG client’. It now uses a hub topology matching
  the stated rule (the runtime talks to everything): the RAG client is
  its own component used pre-generation, and the stores are drawn last
  only as inventory — with the output store explicitly noted as where
  the final .ls lands after the validator pass AND the LLM \#1 audit.

v2.0

Rewritten against Design Document v1.3. Everything the design added
since the first software sketch is reflected in code terms: the
runtime’s level-A gate and the two-level rejection model; reg_io_v1 as
the scan wire format with the single-parser rule (a dedicated reg_io.py
module); the table-source hierarchy with cache and default_index_map in
stores/table.py; the answers relaxation ({reply: raw text});
rag_config.yaml as the unit-owned home of retrieval/chunking parameters
with one index per backend profile; the mandatory LLM \#1 audit turn;
the example syntax pre-check (validator mode="syntax_report"); and the
tier-2 caller (apps/) with its envelope-assembly logic, for which a
working reference implementation already exists and validated the
interfaces specified here.

1 Scope and reading guide

The Design Document answers what the system does and why; this document
answers how it is built: which processes exist, which modules live in
them, the exact interfaces between modules, and what travels across
every boundary. Sections 2–5 are top-down architecture (processes →
repository → layers → data model); Section 6 is the per-component
reference with inputs, outputs and forbidden behaviors; Sections 7–11
cover communication, persistence, configuration, testing and the
migration from the existing prototype.

**One sentence to keep while reading:** intelligence (llm1, llm2) and
correctness (validator) never import each other; the runtime is the only
module that talks to everything; the caller talks only to contract.py.
Every interface below exists to preserve those three rules.

2 High-level architecture: processes and boundaries

<img src="media/e97734327270ae3ff29139fc7bf5647706e1a732.png"
style="width:5.67708in;height:5.17708in" />

*Figure 1 — Two processes plus external services. Inside the unit the
topology is a hub, not a pipeline: the runtime calls each component in
the flow order defined by Design Doc Figure 1 (RAG retrieval happens
BEFORE generation; the output store is written LAST, after validator
pass + LLM \#1 audit). The contract boundary carries only
Request/Response JSON — direct call in v0, HTTP later. External services
are selected per rag_backend / TP_LLM\* profile.*

Three kinds of boundaries, each with a fixed payload:

| **Boundary**                 | **Payload crossing it**                                                                                                               | **Direction** | **Notes**                                                                                           |
|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|---------------|-----------------------------------------------------------------------------------------------------|
| caller ↔ unit                | Request JSON (prompt verbatim, reg_io_v1 CSV verbatim, overrides, flags) / Response JSON (status, program, report, questions, reason) | both          | The only coupling between processes. The caller never parses the CSV and never sees unit internals. |
| unit ↔ LLM backends          | rendered prompt → completion (LLM \#2); tool-loop messages → structured JSON / tool calls (LLM \#1)                                   | both          | Vendor SDKs are imported only inside llm1.py / llm2.py; swapping backends is an env change.         |
| unit ↔ embedding + vector DB | query string → embedding → top-k chunks                                                                                               | both          | Profile chosen by Request.rag_backend; each profile has its own index (hard invariant).             |

The caller process is deliberately brainless (Design Doc Section 2d):
gui.py is a thin tkinter skin over app_state.py, which holds exactly two
pieces of conversation state (last draft, pending question) plus
configuration, and assembles the envelope mechanically. console.py is
the same brain on stdin. Both import nothing from tpagent/ except
contract.py — which makes the caller itself the boundary-enforcement
test.

3 Repository layout

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>tp-creator/</p>
<p>+-- CLAUDE.md # agent rules for Claude Code sessions</p>
<p>+-- config/</p>
<p>| +-- static_config.yaml # defaults + limits + retry + max_table_age
+ default_index_map</p>
<p>| +-- rag_config.yaml # unit-owned: profiles (online|local), index +
retrieve params</p>
<p>+-- tpagent/ # THE UNIT (Design Doc Figure 1)</p>
<p>| +-- contract.py # Request/Response/Report + level-A
validate_request()</p>
<p>| +-- reg_io.py # reg_io_v1 parser -- the single parser in the
system</p>
<p>| +-- runtime.py # handle(): session loop, budgets, finalize</p>
<p>| +-- llm1.py # orchestrator tool loop (intake, params, retries)</p>
<p>| +-- review.py # the audit turn (same LLM #1 instance)</p>
<p>| +-- prompts/llm1_system.md # domain primer + checklists +
few-shots</p>
<p>| +-- renderer.py # deterministic prompt assembly</p>
<p>| +-- templates/ # system.j2 cell.j2 docs.j2 example.j2 task.j2
notes.j2 retry.j2</p>
<p>| +-- llm2.py # single-shot codegen; backends
anthropic|ollama|mock</p>
<p>| +-- rag/</p>
<p>| | +-- index.py # offline: chunk + embed + write collection (per
profile)</p>
<p>| | +-- retrieve.py # online: embed query + top-k (asserts index
model)</p>
<p>| +-- validator/</p>
<p>| | +-- grammar.py # FAMILIES dict + token walks + bounded
suggestions</p>
<p>| | +-- existence.py # symbol extraction vs table keys + initialized
diagnosis</p>
<p>| | +-- limits.py # numeric checks vs static config</p>
<p>| | +-- verdict.py # Verdict/Err dataclasses; run(text, table,
limits, mode)</p>
<p>| +-- stores/</p>
<p>| +-- table.py # 2c source hierarchy: scan &gt; cache &gt;
default_map</p>
<p>| +-- session.py # drafts, verdicts, params, decisions, example</p>
<p>| +-- output.py # final .ls + report.json</p>
<p>+-- apps/ # THE CALLER (tier 2) -- outside the unit</p>
<p>| +-- app_state.py # config IO + conversation state + envelope
assembly</p>
<p>| +-- gui.py # tkinter: Chat | Program | Report | Settings</p>
<p>| +-- console.py # stdin shell</p>
<p>| +-- app_config.yaml # caller-owned configuration</p>
<p>+-- corpus/ # TP manual sections + curated .ls examples</p>
<p>+-- sessions/ out/ chroma/ # runtime data (gitignored)</p>
<p>+-- tests/ # see Section 10</p>
<p>+-- cli.py # request | chat | validate | index subcommands</p></td>
</tr>
</tbody>
</table>

4 Layer rules and dependencies

<img src="media/c43c89d9fa2f4f07f1db1b750092a77c8ff1506c.png"
style="width:5.67708in;height:5.01042in" />

*Figure 2 — Imports point downward only. apps/ sees nothing below
contract.py; runtime.py is the sole module importing from every layer;
llm1/llm2/validator never import each other across branches; reg_io.py
lives with the stores because the table store is its only caller.*

| **Rule**                                           | **Enforced by**                                           | **Why it exists**                                                             |
|----------------------------------------------------|-----------------------------------------------------------|-------------------------------------------------------------------------------|
| apps/ imports contract.py only                     | code review + the fact that apps/ runs against HTTP later | keeps the caller replaceable (tier 3) and the unit boundary honest            |
| intelligence ↮ correctness (llm1/llm2 ↮ validator) | package structure; no shared modules except dataclasses   | the validator must be testable with zero LLMs and immune to model blind spots |
| reg_io.py has one caller: stores/table.py          | import audit in CI (simple grep test)                     | single-parser rule — derived fields computed exactly once                     |
| vendor SDKs only inside llm1.py, llm2.py, rag/     | import audit in CI                                        | model/backend swap = env change, not refactor                                 |
| templates contain no logic beyond presence checks  | renderer snapshot tests                                   | determinism: same inputs ⇒ byte-identical prompt                              |

5 Core data model (classes)

<img src="media/297fb9d4ff25f09b1bbba7e4f3c6e7f145f35b51.png"
style="width:5.67708in;height:5.09375in" />

*Figure 3 — The nine load-bearing dataclasses. Response owns one Report;
RegIOTable owns Entry rows (with category/direction computed at parse
time, never stored); Session owns Drafts and the table reference;
Verdict owns Err records whose layer values are grammar \| existence \|
limits.*

Everything else in the system is behavior over these types. Two
deliberate asymmetries: Entry carries the derived category/direction so
no consumer ever re-implements the FANUC type decoding; and Err.expected
is either a token set (grammar walk position) or a form string (pattern
instructions like WAIT), because those are the two shapes “what was
legal here” actually takes.

6 Component specifications

Format per component: role · public interface (signatures) · in / out ·
never. Signatures marked (proto) exist verbatim in the reference
implementation and survived the conversation tests; the rest are
specified here.

6.1 contract.py — types + level-A gate

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>Status = Literal["ok", "needs_clarification", "rejected",
"failed"]</p>
<p>OVERRIDABLE_DEFAULTS =
{"speed","pick_speed","term","utool","uframe","gripper_settle_sec"}</p>
<p>LIMIT_KEYS = {"max_speed_mmsec","max_wait_sec"}</p>
<p>@dataclass Request(prompt, cell_id, scan: str|None,
config_overrides={},</p>
<p>rag_backend="online", example_ls=None, revision_of=None,
answers={})</p>
<p>@dataclass Report(scan_used, table_source, mapping_confidence,
effective_defaults,</p>
<p>positions, inferred, retries, advisories)</p>
<p>@dataclass Response(status, draft_id, program_ls, file_ref, report,
questions, reason)</p>
<p>def validate_request(req) -&gt; str | None # (proto) level-A:
friendly message or pass</p></td>
</tr>
</tbody>
</table>

|                |                                                                                                                                                                                                                                   |
|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| In / out       | JSON strings at both ends (to_json/from_json); dataclasses everywhere inside.                                                                                                                                                     |
| Level-A checks | empty prompt; missing cell_id; overrides touching LIMIT_KEYS; unknown override keys; invalid rag_backend. Each failure returns a pre-written friendly sentence (Design Doc Section 2b) — the runtime wraps it as status=rejected. |
| Never          | Reasons about content. Anything requiring judgment is not a level-A check by definition.                                                                                                                                          |

6.2 reg_io.py — the single CSV parser

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>class SchemaError(ValueError) # -&gt; level-A reject upstream</p>
<p>def parse_reg_io_csv(raw: str) -&gt; RegIOTable # (proto)</p>
<p># - strips '#' metadata lines; requires schema=reg_io_v1, cell_id,
scanned_at</p>
<p># - csv.DictReader over the body; required columns
type,index,comment,initialized,value</p>
<p># - classify(type) -&gt; category REG|IO|UNKNOWN, direction
in|out|None (computed, not stored)</p>
<p># - unknown types / bad rows -&gt; table.flags (kept, flagged, never
rejected)</p>
<p>RegIOTable.find(type,index) / by_note(needle,type?) / key_set() #
(proto)</p></td>
</tr>
</tbody>
</table>

**by_note filters out initialized=False entries** — an uninitialized
register is a valid existence fact but an invalid inference target,
which is exactly the split the design’s ‘exists but uninitialized’
diagnosis needs. Comment matching trims the trailing whitespace FANUC
pads comments with.

6.3 runtime.py — session loop

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>def handle(req: Request) -&gt; Response:</p>
<p>if (msg := contract.validate_request(req)): return reject(msg) #
level A</p>
<p>table, source = stores.table.materialize(req.cell_id, req.scan) # 2c
hierarchy</p>
<p>sess = stores.session.open(req.cell_id, req.revision_of)</p>
<p>if req.example_ls:</p>
<p>rep = validator.run(req.example_ls, table, cfg.limits,
mode="syntax_report")</p>
<p>sess.save_example(req.example_ls, rep)</p>
<p>if rep.verdict == "fail": # early feedback</p>
<p>return needs_clarification(friendly_syntax_feedback(rep))</p>
<p>loop = llm1.ToolLoop(cfg_effective(req), table, sess) # level B
inside</p>
<p>for turn in loop:</p>
<p>if turn.tool == "rag_retrieve":</p>
<p>turn.result = rag.retrieve(turn.query, profile=req.rag_backend)</p>
<p>if turn.tool == "generate_program":</p>
<p>prompt = renderer.render(cfg, table, sess, turn.args)</p>
<p>draft = llm2.generate(prompt); sess.save_draft(draft)</p>
<p>turn.result = validator.run(draft.text, table, cfg.limits)</p>
<p>sess.save_verdict(turn.result)</p>
<p>budget.count(turn.result) # max_attempts + same-class-twice
escalation</p>
<p>if loop.outcome.ok:</p>
<p>advisories = review.semantic_audit(loop.program, loop.params, table)
# ALWAYS</p>
<p>return finalize(loop.outcome, sess) # ok | needs_clarification |
rejected | failed</p></td>
</tr>
</tbody>
</table>

|         |                                                                                                                                                                                                           |
|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| In      | Request; tool intents from LLM \#1; drafts; verdicts.                                                                                                                                                     |
| Out     | Response; every file under sessions/ and out/ (sole writer of stores).                                                                                                                                    |
| Budgets | retry.max_attempts from static config, enforced here in code; the same-error-class-twice counter is mechanical (LLM \#1 chooses the new strategy, runtime forbids spending more attempts on the old one). |
| Never   | Decides scope or fills gaps (level B belongs to LLM \#1); parses prompts; edits config.                                                                                                                   |

6.4 llm1.py + review.py + prompts/

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>class ToolLoop:</p>
<p>"""Tool-use loop. Tools: rag_retrieve(query),</p>
<p>generate_program(params, program_name, notes, base_draft,
errors),</p>
<p>ask_user(questions) -&gt; loop terminal, becomes
needs_clarification.</p>
<p>Structured output only: every turn is a tool call or a final
JSON;</p>
<p>free text is a protocol error the runtime rejects and retries
once."""</p>
<p>def review.semantic_audit(program, params, table) -&gt; list[str] #
advisories, friendly</p></td>
</tr>
</tbody>
</table>

- **prompts/llm1_system.md** is the whole of LLM \#1’s TP knowledge: the
  ~2-page literacy primer, per-intent parameter checklists, the gap
  policy (config default / note inference / ask — never invent
  positions), the user-facing language rule with examples, and 2
  few-shot prompt→params extractions. No RAG chunks ever enter LLM \#1’s
  context — they route to the renderer — which is what keeps the
  small-local-model plan credible.

- **Answers handling:** on a call with answers={reply: text}, the open
  question is read from the session store and the raw reply is
  interpreted against it (the reference implementation demonstrated
  fixture-letter and PR-index replies). Structured {key: value} bypasses
  interpretation.

- **review.py is the same client, different turn:** fresh audit prompt
  (program + params + table notes), output constrained to an advisories
  list. It cannot block — the runtime treats its output as report
  content only.

6.5 renderer.py + templates/

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>def render(cfg, table, sess, args: GenerateArgs) -&gt; str</p>
<p># fixed order: SYSTEM -&gt; CELL(cfg, table verbatim) -&gt;
DOCS(args.chunks)</p>
<p># -&gt; EXAMPLE(sess, verbatim)? -&gt; TASK(args.params) -&gt;
NOTES(name, comments)</p>
<p># -&gt; PREVIOUS+FIX(sess.draft(args.base_draft), args.errors)? retry
only</p>
<p># byte-identical for identical inputs (snapshot-tested)</p></td>
</tr>
</tbody>
</table>

**No-leakage in code terms:** render() takes the table and config
objects from the stores, never from LLM \#1’s output — GenerateArgs
simply has no field that could carry them. The whitelist reaching LLM
\#2 is the store’s bytes.

6.6 llm2.py — backends

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>def generate(prompt: str) -&gt; Draft</p>
<p># backend by env TP_LLM2 = anthropic:&lt;model&gt; |
ollama:&lt;model&gt; | mock:&lt;path&gt;</p>
<p># post-processing (code): strip markdown fences, normalize CRLF,</p>
<p># require a /PROG ... /END envelope (else -&gt; synthetic grammar
error, not a crash)</p></td>
</tr>
</tbody>
</table>

6.7 validator/ — three layers

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>def run(text, table, limits, mode="gate") -&gt; Verdict</p>
<p># mode="gate": grammar + existence + limits (drafts)</p>
<p># mode="syntax_report": grammar only (example pre-check)</p>
<p># grammar.py: FAMILIES dict keyed by leading token; token walk per
family;</p>
<p># suggestion iff edit_distance&lt;=2 AND unique candidate; grammar
layer only</p>
<p># existence.py: regex-extract PR/R/SR/PL/DI/DO/RI/RO/... refs; three
outcomes:</p>
<p># ok | not_in_table (known set attached) | exists_uninitialized</p>
<p># ("PR[10] exists but is uninitialized and unlabeled - did you mean
PR[6]?")</p>
<p># limits.py: speeds, waits vs static config</p></td>
</tr>
</tbody>
</table>

existence.py consumes RegIOTable.key_set() plus the initialized flags —
read-only, no note interpretation, per the correctness/existence split.
The two symbol outcomes produce different Err payloads because LLM \#1
repairs them differently (wrong index vs. missing setup).

6.8 rag/ — profiles

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p># rag_config.yaml (unit-owned): profiles.online /
profiles.local</p>
<p># each: embedding {provider, model}, vector_db {provider,
index/collection}</p>
<p># index: chunk_strategy logical|fixed, chunk_size_chars,
chunk_overlap_chars</p>
<p># retrieve: top_k, score_threshold, max_context_chars</p>
<p>def retrieve(query, profile) -&gt; list[Chunk]</p>
<p># asserts collection.embedding_model == profile.embedding.model (hard
invariant)</p>
<p># truncates the chunk list at max_context_chars before
returning</p></td>
</tr>
</tbody>
</table>

6.9 stores/ — table, session, output

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>table.materialize(cell_id, scan_csv|None) -&gt; (RegIOTable,
source)</p>
<p># 1 scan: parse_reg_io_csv; persist CSV as cache/&lt;cell_id&gt;.csv;
source="scan"</p>
<p># 2 cache: last CSV for the SAME cell_id, age(scanned_at) &lt;=
max_table_age; "cache(&lt;age&gt;)"</p>
<p># 3 defaults: static_config.default_index_map -&gt; synthetic table;
"default_map"</p>
<p># (mapping_confidence="unverified" + mandatory advisory)</p>
<p># else: raise NoTableSource -&gt; friendly needs_clarification
upstream</p>
<p>session: drafts/ verdicts/ params_history decisions.log
example(.ls,_report)</p>
<p>output: out/&lt;sid&gt;/&lt;PROGRAM&gt;_vN.ls + report.json</p></td>
</tr>
</tbody>
</table>

6.10 apps/ — the tier-2 caller

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>AppState.load() # (proto) reads app_config.yaml, auto-loads
scan</p>
<p>AppState.build_request(text) -&gt; Request # (proto) the mechanical
envelope:</p>
<p># prompt verbatim; scan once-then-None; overrides = user-CHANGED
values only;</p>
<p># revision_of = last draft unless "New program"; answers={reply:text}
iff pending</p>
<p>AppState.apply_response(req, resp) # (proto) updates the two state
variables</p>
<p>AppState.set_default(key, value) # (proto) raises on non-overridable
keys (limits</p>
<p># are blocked at the GUI layer AND at level A)</p>
<p>gui.py: Chat | Program | Report | Settings; post_to_unit() switches
direct|http</p></td>
</tr>
</tbody>
</table>

The Settings tab edits both configs but labels their ownership:
app_config.yaml values become Request fields; rag_config.yaml edits are
a developer convenience over the unit’s file, with the re-index warning
shown whenever index/embedding values change.

7 Communication: one contract call end to end

<img src="media/a2fac6b3b127715bc91ddb0fcaa0cff9e68e493f.png"
style="width:5.67708in;height:5.67708in" />

*Figure 4 — Class-level sequence of a contract call, including the
intake clarification round-trip (a full new Request), the bounded retry
band, and the mandatory audit turn. ‘Tools’ is the runtime-mediated
renderer + LLM \#2 + validator chain; LLM \#2 and the validator never
address each other.*

| **Hop**                       | **Carries**                                                               | **Format**                              |
|-------------------------------|---------------------------------------------------------------------------|-----------------------------------------|
| Caller → Runtime              | Request                                                                   | JSON (direct call v0 / HTTP POST later) |
| Runtime → LLM \#1             | intake context: prompt, parsed table, effective defaults, session history | messages + tool schemas                 |
| LLM \#1 → Runtime             | tool calls / final JSON: params, name, notes, questions, fix guidance     | structured JSON only                    |
| Runtime → LLM \#2             | rendered prompt (Design Doc Figure 2)                                     | single completion request               |
| Runtime → Validator           | draft text + table key-set/initialized + limits                           | function call                           |
| Validator → Runtime → LLM \#1 | Verdict (Err\[\] with layer, position, expected set, optional suggestion) | dataclass / JSON                        |
| Runtime → Caller              | Response (one of the four statuses; strings user-ready)                   | JSON                                    |

8 Data on disk

| **Path**                                                    | **Writer**                          | **Readers**                                | **Notes**                                                     |
|-------------------------------------------------------------|-------------------------------------|--------------------------------------------|---------------------------------------------------------------|
| config/static_config.yaml                                   | developer (Git)                     | runtime, renderer, validator, stores.table | defaults + limits + retry + max_table_age + default_index_map |
| config/rag_config.yaml                                      | developer (GUI edit as convenience) | rag/index, rag/retrieve                    | profiles; one index per profile                               |
| cache/\<cell_id\>.csv                                       | stores.table                        | stores.table                               | the verbatim last scan; staleness from its own scanned_at     |
| sessions/\<sid\>/reg_io_table.json                          | stores.table                        | llm1, renderer, validator, review          | parsed table with derived fields                              |
| sessions/\<sid\>/drafts/ verdicts/ decisions.log example.\* | runtime (via session store)         | llm1 retry context, diffs, audit           | append-only trail                                             |
| out/\<sid\>/\<PROG\>\_vN.ls + report.json                   | stores.output                       | caller / human review                      | the deliverables                                              |

9 Configuration and environments

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p># .env (gitignored)</p>
<p>ANTHROPIC_API_KEY=...</p>
<p>TP_LLM1=anthropic:claude-sonnet-4-6 # or ollama:qwen3-14b (structured
output enforced)</p>
<p>TP_LLM2=ollama:qwen2.5-coder:32b # or anthropic:... /
mock:tests/fixtures/v1.ls</p>
<p>EMBED_GATEWAY_URL=... EMBED_GATEWAY_KEY=... # online profile</p>
<p>PINECONE_API_KEY=... # online profile</p>
<p>OLLAMA_URL=http://127.0.0.1:11434 # local profile</p>
<p>CHROMA_PATH=./chroma # local NTFS path, not a synced folder</p></td>
</tr>
</tbody>
</table>

| **File**           | **Owner**      | **Consumed by**                                           |
|--------------------|----------------|-----------------------------------------------------------|
| app_config.yaml    | caller         | apps/ only — becomes Request fields                       |
| static_config.yaml | unit developer | runtime, renderer CELL, validator limits, table defaults  |
| rag_config.yaml    | unit developer | rag/ only — selected by Request.rag_backend               |
| .env               | deployment     | llm1.py, llm2.py, rag/ (the only vendor-touching modules) |

10 Testing strategy

- **reg_io parser tests.** The Appendix-A template is the fixture: 25
  rows exercising the uninitialized/uncommented PR, quoted comma,
  unlabeled-but-real entries, unknown type kept-and-flagged, metadata
  extraction, and the SchemaError paths (missing
  schema/cell_id/scanned_at).

- **Validator table-driven tests (no LLM, no network).** (line, expected
  Err) pairs covering the four hallucination classes, the WAIT
  suggestion, the exists-but-uninitialized diagnosis,
  mode="syntax_report" skipping existence/limits, and 15 known-good
  lines producing zero errors.

- **Renderer snapshots.** First-attempt and retry prompts,
  byte-identical; a snapshot diff is a deliberate template change or a
  bug, never noise.

- **Retrieval gate (human-judged).** Known queries must surface their
  obvious chunks in top-k per profile before any generation is wired.

- **Conversation e2e with mock LLM \#2.** The scripted dialogue that
  already runs against the prototype: ambiguity → friendly question →
  raw-text answer → ok with override visible in the .ls → revision
  adding the approach → off-scope reject → new task. Assertions on
  envelope mechanics too: scan relayed once, overrides
  only-when-changed, inference persisting across the clarification
  round-trip (a real bug this test caught), limits blocked at both
  walls.

- **Import audits in CI.** grep-level tests for the Section-4 rules:
  apps/ imports contract only; no vendor SDK outside llm1/llm2/rag;
  reg_io imported only by stores.table.

- **Live smoke (manual gate).** One real request per backend; compare
  retries-to-pass across backends on the same request before adopting.

11 Prototype-to-target migration map

A working prototype of the caller side and the conversation protocol
exists (tp_creator_console). It is not throwaway — most files move
verbatim; the mock dissolves into the real components it stood in for:

| **Prototype file**                 | **Target location** | **Fate**                                                                                                                                                                                                                    |
|------------------------------------|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| contract.py                        | tpagent/contract.py | moves as-is (already level-A complete)                                                                                                                                                                                      |
| reg_io.py                          | tpagent/reg_io.py   | moves as-is                                                                                                                                                                                                                 |
| app_state.py / gui.py / console.py | apps/               | move as-is; post_to_unit() gains the HTTP branch it already stubs                                                                                                                                                           |
| app_config.yaml / rag_config.yaml  | apps/ and config/   | move as-is (ownership already correct)                                                                                                                                                                                      |
| mock_unit.py                       | dissolves           | level-A + session persistence → runtime.py; note-matching intake → LLM \#1 + prompts; \_emit() → tests/fixtures as the canonical known-good program; the whole file survives as the mock backend for conversation e2e tests |

Build order stays as the roadmap defined: deterministic core (validator,
renderer, reg_io already done) before intelligence, mock end-to-end
before live tokens, and the caller — already built — waiting at the
contract the whole time.
