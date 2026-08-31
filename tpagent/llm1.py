"""llm1.py -- the orchestrator's intake/strategy calls (SOFTWARE.md 6.4).

LLM #1 decides strategy (params, retries, questions); the RUNTIME owns
the loop mechanics. This module builds the context messages and turns
one completion into a validated action dict. Structured output only:
free text is a protocol error - the runtime rejects and retries once.

No RAG chunk ever enters LLM #1's context: a rag_retrieve result is
acknowledged with a count only; the chunks route to the renderer.
"""
from __future__ import annotations

import json
from pathlib import Path

from tpagent import modules
from tpagent.llm_client import LLMClient

ACTIONS = {"rag_retrieve", "generate_program", "ask_user", "reject",
           "edit_table"}
_SYSTEM = (Path(__file__).parent / "prompts" / "llm1_system.md")


class ProtocolError(RuntimeError):
    """LLM #1 answered outside the JSON protocol."""


def system_prompt() -> str:
    return _SYSTEM.read_text(encoding="utf-8")


def table_view(table) -> list[dict]:
    if table is None:
        return []
    return [{"ref": f"{e.type}[{e.index}]", "note": e.comment,
             "initialized": e.initialized} for e in table.entries]


def initial_messages(prompt: str, table, source: str, cfg: dict,
                     example_attached: bool,
                     answers: dict | None = None,
                     previous_attached: bool = False) -> list[dict]:
    context = {
        "prompt": prompt,
        "table": {"source": source, "entries": table_view(table)},
        "effective_defaults": cfg.get("defaults", {}),
        "limits": cfg.get("limits", {}),
        "example_attached": example_attached,
        "previous_program_attached": previous_attached,
    }
    if answers:
        context["answers"] = answers
    return [{"role": "system", "content": system_prompt()},
            {"role": "user", "content": json.dumps(context, sort_keys=True)}]


def parse_action(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        action = json.loads(text)
    except ValueError:
        raise ProtocolError("not valid JSON")
    if not isinstance(action, dict) or action.get("action") not in ACTIONS:
        raise ProtocolError(f"unknown action in {text[:80]!r}")
    return action


def parse_advisories(text: str) -> list[str]:
    return parse_audit(text)[0]


def parse_audit(text: str) -> tuple[list[str], str | None]:
    """Audit reply -> (advisories, must_fix). must_fix is the one hard
    contradiction the auditor wants corrected, or None."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    data = json.loads(text)               # ValueError on bad JSON
    advisories = data.get("advisories") if isinstance(data, dict) else None
    if not isinstance(advisories, list):
        raise ValueError("no advisories list")
    must_fix = data.get("must_fix") if isinstance(data, dict) else None
    must_fix = str(must_fix).strip() if must_fix else None
    return [str(a) for a in advisories][:3], must_fix or None


def decide(llm: LLMClient, messages: list[dict]) -> tuple[dict, str]:
    """One intake turn; returns (action, raw_reply). Retries the protocol
    once by appending a correction, then raises ProtocolError."""
    raw = llm.chat(modules.LLM1_INTAKE, messages, role="llm1")
    try:
        return parse_action(raw), raw
    except ProtocolError:
        retry = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content":
                "Protocol error: reply with exactly ONE JSON object per the "
                "output protocol, nothing else. Continue the task as if "
                "nothing happened - never mention this correction, formats "
                "or JSON in any text the user will read."}]
        raw = llm.chat(modules.LLM1_INTAKE, retry, role="llm1")
        return parse_action(raw), raw
