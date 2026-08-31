"""validator/existence.py -- symbol refs vs the cell's table (layer 2).

Set membership only, never note interpretation. Outcomes per unique
reference: ok | not_in_table (blocking Err, known same-type set
attached) | exists_uninitialized (a WARNING sentence, not an error).

Owner decisions (2026-08-29, supersede DESIGN.md 4.9 on these points):
- table=None means "empty robot" -> the layer is skipped entirely.
- An uninitialized-but-existing register no longer blocks: writing the
  program before teaching the pose is the real workshop workflow. The
  warning (with a did-you-mean when the inline label matches a taught
  entry's note) reaches the human as a report advisory instead.
- (2026-08-31) SEEDING an untaught destination blocks: copying another
  PR into an untaught PR and then moving to it (with no element
  arithmetic in between - that pattern is the sanctioned relative-move
  scratch idiom) defeats teaching; the pose must come from the pendant.
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


def _seeded_destination(body: str, idx: int) -> bool:
    """PR[idx]=PR[j] + a move to PR[idx] + NO PR[idx,e]=... element line
    == seeding an untaught destination (the element line is what makes
    the legitimate relative-move scratch idiom)."""
    return (re.search(rf"PR\[{idx}(?::[^\]]*)?\]\s*=\s*PR\[", body)
            is not None
            and re.search(rf"\b[JL]\s+PR\[{idx}[,:\]]", body) is not None
            and re.search(rf"PR\[{idx}\s*,\s*\d", body) is None)


def check(text: str, table) -> tuple[list[Err], list[str]]:
    """table is a stores RegIOTable (duck-typed: find/by_note/entries).
    Returns (blocking errors, uninitialized-reference warnings)."""
    if table is None:
        return [], []
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

    body = "\n".join(c for _, c in mn_body(text)
                     if not c.startswith("!"))
    errors: list[Err] = []
    warnings: list[str] = []
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
            if type_ == "PR" and _seeded_destination(body, idx):
                errors.append(Err(
                    layer="existence", line=line_no, ref=ref,
                    message=f"{ref} is untaught and used as a move target, "
                            f"but the program copies another position into "
                            f"it first - remove that line; the operator "
                            f"teaches {ref} on the pendant, the program "
                            f"just moves to it."))
                continue
            hit = (next((e for e in table.by_note(label, type_)), None)
                   if label else None)
            if hit:
                warnings.append(
                    f"{ref} is labeled '{label}' in the program but isn't "
                    f"taught yet - did you mean {type_}[{hit.index}] "
                    f"'{hit.comment}'? If {ref} is intentional, teach it "
                    f"on the pendant before running.")
            else:
                warnings.append(
                    f"{ref} is referenced but not yet taught "
                    f"(uninitialized) - teach it on the pendant before "
                    f"running this program.")
    return errors, warnings
