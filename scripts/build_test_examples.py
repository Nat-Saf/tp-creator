"""Build corpus/examples/Testing: grader-style prompts with VERIFIED
program outputs. Each prompt runs live through /api/execute; the
(prompt, program) pair is saved only when every property check passes,
so the folder always shows real, correct behavior.

    .venv/Scripts/python.exe scripts/build_test_examples.py [name ...]
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tpagent import config

config.load_dotenv()
os.environ["TP_LLM1"] = "llmod:NBUECSE-gpt-5-mini"
os.environ["TP_LLM2"] = "llmod:NBUECSE-gpt-5-mini"

from fastapi.testclient import TestClient

from api.index import app

client = TestClient(app)
OUT = ROOT / "corpus" / "examples" / "Testing"


def has(*subs):
    return lambda p: all(s in p for s in subs), "contains " + ", ".join(subs)


def rx(pattern, why):
    return lambda p: re.search(pattern, p) is not None, why


def no(sub, why):
    return lambda p: sub not in p, why


TESTS = [
    ("01_basic_pick_place",
     "pick a part from the conveyor and put it on fixture A, gently",
     [has("PR[5", "PR[8", "RO[1"), rx(r"WAIT\s+1\.\d+\(sec\)",
                                      "gently -> longer settle")]),
    ("02_pick_place_fixture_b",
     "pick a part from the conveyor and place it on fixture B",
     [has("PR[5", "PR[9"), has("RO[1")]),
    ("03_named_program_speed",
     "write a program called DEMO_CYCLE that moves from home to conveyor "
     "approach at 150mm/sec and back home",
     [has("/PROG DEMO_CYCLE", "150mm/sec", "PR[6"),
      rx(r"J PR\[1[^;]*FINE", "home moves")]),
    ("04_camera_minute_wait",
     "move from home to the camera inspection pose, turn the camera on, "
     "wait for a minute, turn the camera off, and return home",
     [has("PR[17"), rx(r"DO\[1[:\]]", "camera output"),
      rx(r"WAIT\s+60\.\d+\(sec\)", "full 60s wait")]),
    ("05_wait_part_present_timeout",
     "pick from the conveyor and place on fixture A, but before picking "
     "wait until part present is on with a 5 second timeout to an error "
     "label",
     [has("DI[3", "TIMEOUT", "LBL")]),
    ("06_cycle_counter",
     "pick and place from the conveyor to fixture A and increment the "
     "cycle count at the end",
     [rx(r"R\[1[:\]][^;]*=[^;]*R\[1[:\]][^;]*\+\s*1", "R[1]=R[1]+1")]),
    ("07_lamp_pulse",
     "pick from the conveyor to fixture A and pulse the green lamp for "
     "1 second at the end",
     [has("DO[7"), rx(r"WAIT\s+1\.\d+\(sec\)|PULSE", "1s pulse")]),
    ("08_gripper_feedback",
     "pick from the conveyor, verify the gripper closed feedback after "
     "closing the gripper, then place on fixture A",
     [has("RI[1", "RO[1", "PR[8")]),
    ("09_repeat_three_cycles",
     "pick from the conveyor and place on fixture A, repeat the cycle "
     "3 times",
     [lambda p: ("LBL[" in p and ("JMP" in p or "IF" in p))
      or p.count("PR[5") >= 3, "loop or three unrolled cycles"]),
    ("10_io_only_buzzer",
     "write a program that turns the buzzer on for 2 seconds and then "
     "off, with no motion at all",
     [has("DO[5"), rx(r"WAIT\s+2\.\d+\(sec\)", "2s wait"),
      no("L PR[", "no linear moves"), no("J PR[", "no joint moves")]),
    ("11_smooth_through_point",
     "move from home through conveyor approach to fixture A approach "
     "without stopping at the middle point, then back home",
     [has("PR[6", "PR[7"),
      lambda p: any("CNT" in l for l in p.splitlines()
                    if re.search(r"[JL]\s+PR\[6[:\]]", l)),
      "through-move blends with CNT"]),
    ("12_from_to_points",
     "move the robot from the safe travel point to the purge station "
     "and then home",
     [has("PR[14", "PR[16"),
      lambda p: (lambda m: "14" in m and "16" in m
                 and m.index("14") < m.index("16"))(
          re.findall(r"[JL]\s+PR\[(\d+)[,:\]]", p)),
      "visits FROM before TO"]),
    ("13_conditional_pick",
     "if the part present input is on, pick from the conveyor and place "
     "on fixture A; otherwise just go back to home",
     [has("IF", "DI[3", "LBL")]),
    ("14_conveyor_handshake",
     "move from home to conveyor approach, start the conveyor, wait "
     "until conveyor running is on with a 10 second timeout to an error "
     "label, then stop the conveyor and go home",
     [has("DO[6", "DI[4", "TIMEOUT")]),
    ("15_relative_down_named_scratch",
     "move from home to fixture A approach, then move down by 50mm "
     "using PR[10] as a scratch register, and return home",
     [has("PR[7", "PR[10,3"), rx(r"-\s*50", "50mm down"),
      lambda p: p.count("PR[10]=PR[") == 1, "single scratch seed"]),
]


def normalize(checks):
    out = []
    for item in checks:
        if isinstance(item, tuple):
            out.append(item)
        else:                        # a bare lambda followed by its label
            out.append((item, None))
    # pair bare lambdas with the string that follows them in the list
    fixed, i = [], 0
    flat = []
    for item in checks:
        flat.append(item)
    while i < len(flat):
        if isinstance(flat[i], tuple):
            fixed.append(flat[i])
            i += 1
        else:
            fixed.append((flat[i], flat[i + 1]))
            i += 2
    return fixed


def run_test(name, prompt, checks, attempt=1):
    r = client.post("/api/execute", json={"prompt": prompt}).json()
    text = r["response"] or ""
    if "\n--- table ---\n" in text:
        text = text.rsplit("\n--- table ---\n", 1)[0]
    prog = text.split("\n--- report ---")[0].strip()
    if not prog.startswith("/PROG"):
        return None, [f"no program (reply: {text[:160]!r})"]
    fails = []
    for fn, why in normalize(checks):
        try:
            ok = fn(prog)
        except Exception as e:
            ok = False
            why = f"{why} (check error: {e})"
        if not ok:
            fails.append(why)
    return prog, fails


def main():
    only = set(sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for name, prompt, checks in TESTS:
        if only and not any(o in name for o in only):
            continue
        prog, fails = run_test(name, prompt, checks)
        if fails:                                   # one retry
            prog, fails = run_test(name, prompt, checks)
        if not fails and prog:
            (OUT / f"{name}.prompt.txt").write_text(prompt + "\n",
                                                    encoding="utf-8")
            (OUT / f"{name}.ls").write_text(prog + "\n", encoding="utf-8")
        results.append((name, prompt, fails))
        mark = "PASS" if not fails else "FAIL"
        print(f"[{mark}] {name}")
        for f in fails:
            print(f"       - {f}")

    lines = ["# Testing examples",
             "",
             "Grader-style prompts with their VERIFIED program outputs.",
             "Each pair was produced by a live run through /api/execute",
             "and saved only after passing its property checks.",
             "", "| # | Prompt | Output |", "|---|---|---|"]
    for name, prompt, fails in results:
        if not fails:
            lines.append(f"| {name.split('_')[0]} | {prompt} | "
                         f"`{name}.ls` |")
    (OUT / "README.md").write_text("\n".join(lines) + "\n",
                                   encoding="utf-8")
    passed = sum(1 for _, _, f in results if not f)
    print(f"\n{passed}/{len(results)} saved -> {OUT}")


if __name__ == "__main__":
    main()
