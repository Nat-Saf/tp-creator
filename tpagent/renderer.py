"""renderer.py -- deterministic prompt assembly (SOFTWARE.md 6.5).

Fixed section order: SYSTEM -> CELL -> DOCS -> EXAMPLE? -> TASK -> NOTES
-> PREVIOUS+FIX (retry only). Byte-identical for identical inputs
(snapshot-tested). No LLM calls, no network, no randomness.

No-leakage rule in code: render() takes the table and config straight
from the stores; GenerateArgs has NO field that could carry them, so
LLM #1's output can never smuggle a fake register list to LLM #2.

Owner-accepted deviation from Figure 2 (2026-08-30): the SYSTEM template
carries a canonical program skeleton and hard syntax rules in addition
to the retrieved DOCS - live gpt-5-mini runs proved the fixed skeleton
prevents malformed output, so it stays as belt-and-braces alongside the
now-mandatory retrieval.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    undefined=StrictUndefined, autoescape=False,
    trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=False)


@dataclass
class GenerateArgs:
    params: dict
    program_name: str
    notes: list = field(default_factory=list)
    chunks: list = field(default_factory=list)      # retrieved doc texts
    base_draft: str | None = None                   # retry: previous draft id
    errors: list = field(default_factory=list)      # retry: validator errors
    fix_guidance: str | None = None


@dataclass
class RenderSession:
    """The runtime-built view of session state the renderer may read."""
    example_ls: str | None = None
    drafts: dict = field(default_factory=dict)      # draft_id -> text
    previous_ls: str | None = None    # edit turns: the delivered program
                                      # (from the REQUEST, never from LLM #1)


def _table_block(table) -> str:
    lines = []
    for e in table.entries:
        note = e.comment or "(no label)"
        flag = "" if e.initialized is not False else " (uninitialized)"
        lines.append(f"{e.type}[{e.index}] {note}{flag}")
    return "\n".join(lines)


def _kv_block(d: dict) -> str:
    return "\n".join(f"  {k}: {d[k]}" for k in sorted(d))


def render(cfg: dict, table, sess: RenderSession, args: GenerateArgs) -> str:
    sections = [
        _ENV.get_template("system.j2").render(),
        _ENV.get_template("cell.j2").render(
            cell_id=table.cell_id if table is not None else "(unknown)",
            defaults=_kv_block(cfg.get("defaults", {})),
            limits=_kv_block(cfg.get("limits", {})),
            registers=_table_block(table) if table is not None
            and table.entries else ""),
    ]
    if args.chunks:
        sections.append(_ENV.get_template("docs.j2").render(
            chunks="\n\n".join(args.chunks)))
    if sess.example_ls:
        sections.append(_ENV.get_template("example.j2").render(
            example_ls=sess.example_ls))
    if sess.previous_ls:
        sections.append(_ENV.get_template("edit.j2").render(
            previous_ls=sess.previous_ls))
    sections.append(_ENV.get_template("task.j2").render(
        params=_kv_block(args.params)))
    sections.append(_ENV.get_template("notes.j2").render(
        program_name=args.program_name,
        notes="\n".join(f"  - {n}" for n in args.notes)))
    if args.base_draft is not None:
        sections.append(_ENV.get_template("retry.j2").render(
            base_draft=sess.drafts.get(args.base_draft, "(draft not found)"),
            errors=json.dumps(args.errors, indent=2, sort_keys=True),
            fix_guidance=args.fix_guidance or ""))
    return "\n\n".join(s.strip("\n") for s in sections) + "\n"
