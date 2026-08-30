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
from io import StringIO

from tpagent.config import ROOT
from tpagent.reg_io import RegIOTable, SchemaError, parse_reg_io_csv

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


def materialize(cell_id: str, scan_csv: str | None = None) \
        -> tuple[RegIOTable, str]:
    """Source hierarchy: uploaded scan > bundled default > empty robot."""
    if scan_csv is not None and not scan_csv.strip():
        scan_csv = None                 # a blank scan means "no scan sent"
    if scan_csv:
        return _load(scan_csv, cell_id), "scan"

    try:
        raw = DEFAULT_TABLE.read_text(encoding="utf-8")
        return _load(raw, cell_id), "default_table"
    except (OSError, SchemaError):
        # best-effort rung: a broken or foreign default file is not the
        # requester's fault - fall through to the empty robot
        return RegIOTable(cell_id=cell_id, scanned_at=""), "none"
