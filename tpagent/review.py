"""review.py -- the mandatory audit turn (SOFTWARE.md 6.4).

Same LLM #1 client, fresh prompt, module LLM1-Audit. Output is a list of
friendly advisory sentences; it can never block - parse trouble yields a
single advisory, and the runtime treats everything here as report
content only. Audit findings never withhold delivery.
"""
from __future__ import annotations

import json

from tpagent import llm1, modules
from tpagent.llm_client import LLMClient

_AUDIT_SYSTEM = """You are auditing a FANUC TP program that already passed a
deterministic validator. Judge SEMANTICS only: does the program plausibly do
what the task params say, are approach/retreat moves sensible, did the
effective defaults and any user-requested values actually land in the code
(speeds, settle times, frames), is anything risky worth a human look? You
cannot block delivery.

Reply with ONE JSON object, nothing else:
{"advisories": ["<plain, friendly, self-contained sentence>", ...]}
Return an empty list when nothing is worth flagging. At most 3 advisories."""


def semantic_audit(program: str, params: dict, table, llm: LLMClient,
                   effective_defaults: dict | None = None) -> list[str]:
    payload = {"program": program, "params": params,
               "effective_defaults": effective_defaults or {},
               "table_notes": llm1.table_view(table)}
    raw = llm.chat(modules.LLM1_AUDIT, [
        {"role": "system", "content": _AUDIT_SYSTEM},
        {"role": "user", "content": json.dumps(payload, sort_keys=True)},
    ], role="llm1")
    try:
        advisories = llm1.parse_advisories(raw)
    except ValueError:
        return ["The automatic review couldn't be read this time - please "
                "give the program a quick manual look."]
    return advisories
