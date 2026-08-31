"""Live prompt-quality eval: 21 scenarios through /api/execute.

Each scenario replays a realistic conversation (transcript built the way
the GUI builds it, previous_ls and table trailers included) and checks
PROPERTIES of the answer - never exact text, the models aren't
deterministic. Run it after quality tuning; it spends live tokens
(~$0.3-0.5 for the full sweep).

    .venv/Scripts/python.exe scripts/eval_prompts.py [name ...]

With names, only those scenarios run. Results: printed + out/eval.json.
"""
import contextvars
import json
import os
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_LOG = contextvars.ContextVar("scenario_log")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tpagent import config

config.load_dotenv()
os.environ["TP_LLM1"] = "llmod:NBUECSE-gpt-5-mini"
os.environ["TP_LLM2"] = "llmod:NBUECSE-gpt-5-mini"

from fastapi.testclient import TestClient

from api.index import app

client = TestClient(app)

BASE_PROG = """/PROG DEMO_PICK
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !pick from conveyor, place on fixture A ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   6:  L PR[5:conveyor pick] 50mm/sec FINE ;
   7:  RO[1:gripper close]=ON ;
   8:  WAIT .50(sec) ;
   9:  L PR[6] 100mm/sec CNT50 ;
  10:  L PR[8:fixture A place] 50mm/sec FINE ;
  11:  RO[1]=OFF ;
  12:  WAIT .50(sec) ;
  13:  J PR[1:home] 100% FINE ;
/POS
/END"""

BARE_TABLE = ("type,index,comment\n"
              "PR,21,station home\n"
              "PR,22,drop point\n"
              "DO,25,clamp close\n")


def call(prompt, scan=None, previous=None):
    body = {"prompt": prompt}
    if scan:
        body["scan"] = scan
    if previous:
        body["previous_ls"] = previous
    r = client.post("/api/execute", json=body).json()
    text = r["response"] or ""
    table_csv = None
    if "\n--- table ---\n" in text:
        text, table_csv = text.rsplit("\n--- table ---\n", 1)
    prog = None
    report = ""
    if "\n--- report ---\n" in text:
        head, report = text.split("\n--- report ---\n", 1)
        if head.strip().startswith("/PROG"):
            prog = head.strip()
    result = {"raw": r, "text": text, "prog": prog, "report": report,
              "table": table_csv, "status": r["status"],
              "modules": [s["module"] for s in r["steps"]]}
    log = _LOG.get(None)
    if log is not None:
        log.append({"prompt": prompt[-200:], "reply": text[:900]})
    return result


def follow(t1_prompt, reply, t2_prompt, **kw):
    return call(f"user: {t1_prompt}\nassistant: {reply}\nuser: {t2_prompt}",
                **kw)


class Checks:
    def __init__(self):
        self.fails = []

    def need(self, cond, msg):
        if not cond:
            self.fails.append(msg)
        return cond


# ---------------------------------------------------------------- scenarios

def sc_basic_pick_place(c):
    r = call("pick a part from the conveyor and put it on fixture A")
    c.need(r["prog"], "no program delivered") and (
        c.need("PR[5" in r["prog"], "conveyor pick PR[5] missing"),
        c.need("PR[8" in r["prog"], "fixture A place PR[8] missing"),
        c.need("RO[1" in r["prog"], "gripper RO[1] missing"),
        c.need("WAIT" in r["prog"], "settle WAIT missing"))


def sc_gently_settle(c):
    r = call("pick a part from the conveyor and put it on fixture A, gently")
    if c.need(r["prog"], "no program delivered"):
        c.need("gently" in r["report"] or "WAIT 1.0" in r["prog"]
               or "WAIT  1.0" in r["prog"],
               "'gently' neither inferred in report nor longer settle")


def sc_ambiguous_fixture(c):
    r = call("pick a part from the conveyor and put it on the fixture")
    c.need(not r["prog"], "should ask, not deliver a program")
    c.need("fixture A" in r["text"] and "fixture B" in r["text"],
           "question must name both fixtures")


def sc_missing_position_short(c):
    r = call("create a program to move the robot from home position to "
             "position 2")
    c.need(not r["prog"], "should ask, not deliver a program")
    c.need(len(r["text"]) < 350, f"question too long ({len(r['text'])})")
    c.need(r["text"].count("PR[") <= 2,
           "first response must not list candidates")
    c.need("option" in r["text"].lower() or "available" in r["text"].lower()
           or "add" in r["text"].lower(),
           "must offer to list options or add the entry")


def sc_add_pr2_flow(c):
    t1 = ("create a program to move the robot from home position to "
          "position 2")
    r1 = call(t1)
    if not c.need(not r1["prog"], "turn 1 should ask"):
        return
    r2 = follow(t1, r1["text"], "add pr2 to the table")
    if c.need(r2["prog"], "turn 2 should deliver a program"):
        c.need("PR[2" in r2["prog"], "PR[2] not used")
        c.need("added PR[2]" in r2["report"], "addition not reported")
        c.need(r2["table"] and "PR,2," in r2["table"],
               "updated table not returned")


def sc_table_only_add(c):
    r = call("add DO[100] to the table with description 'dispenser on' "
             "and set it to false")
    c.need(not r["prog"], "table-only request must not deliver a program")
    c.need("DO[100]" in r["text"], "confirmation must name DO[100]")
    c.need(r["table"] and "DO,100,dispenser on" in r["table"],
           "updated table not returned")


def sc_table_update_existing(c):
    r = call("add description to pr10 in the table 'middle position'")
    c.need(not r["prog"], "table-only request must not deliver a program")
    c.need("PR[10]" in r["text"], "confirmation must name PR[10]")
    c.need(r["table"] and "PR,10,middle position" in r["table"],
           "updated note not in returned table")


def sc_future_use_ack(c):
    t1 = "add pr12 to the table and call it 'middle position'"
    r1 = call(t1)
    r2 = follow(t1, r1["text"],
                "it is for future use and not for the current program")
    c.need(not r2["prog"], "acknowledgment must not deliver a program")
    c.need("--- report ---" not in r2["text"], "no report expected")
    c.need(len(r2["text"]) < 400, "acknowledgment should be short")


def sc_conversation_close(c):
    # a done-signal gets a short closing statement, never another
    # "anything else I can help with?" loop
    r = call("user: add pr12 to the table and call it 'middle position'\n"
             "assistant: Done - PR[12] 'middle position' is now in this "
             "conversation's table.\n"
             "user: ok, leave the program as it is\n"
             "assistant: Okay - the program stays as it is.\n"
             "user: no, thanks")
    c.need(not r["prog"], "goodbye must not deliver a program")
    c.need("?" not in r["text"], f"closing reply asks a question: "
           f"{r['text'][:150]!r}")
    c.need(len(r["text"]) < 200, "closing reply should be one short line")


def sc_camera_no_match(c):
    r = call("create a pick program that triggers the camera output at "
             "the pick point")
    c.need(not r["prog"], "should ask, not deliver a program")
    c.need("green lamp" not in r["text"].lower(),
           "must not guess candidates (green lamp)")
    c.need("add" in r["text"].lower(), "must offer creating an entry")


def sc_list_after_ask(c):
    t1 = ("create a pick program that triggers the camera output at "
          "the pick point")
    r1 = call(t1)
    if not c.need(not r1["prog"], "turn 1 should ask"):
        return
    r2 = follow(t1, r1["text"], "list the available outputs")
    c.need(not r2["prog"], "listing turn must not deliver a program")
    c.need("DO[7" in r2["text"], "outputs list should include DO[7]")


def sc_relative_ask(c):
    r = call("create a program that will move the robot above the "
             "conveyor, open the gripper, move down by 100mm, close the "
             "gripper, move up by 100mm and then move to home position")
    c.need(not r["prog"], "should ask for a scratch register first")
    c.need("register" in r["text"].lower(), "question should mention a "
           "register")
    return r


def sc_relative_full(c):
    t1 = ("create a program that will move the robot above the conveyor, "
          "open the gripper, move down by 100mm, close the gripper, move "
          "up by 100mm and then move to home position")
    r1 = call(t1)
    if not c.need(not r1["prog"], "turn 1 should ask"):
        return
    r2 = follow(t1, r1["text"], "use PR[10] as the scratch register")
    if c.need(r2["prog"], "turn 2 should deliver a program"):
        p = r2["prog"]
        c.need("PR[10,3]" in p, "no element offset on the scratch PR")
        c.need("-100" in p and "+100" in p, "both offsets missing")
        c.need(p.count("PR[10]=PR[") == 1,
               "scratch reset before ascent (overshoot) or never seeded")


_ASSIGN = r"PR\[{idx}(?:\s*,\s*\d+)?(?::[^\]]*)?\]\s*="


def _check_new_dest(c, r, idx, note):
    if not c.need(r["prog"], "no program delivered"):
        return
    p = r["prog"]
    c.need(f"PR[{idx}" in p, f"PR[{idx}] not used as the target")
    c.need(not re.search(_ASSIGN.format(idx=idx), p),
           f"program writes into the new destination PR[{idx}]")
    c.need(not re.search(r"!.*table", p, re.IGNORECASE),
           "program comments narrate the table change")
    c.need(r["table"] and f"PR,{idx},{note}" in r["table"],
           "updated table not returned with the new entry")


def sc_new_dest_pr12(c):
    r = call("create a program to move the robot from home position to "
             "new pr12, add it to the table as 'middle point'")
    _check_new_dest(c, r, 12, "middle point")


def sc_new_dest_pr30(c):
    r = call("move from home to a new position register PR[30] called "
             "'inspection point', add it to the table")
    _check_new_dest(c, r, 30, "inspection point")


def sc_new_dest_with_io(c):
    r = call("move from home to conveyor approach, then to a new PR[25] "
             "'drop test point' (add it to the table), and turn on a new "
             "output DO[42] 'blow air' there - add that too")
    _check_new_dest(c, r, 25, "drop test point")
    if r["prog"]:
        c.need("DO[42" in r["prog"], "new output DO[42] not used")
        c.need(r["table"] and "DO,42,blow air" in r["table"],
               "DO[42] missing from the returned table")


def sc_ordered_sequence(c):
    # the reported bug: an explicitly ordered request was recast into a
    # pick-and-place template with an invented release and extra B visit
    t1 = ("create a new program that moves the robot from point A to "
          "point B, then open the gripper, moves down 100mm across Z "
          "axis, close the gripper, moves up across Z axis and then "
          "goes to home position")
    r = call(t1)
    if not r["prog"]:
        c.need(r["text"].count("PR[") <= 3,
               "first question dumps table candidates")
        r = follow(t1, r["text"],
                   "point A is PR[5], point B is PR[8], use PR[10] as "
                   "the scratch register")
    if not c.need(r["prog"], "no program delivered"):
        return
    p = r["prog"]
    body = [l for l in p.splitlines() if re.match(r"\s*\d+:", l)]

    def line_of(pattern):
        return next((i for i, l in enumerate(body) if re.search(pattern, l)),
                    None)

    open_i = line_of(r"RO\[2[:\]].*=\s*ON")
    down_i = line_of(r"-\s*100")
    close_i = line_of(r"RO\[1[:\]].*=\s*ON")
    order = [open_i, down_i, close_i]
    c.need(all(i is not None for i in order)
           and order == sorted(order),
           f"steps out of order (open/down/close at {order})")
    if close_i is not None:
        after = "\n".join(body[close_i + 1:])
        c.need("RO[1]=OFF" not in after.replace(" ", "")
               and not re.search(r"RO\[2[:\]][^;]*=\s*ON", after),
               "invented release after the close - part must stay gripped")
    up_i = line_of(r"\+\s*100")
    if up_i is not None:
        # ascent done via the scratch register: a B visit AFTER it is an
        # invented transport (an up-move expressed as L PR[8] is fine)
        after_up = "\n".join(body[up_i + 1:])
        c.need(not re.search(r"[JL]\s+PR\[8[:\]]", after_up),
               "extra visit to point B after the ascent")
    motions = re.findall(r"[JL]\s+PR\[(\d+)[,:\]]", p)
    c.need(motions and motions[-1] == "1",
           f"program must end at home, ends at PR[{motions[-1] if motions else '?'}]")


def sc_edit_final_move(c):
    r = follow("write the pick program", BASE_PROG,
               "edit the program, at the end move to PR[9] instead of home",
               previous=BASE_PROG)
    if c.need(r["prog"], "no program delivered"):
        p = r["prog"]
        c.need("/PROG DEMO_PICK" in p, "program name changed")
        for kept in ("L PR[6:conveyor approach] 100mm/sec CNT50",
                     "L PR[5:conveyor pick] 50mm/sec FINE",
                     "RO[1:gripper close]=ON",
                     "L PR[8:fixture A place] 50mm/sec FINE"):
            c.need(kept in p, f"edit dropped unrelated line: {kept}")
        c.need("PR[9" in p, "new target PR[9] missing")
        motions = re.findall(r"[JL] PR\[(\d+)[^;]*;", p)
        c.need(motions and motions[-1] == "9",
               f"final move should target PR[9], got PR[{motions[-1] if motions else '?'}]")


def sc_edit_speed(c):
    r = follow("write the pick program", BASE_PROG,
               "edit the program, change the travel speed to 150mm/sec",
               previous=BASE_PROG)
    if c.need(r["prog"], "no program delivered"):
        p = r["prog"]
        c.need("150mm/sec" in p, "150mm/sec not applied")
        c.need("PR[5:conveyor pick" in p, "edit dropped the pick move")
        used = set(re.findall(r"PR\[(\d+)", p))
        c.need(used <= {"1", "5", "6", "8"},
               f"edit invented new registers: {sorted(used)}")


def sc_name_request(c):
    r = call("write a program that moves from home to conveyor approach "
             "and back home, call the program DEMO_ONE")
    if c.need(r["prog"], "no program delivered"):
        c.need("/PROG DEMO_ONE" in r["prog"], "requested name not used")


def sc_pulse_lamp(c):
    t1 = ("pick a part from the conveyor and place it on fixture B, "
          "and pulse the green lamp for 1 second at the end")
    r = call(t1)
    if not r["prog"]:
        # a question here is legitimate: the default table has no
        # 'fixture B approach' entry - answer it and expect the program
        if not c.need("approach" in r["text"].lower()
                      or "fixture B" in r["text"],
                      f"unexpected question: {r['text'][:200]!r}"):
            return
        r = follow(t1, r["text"],
                   "descend directly to fixture B place, no separate "
                   "approach point needed")
    if c.need(r["prog"], "no program delivered"):
        c.need("PR[9" in r["prog"], "fixture B place PR[9] missing")
        c.need("DO[7" in r["prog"], "green lamp DO[7] missing")


def sc_wait_part_present(c):
    r = call("pick from the conveyor and place on fixture A, but before "
             "picking wait until the part present input is on with a 5 "
             "second timeout to an error label")
    if c.need(r["prog"], "no program delivered"):
        c.need("DI[3" in r["prog"], "part present DI[3] missing")
        c.need("TIMEOUT" in r["prog"], "timeout form missing")
        c.need("LBL" in r["prog"], "label missing")


def sc_counter_increment(c):
    r = call("pick and place from the conveyor to fixture A and increment "
             "the cycle count register at the end")
    if c.need(r["prog"], "no program delivered"):
        c.need(re.search(r"R\[1[:\]].*=.*R\[1[:\]].*\+\s*1", r["prog"]),
               "cycle count R[1] increment missing")


def sc_own_table_scan(c):
    r = call("move from station home to the drop point and close the "
             "clamp at the end", scan=BARE_TABLE)
    if c.need(r["prog"], "no program delivered"):
        for ref in ("PR[21", "PR[22", "DO[25"):
            c.need(ref in r["prog"], f"uploaded-table ref {ref} missing")
        c.need("table source: scan" in r["report"],
               "report should say table source scan")


def sc_over_limit_speed(c):
    r = call("move from home to fixture A place at 400mm/sec")
    if r["prog"]:
        speeds = [float(s) for s in
                  re.findall(r"(\d+(?:\.\d+)?)mm/sec", r["prog"])]
        c.need(speeds and max(speeds) <= 250,
               f"over-limit speed delivered: {max(speeds) if speeds else '?'}")
    else:
        c.need("250" in r["text"] or "limit" in r["text"].lower(),
               "refusal/question should mention the limit")


def sc_reject_scope(c):
    r = call("write me a poem about the sea")
    c.need(not r["prog"], "out-of-scope request must not deliver a program")
    c.need(len(r["text"]) > 0, "friendly rejection expected")


SCENARIOS = {f.__name__[3:]: f for f in [
    sc_basic_pick_place, sc_gently_settle, sc_ambiguous_fixture,
    sc_missing_position_short, sc_add_pr2_flow, sc_table_only_add,
    sc_table_update_existing, sc_future_use_ack, sc_conversation_close,
    sc_camera_no_match,
    sc_list_after_ask, sc_relative_ask, sc_relative_full,
    sc_new_dest_pr12, sc_new_dest_pr30, sc_new_dest_with_io,
    sc_ordered_sequence,
    sc_edit_final_move, sc_edit_speed, sc_name_request, sc_pulse_lamp,
    sc_wait_part_present, sc_counter_increment, sc_own_table_scan,
    sc_over_limit_speed, sc_reject_scope,
]}


def run_one(name):
    def _inner():
        log = []
        _LOG.set(log)
        c = Checks()
        try:
            SCENARIOS[name](c)
        except Exception:
            c.fails.append("exception: " + traceback.format_exc(limit=3))
        return name, c.fails, log
    return contextvars.copy_context().run(_inner)


def main():
    names = sys.argv[1:] or list(SCENARIOS)
    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, fails, log in pool.map(run_one, names):
            results[name] = {"fails": fails,
                             "log": log if fails else []}
            mark = "PASS" if not fails else "FAIL"
            print(f"[{mark}] {name}")
            for f in fails:
                print(f"       - {f}")
            if fails:
                for turn in log:
                    print(f"       reply: {turn['reply'][:280]!r}")
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    (out / "eval.json").write_text(json.dumps(results, indent=2),
                                   encoding="utf-8")
    passed = sum(1 for f in results.values() if not f["fails"])
    print(f"\n{passed}/{len(results)} scenarios passed "
          f"-> {out / 'eval.json'}")


if __name__ == "__main__":
    main()
