"""Phase 7: compliance endpoints + the module-name consistency contract.

The course grades consistency: names in every steps trace == subset of
the registry == the names drawn in the architecture PNG (via its JSON
manifest, written by the same generator from the same constants).
"""
import json

import pytest
from fastapi.testclient import TestClient

from api.index import app
from tpagent.config import ROOT
from tpagent.modules import REGISTRY

MANIFEST = ROOT / "docs" / "architecture.json"
EXAMPLES = ROOT / "api" / "agent_info_examples.json"


class TestConsistency:
    def test_manifest_boxes_equal_registry(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert set(manifest["boxes"]) == set(REGISTRY)
        assert len(manifest["boxes"]) == len(REGISTRY)   # no duplicates

    def test_manifest_flow_covers_registry(self):
        # the agent-view flow: 10 numbered steps whose module references
        # stay inside the registry and together touch every module
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        flow = manifest["flow"]
        assert [s["step"] for s in flow] == list(range(1, 11))
        seen = set()
        for step in flow:
            assert set(step) == {"step", "title", "modules", "text"}
            assert step["title"] and step["text"]
            assert set(step["modules"]) <= set(REGISTRY)
            seen |= set(step["modules"])
        assert seen == set(REGISTRY)
        assert manifest["intro"] and all(manifest["intro"])

    def test_agent_info_example_steps_within_registry(self):
        examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
        assert len(examples) == 2
        for example in examples:
            assert set(example) == {"prompt", "full_response", "steps"}
            assert example["steps"], "steps array must not be empty"
            modules_seen = {s["module"] for s in example["steps"]}
            assert modules_seen <= set(REGISTRY)
            for step in example["steps"]:
                assert set(step) == {"module", "prompt", "response"}

    def test_example_traces_show_agent_chat_steps_only(self):
        # owner decision (2026-08-30): the agent_info SHOWCASE hides the
        # embedding plumbing - its steps are the chat calls the reader
        # cares about. Live /api/execute traces still record every
        # provider call, embeddings compacted (see test_llm_client).
        from tpagent.modules import RAG_EMBED, RAG_RETRIEVE
        examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
        for example in examples:
            assert example["steps"]
            for step in example["steps"]:
                assert step["module"] not in {RAG_EMBED, RAG_RETRIEVE}
                for row in (step["response"].get("data") or []):
                    assert not isinstance(row.get("embedding"), list)

    def test_examples_show_program_and_clarification(self):
        program_ex, clarify_ex = json.loads(
            EXAMPLES.read_text(encoding="utf-8"))
        assert program_ex["full_response"].startswith("/PROG")
        assert "--- report ---" in program_ex["full_response"]
        assert "LLM1-Audit" in [s["module"] for s in program_ex["steps"]]
        assert "?" in clarify_ex["full_response"]        # the question
        assert "/PROG" not in clarify_ex["full_response"]

    def test_recorder_rejects_off_registry_names(self):
        # the mechanical guarantee that no trace can disagree with the PNG
        from tpagent.steps import StepsRecorder
        with pytest.raises(ValueError):
            StepsRecorder().record("Orchestrator", {}, {})


class TestEndpoints:
    def test_model_architecture_serves_png(self):
        r = TestClient(app).get("/api/model_architecture")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(r.content) > 10_000

    def test_agent_info_schema(self):
        body = TestClient(app).get("/api/agent_info").json()
        assert set(body) == {"description", "purpose", "how_it_works",
                             "prompt_template", "prompt_examples"}
        assert body["prompt_template"]["template"]
        assert "pick a part from <place>" in body["prompt_template"]["template"]
        assert len(body["prompt_examples"]) == 2
        assert body["description"] and body["purpose"]

    def test_agent_info_serves_the_manifest_flow(self):
        # the endpoint's story IS the diagram's manifest, verbatim
        body = TestClient(app).get("/api/agent_info").json()
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert body["how_it_works"] == {"intro": manifest["intro"],
                                        "flow": manifest["flow"]}
        assert len(body["how_it_works"]["flow"]) == 10

    def test_table_endpoint_serves_default(self):
        body = TestClient(app).get("/api/table").json()
        assert set(body) == {"source", "cell_id", "entries", "csv"}
        assert body["source"] == "default_table"
        assert body["entries"] > 0
        assert "# schema: reg_io_v1" in body["csv"]

    def test_config_endpoint(self):
        body = TestClient(app).get("/api/config").json()
        assert set(body) == {"defaults", "limits", "overridable"}
        assert body["defaults"]["speed"] == "100mm/sec"
        assert body["limits"]["max_speed_mmsec"] == 250
        assert "speed" in body["overridable"]
        assert "max_speed_mmsec" not in body["overridable"]

    def test_team_info_still_exact(self):
        body = TestClient(app).get("/api/team_info").json()
        assert set(body) == {"group_batch_order_number", "team_name",
                             "students"}
