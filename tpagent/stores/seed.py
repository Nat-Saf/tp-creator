"""Seed the demo cell into reg_io_tables.

    python -m tpagent.stores.seed [--cell line3_fanuc1] [--csv path]

Parses tests/fixtures/reg_io_v1_template.csv through the table store
(single-parser rule: reg_io stays behind stores/table.py) and upserts it
as the cell's row with source="seed" and scanned_at = now (UTC): seeding
IS the scan delivery event, so the demo cell starts inside the
max_table_age freshness window.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from tpagent.stores import table
from tpagent.stores.client import get_client

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "tests" / "fixtures" / "reg_io_v1_template.csv"


def seed(cell_id: str, csv_path: Path, *, client=None) -> dict:
    client = client or get_client()
    raw = csv_path.read_text(encoding="utf-8")
    scanned_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _, row = table.cache_scan(cell_id, raw, source="seed",
                              scanned_at=scanned_at, client=client)
    return row


def show_row(cell_id: str, *, client=None) -> str:
    client = client or get_client()
    rows = (client.table(table.TABLE).select("*")
            .eq("cell_id", cell_id).limit(1).execute().data)
    if not rows:
        return f"no row for cell '{cell_id}'"
    row = rows[0]
    payload = row.get("entries") or {}
    entries = payload.get("entries", [])
    lines = [
        f"cell_id:    {row['cell_id']}",
        f"scanned_at: {row.get('scanned_at')}",
        f"source:     {row.get('source')}",
        f"entries:    {len(entries)}",
        f"flags:      {payload.get('flags', [])}",
    ]
    for e in entries[:6]:
        note = e["comment"] or "(no comment)"
        lines.append(f"  {e['type']}[{e['index']}] {note}")
    if len(entries) > 6:
        lines.append(f"  ... and {len(entries) - 6} more")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cell", default=os.environ.get("DEMO_CELL", "line3_fanuc1"))
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = ap.parse_args(argv)

    seed(args.cell, args.csv)
    print(f"seeded '{args.cell}' from {args.csv.name}:")
    print(show_row(args.cell))


if __name__ == "__main__":
    main()
