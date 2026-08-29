"""validator/existence.py -- symbol refs vs the cell's table (layer 2).

Set membership only, never note interpretation. Three outcomes per
unique reference: ok | not_in_table (known same-type set attached) |
exists_uninitialized (with a did-you-mean when the ref's inline label
matches a real entry's note).

Owner policy: table=None means "empty robot" -> the layer is skipped.
"""
from __future__ import annotations

import re

from tpagent.validator.verdict import Err

# table-backed symbol types only (P[] is a taught position, not a symbol)
_REF = re.compile(
    r"\b(PR|R|SR|PL|DI|DO|RI|RO|UI|UO|SI|SO|GI|GO|AI|AO|F)"
    r"\[(\d+)(?:\s*,\s*\d+)?(?::([^\]]*))?\]")


def _known(table, type_: str) -> dict:
    return {str(e.index): e.comment for e in table.entries
            if e.type == type_ and e.initialized is not False}


def check(text: str, table) -> list[Err]:
    """table is a stores RegIOTable (duck-typed: find/by_note/entries)."""
    if table is None:
        return []
    from tpagent.validator.verdict import mn_body

    first_seen: dict[tuple, tuple] = {}   # (type, idx) -> (mn line, label)
    for line_no, content in mn_body(text):
        if content.startswith("!"):
            continue
        for m in _REF.finditer(content):
            key = (m.group(1), int(m.group(2)))
            label = (m.group(3) or "").strip()
            if key not in first_seen:
                first_seen[key] = (line_no, label)
            elif label and not first_seen[key][1]:
                # keep the first line but adopt a later occurrence's label
                first_seen[key] = (first_seen[key][0], label)

    errors: list[Err] = []
    for (type_, idx), (line_no, label) in sorted(first_seen.items(),
                                                 key=lambda kv: kv[1][0]):
        entry = table.find(type_, idx)
        ref = f"{type_}[{idx}]"
        if entry is None:
            errors.append(Err(
                layer="existence", line=line_no, ref=ref,
                message=f"{ref} is not in this cell's register map "
                        f"(scan {table.scanned_at or 'unknown'}).",
                known=_known(table, type_)))
        elif entry.initialized is False:
            suggestion = None
            if label:
                hit = next((e for e in table.by_note(label, type_)), None)
                if hit:
                    suggestion = f"{type_}[{hit.index}]"
            note = f" - did you mean {suggestion}?" if suggestion else ""
            errors.append(Err(
                layer="existence", line=line_no, ref=ref,
                message=f"{ref} exists but is uninitialized and "
                        f"unlabeled{note}",
                suggestion=suggestion,
                known=_known(table, type_)))
    return errors
