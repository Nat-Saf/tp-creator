"""Offline rag/ tests: chunker, index build, retrieval invariants."""
import pytest

from tpagent import modules
from tpagent.rag import retrieve as retrieve_mod
from tpagent.rag.index import (Chunk, RagConfigError, build_index,
                               check_embedding_model, chunk_prepared)
from tpagent.rag.retrieve import retrieve

CFG = {
    "profiles": {"online": {"embedding": {"model": "embed-test",
                                          "dimension": 4},
                            "vector_db": {"provider": "pinecone",
                                          "index_name": "t"}}},
    "retrieve": {"top_k": 5, "score_threshold": 0.25,
                 "max_context_chars": 9000},
}


class StubLLM:
    def __init__(self):
        self.calls = []

    def embed(self, module, texts):
        self.calls.append((module, list(texts)))
        return [[float(len(t) % 7), 1.0, 0.0, 0.0] for t in texts]


class FakeIndex:
    def __init__(self, matches=None):
        self.upserts = []
        self.matches = matches or []

    def upsert(self, vectors):
        self.upserts.append(vectors)

    def query(self, vector, top_k, include_metadata):
        return {"matches": self.matches[:top_k]}


def match(id_, score, model="embed-test", text="chunk text", family="motion"):
    return {"id": id_, "score": score,
            "metadata": {"text": text, "source": "motion.md",
                         "family": family, "embedding_model": model}}


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("EMBED_MODEL", "embed-test")


class TestChunker:
    def test_sections_become_chunks_format_md_skipped(self, tmp_path):
        (tmp_path / "FORMAT.md").write_text("## not - indexed\n" + "x" * 60)
        (tmp_path / "motion.md").write_text(
            "# preamble is skipped\n"
            "## L - linear motion\nSyntax: L ...\nExample:\n    L P[1] ;\n"
            "## J - joint motion\nSyntax: J ...\nExample:\n    J P[1] ;\n")
        chunks = chunk_prepared(tmp_path)
        assert [c.id for c in chunks] == ["motion--l-linear-motion",
                                          "motion--j-joint-motion"]
        assert all(c.family == "motion" and c.source == "motion.md"
                   for c in chunks)
        assert chunks[0].text.startswith("## L - linear motion")

    def test_short_stub_sections_dropped(self, tmp_path):
        (tmp_path / "io.md").write_text("## DO\nstub\n")
        assert chunk_prepared(tmp_path) == []

    def test_real_examples_file_chunks(self):
        chunks = chunk_prepared()
        examples = [c for c in chunks if c.family == "examples"]
        assert any("pick-and-place" in c.id for c in examples)
        assert all(c.source == "examples.md" for c in examples)


class TestEmbeddingModelInvariant:
    def test_env_profile_mismatch_raises(self, monkeypatch):
        monkeypatch.setenv("EMBED_MODEL", "other-model")
        with pytest.raises(RagConfigError, match="One index per embedding"):
            check_embedding_model("online", CFG)

    def test_match_passes(self, env):
        assert check_embedding_model("online", CFG) == "embed-test"

    def test_unknown_profile_raises(self, env):
        with pytest.raises(RagConfigError, match="no profile"):
            check_embedding_model("offline", CFG)


class TestBuildIndex:
    def test_upserts_vectors_with_metadata(self, tmp_path, env, monkeypatch):
        monkeypatch.setattr("tpagent.rag.index.rag_config", lambda: CFG)
        (tmp_path / "motion.md").write_text(
            "## L - linear motion\nSyntax: L ...\nExample:\n    L P[1] ;\n")
        llm, index = StubLLM(), FakeIndex()
        stats = build_index(llm, index=index, prepared_dir=tmp_path)
        assert stats == {"chunks": 1, "families": {"motion": 1},
                         "embedding_model": "embed-test"}
        assert llm.calls[0][0] == modules.RAG_EMBED
        [batch] = index.upserts
        assert batch[0]["id"] == "motion--l-linear-motion"
        assert batch[0]["metadata"]["embedding_model"] == "embed-test"
        assert batch[0]["metadata"]["family"] == "motion"
        assert len(batch[0]["values"]) == 4

    def test_empty_corpus_raises(self, tmp_path, env, monkeypatch):
        monkeypatch.setattr("tpagent.rag.index.rag_config", lambda: CFG)
        with pytest.raises(RagConfigError, match="no '##' sections"):
            build_index(StubLLM(), index=FakeIndex(), prepared_dir=tmp_path)


class TestRetrieve:
    def test_returns_scored_chunks_uses_rag_retrieve_module(self, env):
        llm = StubLLM()
        hits = retrieve("WAIT syntax", llm=llm,
                        index=FakeIndex([match("a", 0.9), match("b", 0.5)]),
                        config=CFG)
        assert llm.calls[0][0] == modules.RAG_RETRIEVE
        assert [h.id for h in hits] == ["a", "b"]
        assert hits[0].score == 0.9 and hits[0].family == "motion"

    def test_threshold_filters_low_scores(self, env):
        hits = retrieve("q", llm=StubLLM(),
                        index=FakeIndex([match("a", 0.9), match("b", 0.1)]),
                        config=CFG)
        assert [h.id for h in hits] == ["a"]

    def test_model_mismatch_raises(self, env):
        with pytest.raises(RagConfigError, match="Re-index"):
            retrieve("q", llm=StubLLM(),
                     index=FakeIndex([match("a", 0.9, model="stale-model")]),
                     config=CFG)

    def test_max_context_chars_truncates(self, env):
        cfg = {**CFG, "retrieve": {"top_k": 5, "score_threshold": 0.0,
                                   "max_context_chars": 15}}
        hits = retrieve("q", llm=StubLLM(),
                        index=FakeIndex([match("a", 0.9, text="x" * 10),
                                         match("b", 0.8, text="y" * 10)]),
                        config=cfg)
        assert [h.id for h in hits] == ["a"]

    def test_top_k_respected(self, env):
        cfg = {**CFG, "retrieve": {"top_k": 2, "score_threshold": 0.0,
                                   "max_context_chars": 9000}}
        index = FakeIndex([match(str(i), 0.9 - i / 10) for i in range(5)])
        hits = retrieve("q", llm=StubLLM(), index=index, config=cfg)
        assert len(hits) == 2
