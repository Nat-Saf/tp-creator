"""rag/index.py -- offline: chunk corpus/prepared, embed, upsert (6.8).

Chunking is logical: one '##' section = one chunk, family = the file stem.
FORMAT.md is the extraction spec, never indexed. Every vector's metadata
records the embedding model so retrieval can assert the hard invariant
(vectors from different embedding models never share a collection).

    python -m tpagent.rag.index          # build the online index, print stats
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from tpagent import config, modules
from tpagent.llm_client import LLMClient

EMBED_BATCH = 32


class RagConfigError(RuntimeError):
    """Profile/env disagreement -- fail loud before touching any index."""


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    family: str


@lru_cache(maxsize=1)
def rag_config() -> dict:
    path = config.ROOT / "config" / "rag_config.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def profile_config(profile: str, cfg: dict | None = None) -> dict:
    cfg = cfg or rag_config()
    try:
        return cfg["profiles"][profile]
    except KeyError:
        raise RagConfigError(
            f"rag_config.yaml has no profile named '{profile}'.")


def check_embedding_model(profile: str, cfg: dict | None = None) -> str:
    """The profile's model must equal EMBED_MODEL -- one index per model."""
    config.load_dotenv()
    declared = profile_config(profile, cfg)["embedding"]["model"]
    env = os.environ.get("EMBED_MODEL", "").strip()
    if env and env != declared:
        raise RagConfigError(
            f"EMBED_MODEL is '{env}' but the '{profile}' profile declares "
            f"'{declared}'. One index per embedding model - align them "
            f"before indexing or retrieving.")
    return declared


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:64]


def chunk_prepared(prepared_dir: Path | None = None) -> list[Chunk]:
    prepared_dir = prepared_dir or config.ROOT / "corpus" / "prepared"
    chunks: list[Chunk] = []
    for md in sorted(prepared_dir.glob("*.md")):
        if md.name.upper() == "FORMAT.MD":
            continue
        family = md.stem
        sections = re.split(r"(?m)^## ", md.read_text(encoding="utf-8"))
        for section in sections[1:]:            # [0] is preamble before first ##
            title = section.splitlines()[0].strip()
            text = ("## " + section).strip()
            if not title or len(text) < 40:     # skip empty stubs
                continue
            chunks.append(Chunk(id=f"{family}--{_slug(title)}", text=text,
                                source=md.name, family=family))
    return chunks


def get_index(profile: str = "online", *, create_if_missing: bool = False):
    """Open the profile's Pinecone index (the SDK's only import site)."""
    config.load_dotenv()
    from pinecone import Pinecone, ServerlessSpec
    api_key = os.environ.get("PINECONE_API_KEY", "").strip()
    if not api_key:
        raise RagConfigError(
            "PINECONE_API_KEY is not set. Add it to .env (locally) or the "
            "Vercel dashboard.")
    prof = profile_config(profile)
    name = os.environ.get("PINECONE_INDEX",
                          prof["vector_db"].get("index_name", ""))
    pc = Pinecone(api_key=api_key)
    if create_if_missing and not pc.has_index(name):
        pc.create_index(name=name,
                        dimension=int(prof["embedding"].get("dimension", 1536)),
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-east-1"))
    return pc.Index(name)


def build_index(llm: LLMClient, *, profile: str = "online", index=None,
                prepared_dir: Path | None = None) -> dict:
    model = check_embedding_model(profile)
    chunks = chunk_prepared(prepared_dir)
    if not chunks:
        raise RagConfigError(
            "corpus/prepared/ has no '##' sections to index yet.")
    if index is None:
        index = get_index(profile, create_if_missing=True)

    for start in range(0, len(chunks), EMBED_BATCH):
        batch = chunks[start:start + EMBED_BATCH]
        vectors = llm.embed(modules.RAG_EMBED, [c.text for c in batch])
        index.upsert(vectors=[{
            "id": c.id,
            "values": v,
            "metadata": {"text": c.text, "source": c.source,
                         "family": c.family, "embedding_model": model},
        } for c, v in zip(batch, vectors)])

    families: dict[str, int] = {}
    for c in chunks:
        families[c.family] = families.get(c.family, 0) + 1
    return {"chunks": len(chunks), "families": families,
            "embedding_model": model}


def main() -> None:
    from tpagent.steps import StepsRecorder
    stats = build_index(LLMClient(StepsRecorder()))
    print(f"indexed {stats['chunks']} chunks "
          f"(model {stats['embedding_model']}):")
    for family, n in sorted(stats["families"].items()):
        print(f"  {family:<20} {n}")


if __name__ == "__main__":
    main()
