"""validator/limits.py -- numeric checks vs static config (layer 3)."""
from __future__ import annotations

import re

from tpagent.validator.verdict import Err

# every linear unit the grammar accepts, converted to mm/sec so no unit
# can bypass the cap (1 cm/min = 10/60 mm/sec; 1 inch/min = 25.4/60)
_SPEED = re.compile(r"\b(\d+(?:\.\d+)?)(mm/sec|cm/min|inch/min)\b")
_TO_MMSEC = {"mm/sec": 1.0, "cm/min": 10.0 / 60.0, "inch/min": 25.4 / 60.0}
_WAIT = re.compile(r"\bWAIT\s+(\d*\.?\d+)(?:\(sec\)|sec)")


def check(text: str, limits: dict) -> list[Err]:
    from tpagent.validator.verdict import mn_body

    max_speed = limits.get("max_speed_mmsec")
    max_wait = limits.get("max_wait_sec")
    errors: list[Err] = []
    for line_no, line in mn_body(text):
        if line.startswith("!"):
            continue
        for m in _SPEED.finditer(line):
            raw = float(m.group(1))
            if raw <= 0:
                errors.append(Err(
                    layer="limits", line=line_no, found=m.group(0),
                    message="A motion speed must be greater than zero."))
                continue
            mmsec = raw * _TO_MMSEC[m.group(2)]
            if max_speed is not None and mmsec > max_speed:
                about = ("" if m.group(2) == "mm/sec"
                         else f" (about {mmsec:.0f}mm/sec)")
                errors.append(Err(
                    layer="limits", line=line_no,
                    found=m.group(0),
                    message=f"{m.group(0)}{about} exceeds this cell's "
                            f"maximum of {max_speed}mm/sec."))
        if max_wait is not None:
            for m in _WAIT.finditer(line):
                if float(m.group(1)) > max_wait:
                    errors.append(Err(
                        layer="limits", line=line_no,
                        found=f"WAIT {m.group(1)}",
                        message=f"A {m.group(1)} second wait exceeds this "
                                f"cell's maximum of {max_wait} seconds."))
    return errors
