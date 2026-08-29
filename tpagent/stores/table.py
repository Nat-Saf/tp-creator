"""stores/table.py -- the 2c source hierarchy: scan > cache > none.

Single-parser rule: this module is reg_io.py's only importer.
The cache is the reg_io_tables row for the cell (guide Part 1.2): the
entries column holds {"entries": [...], "flags": [...]} so a cached
RegIOTable round-trips losslessly, staleness measured from the row's
scanned_at against static_config table.max_table_age_hours.

Owner decision (2026-08-29, replaces DESIGN.md 2c row 3): there is no
default_index_map. No scan and no fresh cache => source "none" with an
empty table - the robot is treated as empty, any index is usable, and
the validator skips its existence layer (runtime passes table=None).
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from tpagent.config import static_config
from tpagent.reg_io import Entry, RegIOTable, parse_reg_io_csv
from tpagent.stores.client import get_client

TABLE = "reg_io_tables"




def _age_hours(scanned_at: str) -> float | None:
    try:
        dt = datetime.fromisoformat(scanned_at)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)


def _fmt_age(hours: float) -> str:
    if hours < 1:
        return f"{int(hours * 60)}m"
    if hours < 48:
        return f"{int(round(hours))}h"
    return f"{int(hours // 24)}d"


def _rehydrate(row: dict) -> RegIOTable:
    payload = row.get("entries") or {}
    return RegIOTable(
        cell_id=row["cell_id"],
        scanned_at=row.get("scanned_at") or "",
        entries=[Entry(**e) for e in payload.get("entries", [])],
        flags=list(payload.get("flags", [])))


def parse_scan(raw_csv: str) -> RegIOTable:
    """Parse a reg_io_v1 CSV without persisting (CLI/tests convenience).

    Lives here so the single-parser rule holds: stores/table.py stays
    reg_io.py's only importer.
    """
    return parse_reg_io_csv(raw_csv)


def cache_scan(cell_id: str, raw_csv: str, *, source: str = "scan",
               scanned_at: str | None = None, client=None) -> tuple[RegIOTable, dict]:
    """Parse a reg_io_v1 CSV and persist it as the cell's cache row.

    scanned_at overrides the CSV's own header timestamp (the seed stamps
    delivery time so the demo cell starts fresh); the parsed table carries
    whatever the row records.
    """
    client = client or get_client()
    table = parse_reg_io_csv(raw_csv)
    table.cell_id = cell_id
    if scanned_at is not None:
        table.scanned_at = scanned_at
    row = {
        "cell_id": cell_id,
        "scanned_at": table.scanned_at,
        "source": source,
        "entries": {"entries": [asdict(e) for e in table.entries],
                    "flags": list(table.flags)},
    }
    client.table(TABLE).upsert(row).execute()
    return table, row


def materialize(cell_id: str, scan_csv: str | None = None, *,
                client=None, config: dict | None = None) -> tuple[RegIOTable, str]:
    """Source hierarchy: scan > fresh cache > "none" (empty robot)."""
    client = client or get_client()
    cfg = config if config is not None else static_config()

    if scan_csv:
        table, _ = cache_scan(cell_id, scan_csv, client=client)
        return table, "scan"

    rows = (client.table(TABLE).select("*")
            .eq("cell_id", cell_id).limit(1).execute().data)
    if rows:
        max_age = (cfg.get("table") or {}).get("max_table_age_hours", 72)
        age = _age_hours(rows[0].get("scanned_at") or "")
        if age is not None and age <= max_age:
            return _rehydrate(rows[0]), f"cache({_fmt_age(age)})"

    return RegIOTable(cell_id=cell_id, scanned_at=""), "none"
