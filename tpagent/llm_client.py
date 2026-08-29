"""tpagent/llm_client.py -- the ONLY module that talks to the LLM provider.

OpenAI-compatible chat + embeddings against LLMOD_BASE_URL / LLMOD_API_KEY.
Role -> backend comes from TP_LLM1 / TP_LLM2: "llmod:<model>" | "mock:<path>"
(mock returns the file's text as the completion -- free development).
Embeddings use EMBED_MODEL.

The StepsRecorder is a constructor dependency and recording happens inside
chat()/embed() -- including failures -- so no provider call can bypass the
graded trace. Budget rules (CLAUDE.md): temperature 0 always, per-role
max_tokens from static_config, at most 2 retries on transient failures.
"""
from __future__ import annotations

import os
import time

import httpx

from tpagent import config
from tpagent.steps import StepsRecorder

ROLE_ENV = {"llm1": "TP_LLM1", "llm2": "TP_LLM2"}
DEFAULT_MAX_TOKENS = {"llm1": 800, "llm2": 1600}
RETRY_BACKOFF_SEC = 0.5
ATTEMPTS = 3          # 1 try + 2 retries (course cap: retries <= 2)
TIMEOUT_SEC = 60


class LLMClientError(RuntimeError):
    """Provider/config failure. str() is a human-readable sentence (no
    status codes - the language rule); .detail carries the technical
    part for the steps trace."""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


def _require_env(name: str, hint: str) -> str:
    config.load_dotenv()
    value = os.environ.get(name, "").strip()
    if not value:
        raise LLMClientError(
            f"The language model service isn't configured: {name} is not "
            f"set. {hint}")
    return value


def _max_tokens(role: str) -> int:
    cfg = (config.static_config().get("llm") or {}).get("max_tokens") or {}
    return int(cfg.get(role, DEFAULT_MAX_TOKENS[role]))


def _chat_payload(model: str, messages: list[dict], max_tokens: int) -> dict:
    # The LLMod gateway (LiteLLM) rejects temperature!=1 for gpt-5 models
    # and wants max_completion_tokens; reasoning_effort caps the hidden
    # reasoning spend (probed live 2026-08-29). Determinism for gpt-5 comes
    # from prompts, not temperature. Other models keep the course rule.
    if "gpt-5" in model:
        effort = (config.static_config().get("llm") or {}).get(
            "reasoning_effort", "minimal")
        return {"model": model, "messages": messages,
                "max_completion_tokens": max_tokens,
                "reasoning_effort": effort}
    return {"model": model, "messages": messages,
            "temperature": 0, "max_tokens": max_tokens}


class LLMClient:
    def __init__(self, recorder: StepsRecorder, *, transport=None):
        self._recorder = recorder
        self._transport = transport
        self._mock_calls = {"llm1": 0, "llm2": 0}

    # ---------- provider plumbing ----------
    def _base_url(self) -> str:
        base = _require_env("LLMOD_BASE_URL",
                            "Add it to .env (locally) or the Vercel "
                            "dashboard.").rstrip("/")
        return base if base.endswith("/v1") else base + "/v1"

    def _post(self, path: str, payload: dict) -> dict:
        url = self._base_url() + path
        headers = {"Authorization": "Bearer " + _require_env(
            "LLMOD_API_KEY", "Add the group project key to .env (locally) "
            "or the Vercel dashboard.")}
        last = ""
        for attempt in range(ATTEMPTS):
            if attempt:
                time.sleep(RETRY_BACKOFF_SEC)
            try:
                with httpx.Client(timeout=TIMEOUT_SEC, follow_redirects=True,
                                  transport=self._transport) as http:
                    r = http.post(url, json=payload, headers=headers)
            except httpx.HTTPError as e:
                last = str(e) or type(e).__name__
                continue
            if r.status_code == 429 or r.status_code >= 500:   # transient only
                last = f"HTTP {r.status_code}"
                continue
            if r.status_code >= 400:                           # definitive: no retry
                raise LLMClientError(
                    "The language model service rejected the request. "
                    "Please check the API key and model name.",
                    detail=f"HTTP {r.status_code}")
            try:
                return r.json()
            except ValueError:
                last = "the reply wasn't valid JSON"
                continue
        raise LLMClientError(
            "The language model service didn't answer after several "
            "attempts. Please try again in a moment.", detail=last)

    def _recorded_post(self, module: str, path: str, payload: dict) -> dict:
        try:
            data = self._post(path, payload)
        except LLMClientError as e:
            self._recorder.record(module, payload,
                                  {"error": str(e), "detail": e.detail})
            raise
        self._recorder.record(module, payload, data)
        return data

    # ---------- public surface ----------
    def chat(self, module: str, messages: list[dict], *, role: str) -> str:
        """One chat completion for "llm1" | "llm2"; returns the text."""
        env_name = ROLE_ENV[role]
        spec = _require_env(env_name,
                            "Set it to llmod:<model> or mock:<path>.")
        backend, _, arg = spec.partition(":")

        if backend == "mock":
            # mock:<path>[,<path>...] serves the files in call order
            # (the last one repeats) - lets tests script draft -> retry.
            paths = [p.strip() for p in arg.split(",") if p.strip()]
            n = self._mock_calls[role]
            self._mock_calls[role] = n + 1
            path = paths[min(n, len(paths) - 1)]
            try:
                text = (config.ROOT / path).read_text(encoding="utf-8")
            except OSError:
                raise LLMClientError(
                    f"The mock fixture '{path}' set in {env_name} doesn't "
                    f"exist or can't be read. Point it at a readable file.")
            prompt = {"backend": "mock", "model": spec, "messages": messages,
                      "temperature": 0, "max_tokens": _max_tokens(role)}
            response = {"backend": "mock",
                        "choices": [{"message": {"role": "assistant",
                                                 "content": text}}]}
            self._recorder.record(module, prompt, response)
            return text

        if backend == "llmod":
            payload = _chat_payload(arg, messages, _max_tokens(role))
            data = self._recorded_post(module, "/chat/completions", payload)
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                raise LLMClientError(
                    "The language model service replied in a shape I don't "
                    "recognize, so I couldn't read the completion.")

        raise LLMClientError(
            f"{env_name} is set to '{spec}', which I don't understand. "
            f"Use llmod:<model> or mock:<path>.")

    def embed(self, module: str, texts: list[str]) -> list[list[float]]:
        """Embeddings for a list of texts; returns vectors in input order."""
        model = _require_env("EMBED_MODEL",
                             "Set it to the LLMod embedding deployment name.")
        payload = {"model": model, "input": list(texts)}
        data = self._recorded_post(module, "/embeddings", payload)
        try:
            rows = sorted(data["data"], key=lambda d: d.get("index", 0))
            return [row["embedding"] for row in rows]
        except (KeyError, TypeError):
            raise LLMClientError(
                "The embedding service replied in a shape I don't "
                "recognize, so I couldn't read the vectors.")
