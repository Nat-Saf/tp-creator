"""StepsRecorder -- the graded steps[] trace.

Every LLM-provider call (chat AND embeddings) appends
{"module": <registry name>, "prompt": {...}, "response": {...}} in call
order. The recorder is a constructor dependency of LLMClient, and the
module name is validated against tpagent/modules.py -- so a step can
neither bypass the trace nor carry an off-registry name.
"""
from __future__ import annotations

import copy

from tpagent.modules import REGISTRY


class StepsRecorder:
    def __init__(self):
        self._steps: list[dict] = []

    def record(self, module: str, prompt: dict, response: dict) -> None:
        if module not in REGISTRY:
            raise ValueError(
                f"'{module}' is not a registry module name; use the "
                f"constants in tpagent.modules: {list(REGISTRY)}")
        if not isinstance(prompt, dict) or not isinstance(response, dict):
            raise ValueError("a step's prompt and response must be dicts "
                             "(the graded steps[] schema)")
        self._steps.append({"module": module,
                            "prompt": copy.deepcopy(prompt),
                            "response": copy.deepcopy(response)})

    @property
    def steps(self) -> list[dict]:
        return copy.deepcopy(self._steps)

    def __len__(self) -> int:
        return len(self._steps)
