"""rag/retrieve.py -- online: embed the query, top-k search (6.8).

Asserts every returned chunk was embedded with the profile's model (the
hard invariant), filters by score_threshold, and truncates the chunk list
at max_context_chars before returning.

    python -m tpagent.rag.retrieve "WAIT syntax seconds"
"""
from __future__ import annotations

from dataclasses import dataclass

from tpagent import modules
from tpagent.llm_client import LLMClient
from tpagent.rag.index import (RagConfigError, check_embedding_model,
                               get_index, rag_config)


@dataclass
class RetrievedChunk:
    id: str
    text: str
    source: str
    family: str
    score: float


def _fields(match) -> tuple[str, float, dict]:
    if isinstance(match, dict):
        return match["id"], float(match["score"]), match.get("metadata") or {}
    return match.id, float(match.score), dict(match.metadata or {})


def retrieve(query: str, profile: str = "online", *, llm: LLMClient,
             index=None, config: dict | None = None) -> list[RetrievedChunk]:
    cfg = config or rag_config()
    model = check_embedding_model(profile, cfg)
    params = cfg.get("retrieve") or {}
    top_k = int(params.get("top_k", 5))
    threshold = float(params.get("score_threshold", 0.25))
    max_chars = int(params.get("max_context_chars", 9000))

    if index is None:
        index = get_index(profile)
    vector = llm.embed(modules.RAG_RETRIEVE, [query])[0]
    result = index.query(vector=vector, top_k=top_k, include_metadata=True)
    matches = result["matches"] if isinstance(result, dict) else result.matches

    chunks: list[RetrievedChunk] = []
    used = 0
    for match in matches:
        id_, score, meta = _fields(match)
        indexed_model = meta.get("embedding_model", "")
        if indexed_model != model:
            raise RagConfigError(
                f"The index holds vectors embedded with '{indexed_model}' "
                f"but this profile uses '{model}'. Re-index before "
                f"retrieving - vectors from different embedding models "
                f"never share a collection.")
        if score < threshold:
            continue
        text = meta.get("text", "")
        if used + len(text) > max_chars:
            break
        used += len(text)
        chunks.append(RetrievedChunk(id=id_, text=text,
                                     source=meta.get("source", ""),
                                     family=meta.get("family", ""),
                                     score=score))
    return chunks


def main() -> None:
    import sys

    from tpagent.steps import StepsRecorder
    query = " ".join(sys.argv[1:]) or "L linear motion speed termination"
    hits = retrieve(query, llm=LLMClient(StepsRecorder()))
    print(f"query: {query!r} -> {len(hits)} chunks")
    for h in hits:
        snippet = " ".join(h.text.split())[:110]
        print(f"  {h.score:.3f}  {h.source:<22} {h.family:<16} {snippet}")


if __name__ == "__main__":
    main()
