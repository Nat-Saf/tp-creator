"""Record/replay in-memory stand-in for the supabase client.

Backs each table with a list of dict rows and supports exactly the
query-builder surface the stores layer uses:
    table(name).select(...).eq(col, val).limit(n).execute().data
    table(name).insert(row).execute().data
    table(name).upsert(row).execute()
    table(name).update(fields).eq(col, val).execute()
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

PRIMARY_KEYS = {
    "reg_io_tables": "cell_id",
    "sessions": "id",
    "drafts": "id",
    "verdicts": "draft_id",
    "outputs": "draft_id",
}


@dataclass
class _Result:
    data: list


@dataclass
class _Query:
    store: "MockSupabase"
    name: str
    op: str = "select"
    payload: dict | None = None
    filters: list = field(default_factory=list)
    _limit: int | None = None

    def select(self, *_cols) -> "_Query":
        self.op = "select"
        return self

    def insert(self, row: dict) -> "_Query":
        self.op, self.payload = "insert", dict(row)
        return self

    def upsert(self, row: dict) -> "_Query":
        self.op, self.payload = "upsert", dict(row)
        return self

    def update(self, fields: dict) -> "_Query":
        self.op, self.payload = "update", dict(fields)
        return self

    def eq(self, col: str, val) -> "_Query":
        self.filters.append((col, val))
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def _matching(self, rows: list[dict]) -> list[dict]:
        return [r for r in rows
                if all(str(r.get(c)) == str(v) for c, v in self.filters)]

    def execute(self) -> _Result:
        rows = self.store.data.setdefault(self.name, [])
        if self.op == "select":
            hits = self._matching(rows)
            if self._limit is not None:
                hits = hits[:self._limit]
            return _Result([dict(r) for r in hits])
        if self.op == "insert":
            row = dict(self.payload)
            pk = PRIMARY_KEYS.get(self.name)
            if pk and pk not in row:
                row[pk] = str(uuid.uuid4())
            if self.name == "sessions":   # column defaults from the DDL
                row.setdefault("params", {})
                row.setdefault("inferred", [])
                row.setdefault("decisions", [])
                row.setdefault("pending_question", None)
            rows.append(row)
            return _Result([dict(row)])
        if self.op == "upsert":
            pk = PRIMARY_KEYS[self.name]
            row = dict(self.payload)
            for i, r in enumerate(rows):
                if str(r.get(pk)) == str(row.get(pk)):
                    rows[i] = {**r, **row}
                    return _Result([dict(rows[i])])
            rows.append(row)
            return _Result([dict(row)])
        if self.op == "update":
            hits = self._matching(rows)
            for r in hits:
                r.update(self.payload)
            return _Result([dict(r) for r in hits])
        raise NotImplementedError(self.op)


@dataclass
class MockSupabase:
    data: dict = field(default_factory=dict)   # table name -> list[dict rows]

    def table(self, name: str) -> _Query:
        return _Query(self, name)
