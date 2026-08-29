"""validator/verdict.py -- Err/Verdict dataclasses + run() (SOFTWARE.md 6.7).

    run(text, table, limits, mode="gate")            # drafts: all 3 layers
    run(text, table, limits, mode="syntax_report")   # examples: grammar only

    python -m tpagent.validator.verdict <file.ls> [--scan <reg_io.csv>]

Layer modules are imported inside run() so grammar/existence/limits can
import Err from here without a cycle.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_MN_LINE = re.compile(r"^\s*(\d+)\s*:(.*)$")


def mn_body(text: str):
    """Yield (mn_line_no, content) for each numbered /MN body line.

    Error line numbers throughout the validator are these MN numbers -
    the ones LLM #1 sees inside the draft - not file line numbers.
    """
    in_mn = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped == "/MN":
            in_mn = True
            continue
        if stripped in ("/POS", "/END"):   # /POS is optional in PR-only programs
            break
        if not in_mn:
            continue
        m = _MN_LINE.match(raw)
        if m:
            yield int(m.group(1)), m.group(2).strip().rstrip(";").strip()


@dataclass
class Err:
    layer: str                       # grammar | existence | limits
    line: int
    col: int | None = None
    found: str | None = None
    expected: object = None          # token set (list) or form string
    expected_form: str | None = None
    suggestion: str | None = None
    ref: str | None = None
    message: str | None = None
    known: dict | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Verdict:
    verdict: str                     # pass | fail
    errors: list[Err] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"verdict": self.verdict,
                "errors": [e.to_dict() for e in self.errors],
                "stats": self.stats}


def run(text: str, table, limits: dict, mode: str = "gate") -> Verdict:
    from tpagent.validator import existence, grammar
    from tpagent.validator import limits as limits_layer

    errors, stats = grammar.check(text)
    if mode == "gate":
        errors = errors + existence.check(text, table)
        limit_errors = limits_layer.check(text, limits or {})
        errors = errors + limit_errors
        stats["limits_ok"] = not limit_errors
    return Verdict(verdict="pass" if not errors else "fail",
                   errors=errors, stats=stats)


def _friendly(err: Err) -> str:
    where = f"line {err.line}"
    if err.message:
        return f"{where}: {err.message}"
    parts = [f"{where}: '{err.found}' isn't valid here"]
    if err.expected_form:
        parts.append(f"the expected form is {err.expected_form}")
    elif err.expected:
        exp = err.expected if isinstance(err.expected, str) \
            else ", ".join(map(str, err.expected))
        parts.append(f"expected one of: {exp}")
    if err.suggestion:
        parts.append(f"did you mean '{err.suggestion}'?")
    return " - ".join(parts)


def main() -> None:
    import argparse
    import json
    from pathlib import Path

    from tpagent.config import static_config

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path)
    ap.add_argument("--scan", type=Path, default=None,
                    help="reg_io_v1 CSV; without it the robot is treated "
                         "as empty (no existence checks)")
    ap.add_argument("--mode", choices=["gate", "syntax_report"],
                    default="gate")
    args = ap.parse_args()

    table = None
    if args.scan:
        from tpagent.stores.table import parse_scan
        table = parse_scan(args.scan.read_text(encoding="utf-8"))

    verdict = run(args.path.read_text(encoding="utf-8"), table,
                  static_config().get("limits", {}), mode=args.mode)
    print(json.dumps(verdict.to_dict(), indent=2))
    for err in verdict.errors:
        print(_friendly(err))
    if not verdict.errors:
        print("The program passed every check.")


if __name__ == "__main__":
    main()
