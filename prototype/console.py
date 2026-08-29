"""console.py -- Orchestrator v0: a conversational shell with zero LLM.

Speaks ONLY the Section-2 contract. Holds the conversation state the unit
deliberately does not: last draft, pending questions, the scan CSV to relay.

Commands:  /new  forget the current draft (next prompt is a new program)
           /report  show the last report
           /exit
"""
from __future__ import annotations
import argparse, difflib, sys
from pathlib import Path

from contract import Request, Response
import mock_unit


def post_to_unit(req: Request) -> Response:
    # v0 wiring: direct call. Later: HTTP to the real unit. Contract unchanged.
    return mock_unit.handle(req)


def show_report(r) -> str:
    if not r:
        return "(no report yet)"
    out = [f"  scan used:   {r.scan_used}  (source: {r.table_source}, {r.mapping_confidence})",
           f"  defaults:    " + ", ".join(f"{k}={v}" for k, v in r.effective_defaults.items()),
           f"  positions:   " + "; ".join(f"{k} {v}" for k, v in r.positions.items()),
           f"  retries:     {r.retries}"]
    for i in r.inferred:
        out.append(f"  inferred:    '{i['text']}' -> {i['decision']}")
    for a in r.advisories:
        out.append(f"  advisory:    {a}")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", default="line3_fanuc1")
    ap.add_argument("--scan", type=Path, default=None,
                    help="reg_io_v1 CSV to relay with the first request")
    args = ap.parse_args()

    scan_csv = args.scan.read_text(encoding="utf-8") if args.scan else None
    last_draft: str | None = None
    last_program: str | None = None
    last_report = None
    pending = False

    print(f"TP creator console - cell {args.cell}. /new /report /exit")
    for line in sys.stdin:
        user = line.strip()
        if not user:
            continue
        print(f"> {user}")
        if user == "/exit":
            break
        if user == "/new":
            last_draft, last_program, pending = None, None, False
            print("(starting a new program - previous draft forgotten)\n")
            continue
        if user == "/report":
            print(show_report(last_report) + "\n")
            continue

        req = Request(
            prompt=user,
            cell_id=args.cell,
            scan=scan_csv,
            revision_of=last_draft,
            answers={"reply": user} if pending else {},
        )
        scan_csv = None  # relay the map once; the unit persists it
        resp = post_to_unit(req)

        if resp.status == "needs_clarification":
            pending = True
            for q in resp.questions:
                print(f"[unit] {q}\n")
        elif resp.status == "ok":
            pending = False
            print(f"[unit] Done - draft {resp.draft_id}  ({resp.file_ref})")
            if last_program:
                diff = list(difflib.unified_diff(
                    last_program.splitlines(), resp.program_ls.splitlines(),
                    "previous", resp.draft_id, lineterm="", n=1))
                print("  changes vs previous draft:")
                for d in diff[2:]:
                    if d.startswith(("+", "-")):
                        print(f"    {d}")
            else:
                print(resp.program_ls)
            print(show_report(resp.report) + "\n")
            last_draft, last_program, last_report = resp.draft_id, resp.program_ls, resp.report
        else:  # rejected | failed
            pending = False
            print(f"[unit] ({resp.status}) {resp.reason}\n")


if __name__ == "__main__":
    main()
