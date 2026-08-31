"""validator/grammar.py -- FAMILIES dict + token walks + bounded suggestions.

Every /MN body line is dispatched by its leading token to a family
walker that consumes the line with a regex cursor. At each step the
legal continuations are enumerable by construction, so a failure
reports the position, the found text, and exactly that set (or the
canonical form string for pattern instructions like WAIT).

Suggestions appear ONLY here (grammar layer), and only when the found
token is within edit distance 2 of a UNIQUE legal token.
"""
from __future__ import annotations

import re

from tpagent.validator.verdict import Err

# one indexed reference, label may contain spaces: PR[10:conveyor approach]
REF = r"{types}\[\d+(?::[^\]]*)?\]"
POINT = REF.format(types=r"(?:P|PR)")
SPEED = r"(?:\d+(?:\.\d+)?|" + REF.format(types=r"R") + r")"
NUM = r"\d+(?:\.\d+)?"
VALUE = r"(?:ON|OFF|" + NUM + r"|" + REF.format(types=r"R") + r")"
COND_REF = REF.format(types=r"(?:R|DI|DO|RI|RO|UI|UO|SI|SO|GI|GO|AI|AO|F|TIMER)")
OPS = r"(?:<>|<=|>=|=|<|>)"

MOTION_UNITS = {"J": {"%", "sec"},
                "L": {"mm/sec", "cm/min", "inch/min", "deg/sec", "sec"},
                "C": {"mm/sec", "cm/min", "inch/min", "deg/sec", "sec"}}
MOTION_OPTIONS = [
    ("Offset,PR[i]", r"Offset," + REF.format(types=r"PR")),
    ("Tool_Offset,PR[i]", r"Tool_Offset," + REF.format(types=r"PR")),
    ("Offset", r"Offset(?!\w|,)"),
    ("Tool_Offset", r"Tool_Offset(?!\w|,)"),
    ("ACC<n>", r"ACC\d+"),
    ("Wjnt", r"Wjnt"),
    ("PTH", r"PTH"),
    ("Skip,LBL[i]", r"Skip,LBL\[\d+\]"),
]


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def suggest(found: str, candidates) -> str | None:
    close = [c for c in candidates if edit_distance(found.upper(), c) <= 2]
    return close[0] if len(close) == 1 else None


class Cursor:
    def __init__(self, line_no: int, content: str):
        self.line_no = line_no
        self.content = content
        self.pos = 0

    def skip_ws(self):
        while self.pos < len(self.content) and self.content[self.pos] == " ":
            self.pos += 1

    def eat(self, pattern: str) -> re.Match | None:
        self.skip_ws()
        m = re.compile(pattern).match(self.content, self.pos)
        if m:
            self.pos = m.end()
        return m

    def done(self) -> bool:
        self.skip_ws()
        return self.pos >= len(self.content)

    def found(self) -> str:
        self.skip_ws()
        m = re.compile(r"\S+").match(self.content, self.pos)
        return m.group(0) if m else "(end of line)"

    def err(self, expected, suggestion=None) -> Err:
        return Err(layer="grammar", line=self.line_no, col=self.pos + 1,
                   found=self.found(),
                   expected=sorted(expected) if isinstance(expected, (set, list))
                   else expected,
                   suggestion=suggestion)


# ---------------------------------------------------------------- walkers

def _bracket_label_err(c: Cursor) -> list[Err] | None:
    # a label like PR[5:user pick PR[5]] leaves a dangling "]" here; say
    # what actually went wrong instead of "expected <speed>"
    if c.eat(r"\]"):
        return [Err(layer="grammar", line=c.line_no,
                    message="A position label can't contain brackets - "
                            "use plain words after the ':', e.g. "
                            "PR[5:pick point].")]
    return None


def walk_motion(c: Cursor, mtype: str) -> list[Err]:
    c.eat(mtype)
    if not c.eat(POINT):
        return [c.err({"P[i]", "PR[i]"})]
    if (err := _bracket_label_err(c)) is not None:
        return err
    if mtype == "C" and not c.eat(POINT):
        return [c.err({"P[i] (via point then destination)"})]
    if mtype == "C" and (err := _bracket_label_err(c)) is not None:
        return err
    units = MOTION_UNITS[mtype]
    m = c.eat(r"(" + NUM + r"|" + REF.format(types=r"R") + r")"
              + r"(" + "|".join(re.escape(u) for u in sorted(units, key=len, reverse=True)) + r")(?=\s|$)")
    if not m:
        return [c.err({f"<speed>{u}" for u in units})]
    if (mtype == "J" and m.group(2) == "%" and m.group(1)[0].isdigit()
            and not 1 <= float(m.group(1)) <= 100):
        c.pos -= len(m.group(0))
        return [c.err({"<1-100>%"})]
    m = c.eat(r"(FINE|CNT(\d+))(?=\s|$)")
    if not m or (m.group(2) is not None and not 0 <= int(m.group(2)) <= 100):
        if m:                                    # CNT out of range
            c.pos -= len(m.group(1))
        return [c.err({"FINE", "CNT0-100"})]
    while not c.done():
        for _, pat in MOTION_OPTIONS:
            if c.eat(pat + r"(?=\s|$)"):
                break
        else:
            return [c.err({name for name, _ in MOTION_OPTIONS})]
    return []


WAIT_FORM = "WAIT <t>.00(sec) | WAIT <condition> [TIMEOUT,LBL[i]]"


def walk_wait(c: Cursor) -> list[Err]:
    c.eat(r"WAIT")
    # timed: <t>.NN(sec) incl. FANUC's leading-dot spelling, or R[i](sec)
    if c.eat(r"(?:\d*\.\d{1,2}|" + REF.format(types=r"R") + r")\(sec\)$"):
        return []
    cond = COND_REF + r"\s*" + OPS + r"\s*" + VALUE
    if c.eat(cond):
        joiners = set()
        while True:
            m = c.eat(r"(AND|OR)\s+" + cond)
            if not m:
                break
            joiners.add(m.group(1))
        if len(joiners) > 1:
            return [Err(layer="grammar", line=c.line_no,
                        message="WAIT conditions may chain with AND or "
                                "with OR, never both in one line.")]
        c.eat(r"TIMEOUT\s*,\s*LBL\[\d+\]")
        if c.done():
            return []
        return [c.err({"AND", "OR", "TIMEOUT,LBL[i]", "(end of line)"})]
    rest = c.content[c.pos:].strip()
    suggestion = None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*\(?(?:sec|s)\)?", rest)
    if m:
        suggestion = f"WAIT {float(m.group(1)):.2f}(sec)"
    err = c.err(WAIT_FORM, suggestion)
    err.expected = None
    err.expected_form = WAIT_FORM
    return [err]


def walk_if(c: Cursor) -> list[Err]:
    c.eat(r"IF")
    cond = COND_REF + r"\s*" + OPS + r"\s*" + VALUE
    if not c.eat(cond):
        return [c.err({"<R[i]|DI[i]|...> <op> <ON|OFF|n|R[i]>"})]
    joiners = set()
    while True:
        m = c.eat(r"(AND|OR)\s+" + cond)
        if not m:
            break
        joiners.add(m.group(1))
    if len(joiners) > 1:
        return [Err(layer="grammar", line=c.line_no,
                    message="IF conditions may chain with AND or with OR, "
                            "never both in one line.")]
    if not c.eat(r",\s*(JMP\s+LBL\[\d+\]|CALL\s+\w+)"):
        return [c.err({",JMP LBL[i]", ",CALL <program>"})]
    return [] if c.done() else [c.err({"(end of line)"})]


def walk_select_head(c: Cursor) -> list[Err]:
    c.eat(r"SELECT")
    if not c.eat(REF.format(types=r"R") + r"\s*=\s*" + NUM):
        return [c.err({"R[i]=<n>"})]
    if not c.eat(r",\s*(JMP\s+LBL\[\d+\]|CALL\s+\w+)"):
        return [c.err({",JMP LBL[i]", ",CALL <program>"})]
    return [] if c.done() else [c.err({"(end of line)"})]


def walk_select_branch(c: Cursor) -> list[Err]:
    if not c.eat(r"(=\s*" + NUM + r"|ELSE)\s*,\s*(JMP\s+LBL\[\d+\]|CALL\s+\w+)"):
        return [c.err({"=<n>,JMP LBL[i]", "ELSE,JMP LBL[i]",
                       "=<n>,CALL <program>", "ELSE,CALL <program>"})]
    return [] if c.done() else [c.err({"(end of line)"})]


ASSIGN_FORMS = {"R[i]=<expr>", "PR[i]=<source>", "PR[i,j]=<expr>",
                "DO[i]=ON|OFF|PULSE", "RO[i]=ON|OFF|PULSE",
                "TIMER[i]=START|STOP|RESET", "UALM[i]"}


def walk_assign(c: Cursor) -> list[Err]:
    lhs = c.eat(r"(PR)\[\d+\s*,\s*\d+(?::[^\]]*)?\]"     # PR[i,j] only
                r"|(R|PR|DO|RO|GO|AO|F|TIMER|UALM)\[\d+(?::[^\]]*)?\]")
    if lhs is None:                       # e.g. R=5, R[ 1 ]=5, R[R[1]]=..
        return [c.err(ASSIGN_FORMS)]
    kind = lhs.group(1) or lhs.group(2)
    if kind == "UALM":
        return [] if c.done() else [c.err({"(end of line)"})]
    if not c.eat(r"="):
        return [c.err({"="})]
    if kind == "TIMER":
        return [] if c.eat(r"(START|STOP|RESET)$") else [
            c.err({"START", "STOP", "RESET"})]
    if kind in ("DO", "RO", "F"):
        ok = c.eat(r"(ON|OFF|PULSE(?:\s*,\s*" + NUM + r"sec)?|"
                   + REF.format(types=r"(?:R|DI|RI|DO|RO)") + r")$")
        return [] if ok else [c.err({"ON", "OFF", "PULSE[,<t>sec]", "R[i]",
                                     "DI[i]"})]
    elem_ref = r"(?:PR|P)\[\d+\s*,\s*\d+(?::[^\]]*)?\]"   # PR[i,j:label]
    term = (r"(?:-?" + NUM + r"|LPOS|JPOS|" + elem_ref + r"|"
            + REF.format(types=r"(?:R|PR|P|DI|DO|RI|RO|GI|GO|AI|AO|UI|UO|"
                               r"SI|SO|TIMER|PL|SR|AR|UFRAME|UTOOL)")
            + r")")
    term_expected = {"<n>", "R[i]", "PR[i]", "PR[i,j]", "P[i]",
                     "LPOS", "JPOS"}
    parenthesized = bool(c.eat(r"\("))    # FANUC prints computed RHS as (expr)
    if not c.eat(term):
        return [c.err(term_expected)]
    while c.eat(r"(\+|-|\*|/|DIV|MOD)"):
        if not c.eat(term):
            return [c.err(term_expected)]
    if parenthesized and not c.eat(r"\)"):
        return [c.err({")"})]
    return [] if c.done() else [c.err({"+", "-", "*", "/", "DIV", "MOD",
                                       "(end of line)"})]


def walk_simple(pattern: str, expected: set):
    def walker(c: Cursor) -> list[Err]:
        return [] if c.eat(pattern + r"$") else [c.err(expected)]
    return walker


FAMILIES = {
    "J": lambda c: walk_motion(c, "J"),
    "L": lambda c: walk_motion(c, "L"),
    "C": lambda c: walk_motion(c, "C"),
    "WAIT": walk_wait,
    "IF": walk_if,
    "SELECT": walk_select_head,
    "=": walk_select_branch,
    "ELSE": walk_select_branch,
    "CALL": walk_simple(r"CALL\s+\w+(?:\((?:[^)]*)\))?",
                        {"CALL <program>[(args)]"}),
    "JMP": walk_simple(r"JMP\s+LBL\[\d+\]", {"JMP LBL[i]"}),
    "LBL": walk_simple(r"LBL\[\d+(?::[^\]]*)?\]", {"LBL[i]"}),
    "RUN": walk_simple(r"RUN\s+\w+", {"RUN <program>"}),
    "END": walk_simple(r"END", {"END"}),
    "PAUSE": walk_simple(r"PAUSE", {"PAUSE"}),
    "ABORT": walk_simple(r"ABORT", {"ABORT"}),
    "UFRAME_NUM": walk_simple(r"UFRAME_NUM\s*=\s*(?:\d+|"
                              + REF.format(types=r"(?:R|AR)") + r")",
                              {"UFRAME_NUM=<n>"}),
    "UTOOL_NUM": walk_simple(r"UTOOL_NUM\s*=\s*(?:\d+|"
                             + REF.format(types=r"(?:R|AR)") + r")",
                             {"UTOOL_NUM=<n>"}),
    "OVERRIDE": None,                    # set below (range-checked walker)
    "PAYLOAD": walk_simple(r"PAYLOAD\[(?:GP\d+:)?\d+(?::[^\]]*)?\]",
                           {"PAYLOAD[i]", "PAYLOAD[GPx:y]"}),
    "MESSAGE": walk_simple(r"MESSAGE\[[^\]]*\]", {"MESSAGE[text]"}),
    "R": walk_assign, "PR": walk_assign, "DO": walk_assign,
    "RO": walk_assign, "GO": walk_assign, "AO": walk_assign,
    "F": walk_assign, "TIMER": walk_assign, "UALM": walk_assign,
}


def walk_override(c: Cursor) -> list[Err]:
    c.eat(r"OVERRIDE")
    m = c.eat(r"=\s*(\d+|" + REF.format(types=r"(?:R|AR)") + r")%$")
    if not m:
        return [c.err({"OVERRIDE=<1-100>%", "OVERRIDE=R[i]%"})]
    if m.group(1).isdigit() and not 1 <= int(m.group(1)) <= 100:
        return [Err(layer="grammar", line=c.line_no, found=m.group(1) + "%",
                    message="OVERRIDE must be between 1% and 100%.")]
    return []


FAMILIES["OVERRIDE"] = walk_override
KEYWORDS = sorted(k for k in FAMILIES if k not in ("=", "ELSE"))

_LEAD = re.compile(r"([A-Z_]+|=)")
_BODY_LINE = re.compile(r"^\s*(\d+)\s*:(.*?);\s*$")


def _leading_family(content: str) -> str | None:
    m = _LEAD.match(content)
    if not m:
        return None
    word = m.group(1)
    if word in FAMILIES:
        # bare keyword or one that continues legally ([, =, whitespace)
        nxt = content[m.end():m.end() + 1]
        if word in ("J", "L", "C") and nxt not in (" ", ""):
            return None
        return word
    return None


def check(text: str) -> tuple[list[Err], dict]:
    """Envelope + per-line walks. Returns (errors, stats)."""
    errors: list[Err] = []
    lines = [l.rstrip("\r") for l in text.splitlines()]

    def find(marker: str, exact: bool = True):
        return next((i for i, l in enumerate(lines)
                     if (l.strip() == marker if exact
                         else l.strip().startswith(marker))), None)

    prog = find("/PROG", exact=False)
    mn = find("/MN")
    pos_ = find("/POS")                    # optional: PR-only programs omit it
    end = find("/END")
    missing = [m for m, i in (("/PROG", prog), ("/MN", mn), ("/END", end))
               if i is None]
    ordered = [i for i in (prog, mn, pos_, end) if i is not None]
    if missing or ordered != sorted(ordered):
        errors.append(Err(
            layer="grammar", line=1,
            message="The program must be wrapped as /PROG <name> ... /MN "
                    "... [/POS ...] /END, in that order"
                    + (f" (missing: {', '.join(missing)})" if missing else "")
                    + "."))
        return errors, {"mn_lines": 0, "parsed_ok": 0}

    pos_ = pos_ if pos_ is not None else end
    mn_lines = 0
    bad_lines = set()
    for i in range(mn + 1, pos_):
        raw = lines[i]
        if not raw.strip():
            continue
        m = _BODY_LINE.match(raw)
        if not m:
            mn_lines += 1
            bad_lines.add(i + 1)
            errors.append(Err(layer="grammar", line=i + 1, found=raw.strip(),
                              expected="<n>: <instruction> ;"))
            continue
        mn_lines += 1
        mn_no = int(m.group(1))
        content = m.group(2).strip()
        if not content or content.startswith("!"):
            continue
        if re.search(r":\s*\]", content):
            errors.append(Err(
                layer="grammar", line=mn_no, found=content,
                message="There is an empty label after ':' inside brackets "
                        "- write PR[10,3] for an element, or PR[10:note] "
                        "with a real note."))
            bad_lines.add(i + 1)
            continue
        family = _leading_family(content)
        if family is None:
            found = content.split()[0]
            errors.append(Err(
                layer="grammar", line=mn_no, col=1, found=found,
                expected=KEYWORDS,
                suggestion=suggest(found, KEYWORDS)))
            bad_lines.add(i + 1)
            continue
        line_errs = FAMILIES[family](Cursor(mn_no, content))
        if line_errs:
            bad_lines.add(i + 1)
        errors.extend(line_errs)

    return errors, {"mn_lines": mn_lines, "parsed_ok": mn_lines - len(bad_lines)}
