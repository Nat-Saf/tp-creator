"""stores/session.py -- session state on Supabase (guide Part 1.2 tables).

Disk-layout mapping from SOFTWARE.md 6.9:
  drafts/            -> drafts rows (id "<sid8>_vN", n, ls_text)
  verdicts/          -> verdicts rows keyed by draft_id
  params_history +
  decisions.log      -> sessions.decisions jsonb (append-only list)
  example(.ls,_rep)  -> sessions.params keys example_ls / example_report
                        (the course schema has no example columns)
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass

from tpagent.stores.client import get_client


class Session:
    def __init__(self, client, id: str, cell_id: str,
                 revision_of: str | None = None):
        self._client = client
        self.id = id
        self.cell_id = cell_id
        self.revision_of = revision_of

    # ---------- drafts / verdicts ----------
    def save_draft(self, ls_text: str) -> str:
        existing = (self._client.table("drafts").select("id")
                    .eq("session_id", self.id).execute().data)
        n = len(existing) + 1
        draft_id = f"{self.id[:8]}_v{n}"
        self._client.table("drafts").insert(
            {"id": draft_id, "session_id": self.id,
             "n": n, "ls_text": ls_text}).execute()
        return draft_id

    def get_draft(self, draft_id: str) -> dict | None:
        rows = (self._client.table("drafts").select("*")
                .eq("id", draft_id).limit(1).execute().data)
        return rows[0] if rows else None

    def save_verdict(self, draft_id: str, verdict: str,
                     errors: list | None = None,
                     stats: dict | None = None) -> None:
        self._client.table("verdicts").upsert(
            {"draft_id": draft_id, "verdict": verdict,
             "errors": errors or [], "stats": stats or {}}).execute()

    def get_verdict(self, draft_id: str) -> dict | None:
        rows = (self._client.table("verdicts").select("*")
                .eq("draft_id", draft_id).limit(1).execute().data)
        return rows[0] if rows else None

    # ---------- session row state ----------
    def _row(self) -> dict:
        return (self._client.table("sessions").select("*")
                .eq("id", self.id).limit(1).execute().data)[0]

    def _update(self, fields: dict) -> None:
        self._client.table("sessions").update(fields).eq("id", self.id).execute()

    def save_params(self, params: dict) -> None:
        merged = {**self._row().get("params", {}), **params}
        self._update({"params": merged})

    def save_example(self, example_ls: str, report) -> None:
        if is_dataclass(report) and not isinstance(report, type):
            report = asdict(report)   # jsonb column needs plain JSON
        self.save_params({"example_ls": example_ls, "example_report": report})

    def set_pending_question(self, question: str | None) -> None:
        self._update({"pending_question": question})

    def pending_question(self) -> str | None:
        return self._row().get("pending_question")

    def append_inferred(self, item: dict) -> None:
        self._update({"inferred": [*self._row().get("inferred", []), item]})

    def log_decision(self, text: str) -> None:
        self._update({"decisions": [*self._row().get("decisions", []), text]})


def open(cell_id: str, revision_of: str | None = None, *, client=None) -> Session:
    client = client or get_client()
    row = client.table("sessions").insert({"cell_id": cell_id}).execute().data[0]
    sess = Session(client, str(row["id"]), cell_id, revision_of)
    if revision_of:
        sess.log_decision(f"revision_of={revision_of}")
    return sess
