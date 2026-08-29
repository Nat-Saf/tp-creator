"""Registry + StepsRecorder tests."""
import pytest

from tpagent import modules
from tpagent.steps import StepsRecorder


def test_registry_names_exact():
    assert modules.REGISTRY == (
        "Runtime", "LLM1-Intake", "LLM1-Audit", "Renderer", "LLM2-Codegen",
        "Validator", "RAG-Embed", "RAG-Retrieve", "Stores")


def test_record_appends_in_order():
    rec = StepsRecorder()
    rec.record(modules.LLM1_INTAKE, {"q": 1}, {"a": 1})
    rec.record(modules.LLM2_CODEGEN, {"q": 2}, {"a": 2})
    assert [s["module"] for s in rec.steps] == ["LLM1-Intake", "LLM2-Codegen"]
    assert len(rec) == 2


def test_off_registry_module_rejected():
    with pytest.raises(ValueError, match="not a registry module name"):
        StepsRecorder().record("Orchestrator", {}, {})


def test_non_dict_prompt_or_response_rejected():
    rec = StepsRecorder()
    with pytest.raises(ValueError, match="must be dicts"):
        rec.record(modules.LLM1_INTAKE, "raw string", {})
    with pytest.raises(ValueError, match="must be dicts"):
        rec.record(modules.LLM1_INTAKE, {}, ["not", "a", "dict"])


def test_steps_are_snapshots():
    rec = StepsRecorder()
    prompt = {"messages": ["hi"]}
    rec.record(modules.LLM1_INTAKE, prompt, {"ok": True})
    prompt["messages"].append("mutated after the call")
    steps = rec.steps
    steps[0]["module"] = "tampered"
    assert rec.steps[0]["prompt"] == {"messages": ["hi"]}
    assert rec.steps[0]["module"] == "LLM1-Intake"
