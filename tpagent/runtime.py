"""runtime.py -- handle(): the session loop (SOFTWARE.md 6.3).

LLM #1 decides strategy; this runtime enforces the mechanics: the retry
budget (retry.max_attempts), the same-error-class rule (a third
consecutive failure of the same class ends the run mechanically - the
old strategy cannot spend the rest of the budget), and the unconditional
edges - every draft goes to the Validator, every pass goes to the
LLM1-Audit, and only finalize() returns an ok Response. The auditor can
never block; only the human rejects.

Retrieval is a standard pre-generation step (DESIGN Figure 1): before
the first draft the runtime always retrieves documentation for the
task; LLM #1's rag_retrieve tool adds extra targeted look-ups.
Retries are reproducible BY CONSTRUCTION: the retry prompt reuses the
first attempt's TASK and NOTES unchanged and differs only in the
PREVIOUS+FIX sections (DESIGN 5) - with ONE sanctioned exception: an
explicit post-draft rag_retrieve refreshes DOCS, because DESIGN 5 names
"re-retrieve documentation for the failing instruction" as an
escalation strategy and that clause wins over full DOCS pinning.
(DESIGN 4.5's "chunks back to LLM #1" Out-row is NOT implemented - the
no-chunks-in-LLM1-context rule of 4.2/6.4 wins; LLM #1 sees counts.)
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict

from tpagent import llm1, llm2, renderer, review
from tpagent.config import static_config
from tpagent.contract import Report, Request, Response, validate_request
from tpagent.llm_client import LLMClient, LLMClientError
from tpagent.steps import StepsRecorder
from tpagent.stores import output as output_store
from tpagent.stores import session as session_store
from tpagent.stores import table as table_store
from tpagent.stores.table import SchemaError
from tpagent.validator import run as validate
from tpagent.validator.verdict import friendly

MAX_RAG_CALLS = 2

_BUDGET_MSG = ("I tried a few drafts but couldn't produce a program that "
               "passes every check. Please simplify the request or tell me "
               "more precisely which positions to use.")
_STRATEGY_MSG = ("I kept running into the same kind of problem while "
                 "drafting the program. Please simplify the request or name "
                 "the exact positions and signals to use.")
_PROTOCOL_MSG = ("I couldn't work out a plan for this request. Please "
                 "rephrase it or try again in a moment.")
_LOCAL_MSG = ("The local retrieval profile isn't set up in this deployment "
              "yet - please use the online profile.")


def _positions(program: str, table) -> dict:
    found = {}
    for m in re.finditer(r"\bPR\[(\d+)", program):
        entry = table.find("PR", int(m.group(1))) if table else None
        if entry and entry.comment and f"PR[{entry.index}]" not in found:
            found[f"PR[{entry.index}]"] = f"note '{entry.comment}'"
    return found


def _mandatory_advisories(source: str) -> list[str]:
    if source == "none":
        return ["No register and IO map is loaded for this cell, so I chose "
                "the register and IO indexes myself - please review the "
                "mapping before running the program."]
    if source == "default_table":
        return ["I used the built-in cell table - load your own registers "
                "and IO file on the page if your cell differs."]
    return []


def _failure_report(cfg: dict, source: str, table, attempts: int,
                    verdict) -> Report:
    """DESIGN 5 'Bounded': a failure carries the last verdict's story."""
    advisories = []
    if verdict is not None and verdict.errors:
        advisories.append(f"The last draft still had "
                          f"{len(verdict.errors)} problem(s):")
        advisories += [friendly(e) for e in verdict.errors[:5]]
        if len(verdict.errors) > 5:
            advisories.append(f"...and {len(verdict.errors) - 5} more - "
                              f"the full list is in the steps trace.")
    return Report(
        scan_used=(table.scanned_at or None) if table is not None else None,
        table_source=source,
        mapping_confidence="unverified" if source == "none" else "verified",
        effective_defaults=cfg.get("defaults", {}),
        retries=max(attempts - 1, 0),
        advisories=advisories)


def handle(req: Request, *, recorder: StepsRecorder | None = None,
           sb_client=None, transport=None, retrieve_fn=None) -> Response:
    recorder = recorder if recorder is not None else StepsRecorder()

    if (msg := validate_request(req)) is not None:          # level A
        return Response(status="rejected", reason=msg)
    if req.rag_backend == "local":          # accepted by contract, not built
        return Response(status="rejected", reason=_LOCAL_MSG)

    cfg = static_config()
    cfg = {**cfg, "defaults": {**cfg.get("defaults", {}),
                               **req.config_overrides}}
    limits = cfg.get("limits", {})
    max_attempts = int((cfg.get("retry") or {}).get("max_attempts", 3))

    try:
        table, source = table_store.materialize(req.cell_id, req.scan)
    except SchemaError as e:                # bad scan = level-A reject (2b)
        return Response(status="rejected", reason=str(e))

    check_table = None if source == "none" else table
    sess = session_store.open(req.cell_id, req.revision_of, client=sb_client)

    llm = LLMClient(recorder, transport=transport)

    if req.example_ls:                                      # early feedback
        rep = validate(req.example_ls, check_table, limits,
                       mode="syntax_report")
        sess.save_example(req.example_ls, rep.to_dict())
        if rep.verdict == "fail":
            lines = sorted({e.line for e in rep.errors})
            return Response(status="needs_clarification", questions=[
                f"The example program you attached has syntax problems on "
                f"line{'s' if len(lines) > 1 else ''} "
                f"{', '.join(map(str, lines))} - can you fix it or send a "
                f"clean export? I'd rather not copy its style blindly."])

    messages = llm1.initial_messages(
        req.prompt, table, source, cfg,
        example_attached=bool(req.example_ls), answers=req.answers)

    chunks: list[str] = []
    retrieval_note: str | None = None
    table_notes: list[str] = []   # user-requested table additions/refusals
    drafts: dict[str, str] = {}
    draft_errors: dict[str, list] = {}    # verdict errors per draft id
    attempts = 0
    rag_calls = 0
    last_sig = None
    same_class_streak = 0
    program = None
    draft_id = None
    pinned = None                 # first attempt's TASK+NOTES (DESIGN 5)
    params: dict = {}
    program_name = "PROGRAM"
    inferred: list = []
    verdict = None

    def retrieve(query: str) -> list[str]:
        nonlocal retrieval_note
        try:
            return [c.text for c in retrieve_fn(query, req.rag_backend)]
        except Exception:
            retrieval_note = (
                "I couldn't reach the documentation index for this run, so "
                "the program relies on the built-in syntax rules only.")
            return []

    try:
        for _ in range(2 * max_attempts + 3):
            action, raw = llm1.decide(llm, messages)
            messages.append({"role": "assistant", "content": raw})

            if action["action"] == "reject":
                if attempts:        # mid-loop bail-out is a failure, and
                    return Response(  # LLM #1 jargon never reaches the user
                        status="failed", reason=_BUDGET_MSG,
                        report=_failure_report(cfg, source, table,
                                               attempts, verdict))
                return Response(status="rejected",
                                reason=action.get("reason") or _PROTOCOL_MSG)

            if action["action"] == "ask_user":
                questions = [str(q) for q in action.get("questions") or []]
                if not questions:
                    questions = ["Can you tell me more about what the "
                                 "program should do?"]
                sess.set_pending_question(questions[0])
                return Response(status="needs_clarification",
                                questions=questions)

            if action["action"] == "rag_retrieve":
                got = 0
                if retrieve_fn is not None and rag_calls < MAX_RAG_CALLS:
                    rag_calls += 1
                    fresh = retrieve(str(action.get("query", "")))
                    if fresh:
                        chunks = fresh
                        got = len(fresh)
                messages.append({"role": "user", "content": json.dumps(
                    {"tool": "rag_retrieve", "retrieved": got})})
                continue

            # generate_program
            if attempts >= max_attempts:
                return Response(status="failed", reason=_BUDGET_MSG,
                                report=_failure_report(cfg, source, table,
                                                       attempts, verdict))
            attempts += 1
            inferred.extend(action.get("inferred") or [])

            if pinned is None:                  # first attempt: fix the task
                params = action.get("params") or {}
                program_name = str(action.get("program_name") or "PROGRAM")

                # user-requested table additions (owner decision): the
                # runtime merges NEW entries into the working table -
                # add-only, existing indexes never overridden, nothing
                # written back to a file. The renderer and validator see
                # the merged table from here on; the report says so.
                adds = action.get("table_add") or []
                if adds and check_table is not None:
                    table, added, refused = \
                        table_store.with_additions(table, adds)
                    check_table = table
                    for e in added:
                        note = f" '{e.comment}'" if e.comment else ""
                        table_notes.append(
                            f"I added {e.type}[{e.index}]{note} to the "
                            f"working table at your request. It isn't "
                            f"taught yet - teach it on the pendant, and "
                            f"add the row to your table file to keep it "
                            f"for future runs.")
                        sess.log_decision(f"table_add {e.type}[{e.index}]")
                    table_notes.extend(refused)

                if retrieve_fn is not None and not chunks:
                    # mandatory pre-generation retrieval (DESIGN flow step 4)
                    query = str(params.get("task")
                                or req.prompt.splitlines()[-1])[:300]
                    chunks = retrieve(query)
                pinned = {
                    "params": params,
                    "program_name": program_name,
                    "notes": [str(n) for n in action.get("notes") or []],
                }

            base = action.get("base_draft")
            if base is not None:
                base = base if base in drafts else draft_id
            base_errors = (draft_errors.get(base, [])
                           if base is not None else [])
            args = renderer.GenerateArgs(
                **pinned, chunks=list(chunks),   # DOCS refresh = escalation
                base_draft=base, errors=base_errors,
                fix_guidance=action.get("fix_guidance"))
            rsess = renderer.RenderSession(example_ls=req.example_ls,
                                           drafts=drafts)
            prompt_text = renderer.render(cfg, table, rsess, args)

            draft = llm2.generate(prompt_text, llm)
            draft_id = sess.save_draft(draft.text)
            drafts[draft_id] = draft.text

            verdict = validate(draft.text, check_table, limits)
            draft_errors[draft_id] = [e.to_dict() for e in verdict.errors]
            sess.save_verdict(draft_id, verdict.verdict,
                              errors=[e.to_dict() for e in verdict.errors],
                              stats={**verdict.stats,
                                     "warnings": verdict.warnings})
            if verdict.verdict == "pass":
                program = draft.text
                break

            # same-error-class signature: layer + the concrete offender, so
            # partial progress (one existence error fixed, one left) resets
            # the streak while a genuinely stuck error still stops the run
            sig = tuple(sorted({(e.layer, e.ref or e.found or e.message
                                 or "") for e in verdict.errors}))
            same_class_streak = same_class_streak + 1 if sig == last_sig \
                else 1
            last_sig = sig
            if same_class_streak >= 3:      # mechanical stop: old strategy
                return Response(status="failed", reason=_STRATEGY_MSG,
                                report=_failure_report(cfg, source, table,
                                                       attempts, verdict))
            messages.append({"role": "user", "content": json.dumps({
                "draft_id": draft_id,
                "validator_errors": [e.to_dict()
                                     for e in verdict.errors[:10]],
                "attempt": attempts,
                "attempts_left": max_attempts - attempts,
                "escalation": same_class_streak >= 2}, sort_keys=True)})

        if program is None:                 # loop cap: honest wording either way
            return Response(status="failed",
                            reason=_BUDGET_MSG if attempts else _PROTOCOL_MSG,
                            report=_failure_report(cfg, source, table,
                                                   attempts, verdict))

        try:                                # audit ALWAYS; can never block
            advisories = review.semantic_audit(
                program, params, table, llm,
                effective_defaults=cfg.get("defaults", {}))
        except (LLMClientError, llm1.ProtocolError):
            advisories = ["The automatic review wasn't available this time "
                          "- please give the program a quick manual look."]

    except llm1.ProtocolError:
        return Response(status="failed", reason=_PROTOCOL_MSG,
                        report=_failure_report(cfg, source, table,
                                               attempts, verdict))
    except LLMClientError as e:
        return Response(status="failed", reason=str(e),
                        report=_failure_report(cfg, source, table,
                                               attempts, verdict))

    report = Report(
        scan_used=table.scanned_at or None,
        table_source=source,
        mapping_confidence="unverified" if source == "none" else "verified",
        effective_defaults=cfg.get("defaults", {}),
        positions=_positions(program, table),
        inferred=inferred,
        retries=attempts - 1,
        advisories=_mandatory_advisories(source) + table_notes
        + ([retrieval_note] if retrieval_note else [])
        + verdict.warnings + advisories)
    file_ref = output_store.save(sess.id, draft_id, program_name, program,
                                 asdict(report), client=sb_client)
    sess.log_decision(f"delivered {draft_id} after {attempts} attempt(s)")
    return Response(status="ok", draft_id=draft_id, program_ls=program,
                    file_ref=file_ref, report=report)
