"""reg_io.py -- parser for the reg_io_v1 CSV interchange format (Appendix A).

Single parser rule: the caller relays the CSV verbatim; only the unit's runtime
parses it. Derived fields (category, direction) are computed here, never stored
in the file, so they can never contradict the type column.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import csv, io

IO_DIR = {t: "in" for t in ("DI", "RI", "UI", "SI", "GI", "AI")} | \
         {t: "out" for t in ("DO", "RO", "UO", "SO", "GO", "AO")}
REG_TYPES = {"R", "PR", "SR", "PL"}


@dataclass
class Entry:
    type: str
    index: int
    comment: str
    initialized: bool | None     # None for IO / unknown
    value: str
    category: str                # REG | IO | UNKNOWN
    direction: str | None        # in | out | None


@dataclass
class RegIOTable:
    cell_id: str
    scanned_at: str
    entries: list[Entry] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)   # non-fatal parser observations

    def find(self, type_: str, index: int) -> Entry | None:
        return next((e for e in self.entries if e.type == type_ and e.index == index), None)

    def by_note(self, needle: str, type_: str | None = None) -> list[Entry]:
        needle = needle.lower()
        return [e for e in self.entries
                if needle in e.comment.lower()
                and (type_ is None or e.type == type_)
                and (e.initialized is not False)]

    def key_set(self) -> set[tuple[str, int]]:
        return {(e.type, e.index) for e in self.entries}


class SchemaError(ValueError):
    """Raised when the CSV is not a valid reg_io_v1 file -> level-A reject."""


def parse_reg_io_csv(raw: str) -> RegIOTable:
    meta: dict[str, str] = {}
    body_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("#"):
            if ":" in line and not line.startswith("# notes"):
                k, v = line[1:].split(":", 1)
                meta[k.strip()] = v.strip()
        elif line.strip():
            body_lines.append(line)

    if meta.get("schema") != "reg_io_v1":
        raise SchemaError(
            "The IO and registers map you sent isn't in the reg_io_v1 format "
            "(missing or wrong '# schema:' header). Can you re-export it from the "
            "robot scan tool?")
    if "cell_id" not in meta or "scanned_at" not in meta:
        raise SchemaError(
            "The IO and registers map is missing its '# cell_id' or '# scanned_at' "
            "header, so I can't verify which cell it belongs to or how fresh it is.")

    table = RegIOTable(cell_id=meta["cell_id"], scanned_at=meta["scanned_at"])
    reader = csv.DictReader(io.StringIO("\n".join(body_lines)))
    required = {"type", "index", "comment", "initialized", "value"}
    if set(reader.fieldnames or []) < required:
        raise SchemaError(
            f"The map's header row must contain {sorted(required)}; "
            f"got {reader.fieldnames}.")

    for n, row in enumerate(reader, start=2):
        t = (row["type"] or "").strip()
        if t in REG_TYPES:
            cat, direction = "REG", None
            init = (row["initialized"] or "").strip().upper() == "TRUE"
        elif t in IO_DIR:
            cat, direction, init = "IO", IO_DIR[t], None
        else:
            cat, direction, init = "UNKNOWN", None, None
            table.flags.append(f"row {n}: unknown type '{t}' kept but flagged")
        try:
            idx = int(row["index"])
        except (TypeError, ValueError):
            table.flags.append(f"row {n}: non-numeric index '{row['index']}' skipped")
            continue
        table.entries.append(Entry(
            type=t, index=idx, comment=(row["comment"] or "").strip(),
            initialized=init, value=(row["value"] or "").strip(),
            category=cat, direction=direction))
    return table
