"""runtime.py -- handle(): the session loop (SOFTWARE.md 6.3).

LLM #1 decides strategy; this runtime enforces the mechanics: the retry
budget (retry.max_attempts), the same-error-class-twice escalation, and
the unconditional edges - every draft goes to the Validator, every pass
goes to the LLM1-Audit, and only finalize() returns a Response. The
auditor can never block; only the human rejects.
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
from tpagent.validator import run as validate

MAX_RAG_CALLS = 2

_BUDGET_MSG = ("I tried a few drafts but couldn't produce a program that "
               "passes every check. Please simplify the request or tell me "
               "more precisely which positions to use.")
_PROTOCOL_MSG = ("I couldn't work out a plan for this request. Please "
                 "rephrase it or try again in a moment.")


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
    if source.startswith("cache"):
        age = source[source.find("(") + 1:source.find(")")]
        return [f"The register map comes from a scan cached {age} ago - "
                f"re-scan if the cell has changed since."]
    return []


def handle(req: Request, *, recorder: StepsRecorder | None = None,
           sb_client=None, transport=None, retrieve_fn=None) -> Response:
    recorder = recorder if recorder is not None else StepsRecorder()

    if (msg := validate_request(req)) is not None:          # level A
        return Response(status="rejected", reason=msg)

    cfg = static_config()
    cfg = {**cfg, "defaults": {**cfg.get("defaults", {}),
                               **req.config_overrides}}
    limits = cfg.get("limits", {})
    max_attempts = int((cfg.get("retry") or {}).get("max_attempts", 3))

    table, source = table_store.materialize(req.cell_id, req.scan,
                                            client=sb_client)
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
    drafts: dict[str, str] = {}
    attempts = 0
    rag_calls = 0
    last_sig = None
    escalated = False
    program = None
    draft_id = None
    params: dict = {}
    program_name = "PROGRAM"
    inferred: list = []

    try:
        for _ in range(2 * max_attempts + 3):
            action, raw = llm1.decide(llm, messages)
            messages.append({"role": "assistant", "content": raw})

            if action["action"] == "reject":
                if attempts:            # mid-loop bail-out is a failure, and
                    return Response(    # LLM #1's jargon never reaches the user
                        status="failed", reason=_BUDGET_MSG)
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
                    chunks = [c.text for c in
                              retrieve_fn(str(action.get("query", "")))]
                    got = len(chunks)
                messages.append({"role": "user", "content": json.dumps(
                    {"tool": "rag_retrieve", "retrieved": got})})
                continue

            # generate_program
            if attempts >= max_attempts:
                return Response(status="failed", reason=_BUDGET_MSG)
            attempts += 1
            params = action.get("params") or {}
            program_name = str(action.get("program_name") or "PROGRAM")
            inferred.extend(action.get("inferred") or [])

            base = action.get("base_draft")
            if base is not None:
                base = base if base in drafts else draft_id
            last_errors = ([e.to_dict() for e in verdict.errors]
                           if base is not None else [])
            args = renderer.GenerateArgs(
                params=params, program_name=program_name,
                notes=[str(n) for n in action.get("notes") or []],
                chunks=chunks, base_draft=base, errors=last_errors,
                fix_guidance=action.get("fix_guidance"))
            rsess = renderer.RenderSession(example_ls=req.example_ls,
                                           drafts=drafts)
            prompt_text = renderer.render(cfg, table, rsess, args)

            draft = llm2.generate(prompt_text, llm)
            draft_id = sess.save_draft(draft.text)
            drafts[draft_id] = draft.text

            verdict = validate(draft.text, check_table, limits)
            sess.save_verdict(draft_id, verdict.verdict,
                              errors=[e.to_dict() for e in verdict.errors],
                              stats=verdict.stats)
            if verdict.verdict == "pass":
                program = draft.text
                break

            sig = tuple(sorted({e.layer for e in verdict.errors}))
            escalated = sig == last_sig
            last_sig = sig
            messages.append({"role": "user", "content": json.dumps({
                "draft_id": draft_id,
                "validator_errors": [e.to_dict()
                                     for e in verdict.errors[:10]],
                "attempt": attempts,
                "attempts_left": max_attempts - attempts,
                "escalation": escalated}, sort_keys=True)})

        if program is None:
            return Response(status="failed", reason=_BUDGET_MSG)

        try:                                # audit ALWAYS; can never block
            advisories = review.semantic_audit(program, params, table, llm)
        except (LLMClientError, llm1.ProtocolError):
            advisories = ["The automatic review wasn't available this time "
                          "- please give the program a quick manual look."]

    except llm1.ProtocolError:
        return Response(status="failed", reason=_PROTOCOL_MSG)
    except LLMClientError as e:
        return Response(status="failed", reason=str(e))

    report = Report(
        scan_used=table.scanned_at or None,
        table_source=source,
        mapping_confidence="unverified" if source == "none" else "verified",
        effective_defaults=cfg.get("defaults", {}),
        positions=_positions(program, table),
        inferred=inferred,
        retries=attempts - 1,
        advisories=_mandatory_advisories(source) + advisories)
    file_ref = output_store.save(sess.id, draft_id, program_name, program,
                                 asdict(report), client=sb_client)
    sess.log_decision(f"delivered {draft_id} after {attempts} attempt(s)")
    return Response(status="ok", draft_id=draft_id, program_ls=program,
                    file_ref=file_ref, report=report)
