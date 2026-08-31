"""stores/table.py -- table sources: upload > bundled default > none.

Single-parser rule: this module is reg_io.py's only importer.

Owner decision (2026-08-30, supersedes DESIGN.md 2c rows 2-3 AND the
earlier Supabase cache): there is NO table cache and no staleness
window. The caller sends its table CSV with every request (the GUI
re-attaches the loaded file each turn); with no upload, the bundled
config/default_table.csv is the cell's table; if that file is missing,
unreadable, or names a different cell, the robot is treated as EMPTY
(any index usable - the runtime passes table=None to the validator).

Bare CSVs (a header row with type,index and optionally comment,
initialized, value - no '#' meta lines) are normalized to the reg_io_v1
wire format here, BEFORE the single parser; strict reg_io_v1 files pass
through verbatim and must name the request's cell.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from functools import lru_cache
from io import StringIO

from tpagent.config import ROOT
from tpagent.reg_io import (IO_DIR, REG_TYPES, Entry, RegIOTable,
                            SchemaError, parse_reg_io_csv, to_reg_io_csv)

to_csv = to_reg_io_csv        # single-parser rule: re-exported, not re-imported

DEFAULT_TABLE = ROOT / "config" / "default_table.csv"

_COLUMNS = ["type", "index", "comment", "initialized", "value"]
_PAD = {"comment": "", "initialized": "TRUE", "value": ""}


def normalize_scan(raw: str, cell_id: str) -> str:
    """Turn a bare CSV into reg_io_v1 text; strict files pass verbatim."""
    if any(line.strip().lower().startswith("# schema:")
           for line in raw.splitlines()):
        return raw

    rows = [r for r in csv.reader(StringIO(raw))
            if any(cell.strip() for cell in r)]
    if not rows:
        raise SchemaError(
            "The table file is empty. It needs a header row with at least "
            "'type' and 'index' columns, then one row per register or IO "
            "point.")
    header = [cell.strip().lower() for cell in rows[0]]
    if "type" not in header or "index" not in header:
        raise SchemaError(
            "The table file needs at least 'type' and 'index' columns "
            "(plus optional comment, initialized and value). Can you check "
            "the file's header row?")
    missing = [c for c in _COLUMNS if c not in header]

    out = StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header + missing)
    for row in rows[1:]:
        row = row + [""] * (len(header) - len(row))     # ragged rows
        writer.writerow(row[:len(header)] + [_PAD[c] for c in missing])

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return (f"# schema: reg_io_v1\n# cell_id: {cell_id}\n"
            f"# scanned_at: {now}\n" + out.getvalue())


def _load(raw: str, cell_id: str) -> RegIOTable:
    table = parse_reg_io_csv(normalize_scan(raw, cell_id))
    if table.cell_id != cell_id:            # a map never crosses cells (2c)
        raise SchemaError(
            f"The registers and IO map you sent belongs to cell "
            f"'{table.cell_id}', but this request is for cell '{cell_id}'. "
            f"Please export the table for the right cell.")
    return table


def parse_scan(raw_csv: str) -> RegIOTable:
    """Parse a strict reg_io_v1 CSV (CLI/tests convenience).

    Lives here so the single-parser rule holds: stores/table.py stays
    reg_io.py's only importer.
    """
    return parse_reg_io_csv(raw_csv)


def with_additions(table: RegIOTable, additions: list) \
        -> tuple[RegIOTable, list[Entry], list[str]]:
    """Owner decision (2026-08-31): on an EXPLICIT user request the agent
    may ADD new entries to the working table for this run. Existing
    indexes are NEVER overridden, and nothing is written back to any
    table file - the advisory tells the user to add the row for keeps.

    Returns (table', accepted entries, refusal notes). The input table
    is never mutated - the default table is a shared cached object."""
    taken = table.key_set()
    accepted: list[Entry] = []
    refused: list[str] = []
    for raw in additions:
        if not isinstance(raw, dict):
            continue
        t = str(raw.get("type") or "").strip().upper()
        try:
            idx = int(raw.get("index"))
        except (TypeError, ValueError):
            idx = None
        if t in REG_TYPES:
            cat, direction, init = "REG", None, False    # new = untaught
        elif t in IO_DIR:
            cat, direction, init = "IO", IO_DIR[t], None
        else:
            refused.append(
                f"I couldn't add '{raw.get('type')}' to the table - I "
                f"don't recognize that entry type.")
            continue
        if idx is None or idx < 1:
            refused.append(
                f"I couldn't add {t}[{raw.get('index')}] - the index must "
                f"be a positive number.")
            continue
        if (t, idx) in taken:
            refused.append(
                f"{t}[{idx}] already exists in your table, so I kept the "
                f"existing entry - loaded rows are never overwritten.")
            continue
        taken.add((t, idx))
        accepted.append(Entry(
            type=t, index=idx,
            comment=str(raw.get("comment") or "").strip(),
            initialized=init, value=str(raw.get("value") or "").strip(),
            category=cat, direction=direction))
    if not accepted:
        return table, [], refused
    merged = RegIOTable(cell_id=table.cell_id, scanned_at=table.scanned_at,
                        entries=[*table.entries, *accepted],
                        flags=list(table.flags))
    return merged, accepted, refused


@lru_cache(maxsize=8)
def _default_table(path: str, mtime: float,
                   cell_id: str) -> RegIOTable | None:
    """Parse-once cache of the bundled default table, keyed on the file's
    path+mtime so an edited file is picked up without a restart. The
    returned table is SHARED across requests - every consumer treats it
    read-only."""
    try:
        return _load(DEFAULT_TABLE.read_text(encoding="utf-8"), cell_id)
    except (OSError, SchemaError):
        # best-effort rung: a broken or foreign default file is not the
        # requester's fault - fall through to the empty robot
        return None


def materialize(cell_id: str, scan_csv: str | None = None) \
        -> tuple[RegIOTable, str]:
    """Source hierarchy: uploaded scan > bundled default > empty robot."""
    if scan_csv is not None and not scan_csv.strip():
        scan_csv = None                 # a blank scan means "no scan sent"
    if scan_csv:
        return _load(scan_csv, cell_id), "scan"

    try:
        mtime = DEFAULT_TABLE.stat().st_mtime
    except OSError:
        mtime = None
    table = (_default_table(str(DEFAULT_TABLE), mtime, cell_id)
             if mtime is not None else None)
    if table is not None:
        return table, "default_table"
    return RegIOTable(cell_id=cell_id, scanned_at=""), "none"
