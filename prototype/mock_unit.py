"""mock_unit.py -- a contract-faithful stand-in for the TP creator unit.

Implements, for real:
  - level-A validation (contract.validate_request)
  - reg_io_v1 parsing and table_source reporting (Section 2c, scan-or-ask subset)
  - the full conversation protocol of Section 2/2b: intake questions, raw-text
    answers ({"reply": ...}), revisions via revision_of, friendly language rule
  - session persistence across contract calls (drafts, pending question keys)

Stands in for (deterministic, no LLM):
  - LLM #1 intake reasoning: note-substring matching over the table
  - LLM #2 + validator: emits the known-good trace program directly

Swap-out point for the real unit: `handle(request) -> Response` is the whole API.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

from contract import Request, Response, Report, validate_request
from reg_io import parse_reg_io_csv, RegIOTable, SchemaError

DEFAULTS = {"speed": "100mm/sec", "pick_speed": "50mm/sec", "term": "FINE",
            "utool": 1, "uframe": 1, "gripper_settle_sec": 0.5}

SCOPE_WORDS = {"pick", "place", "move", "grab", "put", "gripper", "wait",
               "home", "palletize", "approach", "conveyor", "fixture", "program"}


@dataclass
class Session:
    table: RegIOTable | None = None
    table_source: str | None = None
    params: dict = field(default_factory=dict)
    pending: str | None = None          # which question is open: "fixture" | "scan"
    drafts: dict = field(default_factory=dict)   # draft_id -> program text
    seq: int = 0


_SESSIONS: dict[str, Session] = {}


def handle(req: Request) -> Response:
    # ---- level A: runtime, mechanical, no reasoning (Section 2b) ----
    if (msg := validate_request(req)) is not None:
        return Response(status="rejected", reason=msg)

    sess = _SESSIONS.setdefault(req.cell_id, Session())

    # ---- runtime persists inputs (step 2) ----
    if req.scan:
        try:
            sess.table = parse_reg_io_csv(req.scan)
            sess.table_source = "scan"
        except SchemaError as e:
            return Response(status="rejected", reason=str(e))
    if sess.table is None:
        # no scan, no cache in this mock -> friendly ask (Section 2c bottom rung)
        sess.pending = "scan"
        return Response(status="needs_clarification", questions=[
            f"I need a clarification: can you load an updated IO and registers map "
            f"for cell {req.cell_id}? I don't have one for this cell yet."])

    # ---- LLM #1 intake stand-in (level B) ----
    text = req.prompt.lower()

    # resolve an open question first, using the raw reply (answers relaxation)
    if sess.pending == "fixture" and req.answers:
        reply = str(req.answers.get("reply", "")).lower()
        cands = sess.table.by_note("fixture", "PR")
        place = [e for e in cands if "place" in e.comment.lower()]
        chosen = next((e for e in place
                       if f"pr[{e.index}]" in reply
                       or re.search(rf"\b{re.escape(_letter(e.comment))}\b", reply)), None)
        if chosen is None:
            return Response(status="needs_clarification", questions=[
                "Sorry, I still couldn't tell which fixture you mean - "
                + _fixture_question(place)])
        sess.params["place"] = chosen
        sess.pending = None
        text = ""  # the reply was an answer, not a new task

    # scope check (only for fresh prompts, not answers)
    if text and not (SCOPE_WORDS & set(re.findall(r"[a-z]+", text))):
        return Response(status="rejected", reason=(
            "I can only create FANUC TP programs (motion, gripper, waits, IO). "
            "This doesn't look like a program request - the main assistant can "
            "help with other topics."))

    # revision: patch params instead of restarting (step 3, revision loop)
    revising = req.revision_of in sess.drafts and bool(text)
    if not revising and text:
        sess.params = {}

    # parameter resolution from table notes
    p = sess.params
    if "pick" not in p:
        m = sess.table.by_note("conveyor pick", "PR") or sess.table.by_note("pick", "PR")
        if m: p["pick"] = m[0]
    if "pick_approach" not in p:
        m = sess.table.by_note("conveyor approach", "PR")
        if m: p["pick_approach"] = m[0]
    if "gripper" not in p:
        m = [e for e in sess.table.by_note("gripper close") if e.direction == "out"]
        if m: p["gripper"] = m[0]
    if "home" not in p:
        m = sess.table.by_note("home", "PR")
        if m: p["home"] = m[0]

    inferred = sess.params.setdefault("_inferred", [])
    if "gently" in text or "gentle" in text:
        sess.params["_settle"] = 1.0
        inferred.append({"text": "gently", "decision": "gripper settle 1.0s (default 0.5s)"})
    settle = sess.params.get("_settle", DEFAULTS["gripper_settle_sec"])
    if revising and "approach" in text:
        m = sess.table.by_note("fixture a approach", "PR") or sess.table.by_note("approach", "PR")
        if m:
            p["place_approach"] = m[0]
            inferred.append({"text": req.prompt, "decision":
                             f"added approach via PR[{m[0].index}] before the place move"})

    # place target: the deliberate ambiguity of the trace
    if "place" not in p and ("fixture" in text or "place" in text or "put" in text):
        cands = [e for e in sess.table.by_note("fixture", "PR") if "place" in e.comment.lower()]
        named = [e for e in cands
                 if _letter(e.comment) and f"fixture {_letter(e.comment)}" in text]
        if len(named) == 1:
            p["place"] = named[0]
        elif len(cands) == 1:
            p["place"] = cands[0]
        elif len(cands) > 1:
            sess.pending = "fixture"
            return Response(status="needs_clarification",
                            questions=[_fixture_question(cands)])

    missing = [k for k in ("pick", "place", "gripper") if k not in p]
    if missing:
        return Response(status="needs_clarification", questions=[
            "I couldn't find these in the IO and registers map: "
            + ", ".join(missing)
            + ". Can you point me to the right registers, or update the map's comments?"])

    # ---- LLM #2 + validator stand-in: emit the known-good program ----
    eff = DEFAULTS | req.config_overrides
    sess.seq += 1
    draft_id = f"{req.cell_id[:4]}_v{sess.seq}"
    program = _emit(p, eff, settle)
    sess.drafts[draft_id] = program

    positions = {f"PR[{e.index}]": f"note '{e.comment}'"
                 for e in (p.get("home"), p.get("pick_approach"), p.get("pick"),
                           p.get("place_approach"), p.get("place")) if e}
    advisories = []
    if "place_approach" not in p:
        m = sess.table.by_note("fixture a approach", "PR")
        if m and p["place"].index != m[0].index:
            advisories.append(
                f"There's no approach move before the fixture place - "
                f"PR[{m[0].index}] '{m[0].comment}' is available. Want me to add it?")

    return Response(
        status="ok", draft_id=draft_id, program_ls=program,
        file_ref=f"out/{req.cell_id}/{draft_id}.ls",
        report=Report(
            scan_used=sess.table.scanned_at, table_source=sess.table_source,
            mapping_confidence="verified", effective_defaults=eff,
            positions=positions, inferred=inferred, retries=0,
            advisories=advisories))


def _letter(comment: str) -> str:
    m = re.search(r"fixture\s+([a-z])", comment.lower())
    return m.group(1) if m else ""


def _fixture_question(cands) -> str:
    opts = " or ".join(
        f"fixture {_letter(e.comment).upper()} (PR[{e.index}] '{e.comment}')" for e in cands)
    return f"Which fixture should I place the part on - {opts}?"


def _emit(p: dict, eff: dict, settle: float) -> str:
    L = []
    L.append(f"   1:  UFRAME_NUM={eff['uframe']} ;")
    L.append(f"   2:  UTOOL_NUM={eff['utool']} ;")
    L.append("   3:  !pick from conveyor ;")
    L.append(f"   4:  J PR[{p['home'].index}:{p['home'].comment}] 100% {eff['term']} ;")
    n = 5
    if "pick_approach" in p:
        e = p["pick_approach"]
        L.append(f"   {n}:  L PR[{e.index}:{e.comment}] {eff['speed']} {eff['term']} ;"); n += 1
    e = p["pick"]
    L.append(f"   {n}:  L PR[{e.index}:{e.comment}] {eff['pick_speed']} {eff['term']} ;"); n += 1
    g = p["gripper"]
    L.append(f"   {n}:  {g.type}[{g.index}:{g.comment}]=ON ;"); n += 1
    L.append(f"   {n}:  WAIT   {settle:.2f}(sec) ;"); n += 1
    if "pick_approach" in p:
        e = p["pick_approach"]
        L.append(f"   {n}:  L PR[{e.index}:{e.comment}] {eff['speed']} {eff['term']} ;"); n += 1
    L.append(f"   {n}:  !place on {p['place'].comment} ;"); n += 1
    if "place_approach" in p:
        e = p["place_approach"]
        L.append(f"  {n}:  L PR[{e.index}:{e.comment}] {eff['speed']} {eff['term']} ;"); n += 1
    e = p["place"]
    L.append(f"  {n}:  L PR[{e.index}:{e.comment}] {eff['speed']} {eff['term']} ;"); n += 1
    L.append(f"  {n}:  {g.type}[{g.index}]=OFF ;"); n += 1
    L.append(f"  {n}:  WAIT   0.50(sec) ;"); n += 1
    L.append(f"  {n}:  J PR[{p['home'].index}:{p['home'].comment}] 100% {eff['term']} ;")
    body = "\n".join(L)
    return f"/PROG PICK_PLACE\n/ATTR\nOWNER = MNEDITOR;\nCOMMENT = \"auto v1\";\n/MN\n{body}\n/POS\n/END\n"
