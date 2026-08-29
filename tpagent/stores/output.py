"""stores/output.py -- the deliverables (guide Part 1.2 outputs table).

Replaces out/<sid>/<PROGRAM>_vN.ls + report.json; file_ref becomes the
logical "outputs/<draft_id>".
"""
from __future__ import annotations

from tpagent.stores.client import get_client


def save(session_id: str, draft_id: str, program_name: str,
         ls_text: str, report: dict, *, client=None) -> str:
    client = client or get_client()
    client.table("outputs").upsert(
        {"draft_id": draft_id, "session_id": session_id,
         "program_name": program_name, "ls_text": ls_text,
         "report": report}).execute()
    return f"outputs/{draft_id}"


def load(draft_id: str, *, client=None) -> dict | None:
    client = client or get_client()
    rows = (client.table("outputs").select("*")
            .eq("draft_id", draft_id).limit(1).execute().data)
    return rows[0] if rows else None
