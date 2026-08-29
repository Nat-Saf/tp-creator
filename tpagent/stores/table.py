"""stores/table.py -- the 2c source hierarchy: scan > cache > default_map.

Single-parser rule: this module is reg_io.py's only importer.
The cache is the reg_io_tables row for the cell (guide Part 1.2): the
entries column holds {"entries": [...], "flags": [...]} so a cached
RegIOTable round-trips losslessly, staleness measured from the row's
scanned_at against static_config table.max_table_age_hours.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import yaml

from tpagent.reg_io import IO_DIR, Entry, RegIOTable, parse_reg_io_csv
from tpagent.stores.client import get_client

TABLE = "reg_io_tables"
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "static_config.yaml"


class NoTableSource(Exception):
    """No scan, no fresh cache, no default map -> friendly ask upstream."""


@lru_cache(maxsize=1)
def _static_config() -> dict:
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}


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


def _synthetic_table(cell_id: str, index_map: dict) -> RegIOTable:
    entries = []
    for idx, note in (index_map.get("PR") or {}).items():
        entries.append(Entry(type="PR", index=int(idx), comment=str(note),
                             initialized=True, value="",
                             category="REG", direction=None))
    for key, note in (index_map.get("IO") or {}).items():
        t, _, idx = key.partition("[")
        entries.append(Entry(type=t, index=int(idx.rstrip("]")),
                             comment=str(note), initialized=None, value="",
                             category="IO", direction=IO_DIR.get(t)))
    return RegIOTable(cell_id=cell_id, scanned_at="", entries=entries)


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
    """SOFTWARE.md 6.9: scan > cache > default_map, else NoTableSource."""
    client = client or get_client()
    cfg = config if config is not None else _static_config()

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

    index_map = cfg.get("default_index_map") or {}
    if index_map:
        return _synthetic_table(cell_id, index_map), "default_map"

    raise NoTableSource(
        "I don't have a registers and IO map for this cell yet. Please "
        "attach a reg_io_v1 scan export so I know which registers and "
        "IO points exist.")
