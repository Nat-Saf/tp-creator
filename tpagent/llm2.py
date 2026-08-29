"""llm2.py -- single-shot codegen (SOFTWARE.md 6.6).

The provider transport lives in llm_client (backend by TP_LLM2:
llmod:<model> | mock:<path>[,<path>...]). Post-processing here is code:
strip markdown fences, normalize CRLF. A missing /PROG.../END envelope
is NOT a crash - the validator's envelope check turns it into a normal
grammar error on the next hop.
"""
from __future__ import annotations

from dataclasses import dataclass

from tpagent import modules
from tpagent.llm_client import LLMClient


@dataclass
class Draft:
    text: str


def generate(prompt: str, llm: LLMClient) -> Draft:
    raw = llm.chat(modules.LLM2_CODEGEN,
                   [{"role": "user", "content": prompt}], role="llm2")
    text = raw.replace("\r\n", "\n").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return Draft(text=text + "\n")
