"""Regression tests for the design-conformance audit fixes (group A)."""
import json
from types import SimpleNamespace

import pytest

from tests.conftest import FIXTURES
from tests.mock_supabase import MockSupabase
from tpagent.contract import Request
from tpagent.runtime import handle
from tpagent.steps import StepsRecorder
from tpagent.stores.seed import seed
from tpagent.stores.table import cache_scan, materialize

CSV = (FIXTURES / "reg_io_v1_template.csv").read_text(encoding="utf-8")
CHUNK = SimpleNamespace(text="## L - linear motion\nSyntax: L <P[i]> ...")


@pytest.fixture()
def env(monkeypatch):
    from tpagent import config
    monkeypatch.setattr(config, "load_dotenv", lambda path=None: None)
    monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_gen.json,"
                                  "tests/fixtures/llm1_audit.json")
    monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/v2.ls")
    mock = MockSupabase()
    seed("line3_fanuc1", FIXTURES / "reg_io_v1_template.csv", client=mock)
    yield mock


class TestScanLevelA:                                   # audit A1 + A2
    def test_garbage_scan_rejected_friendly(self, env):
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1",
                              scan="not,a,real\ncsv,at,all"), sb_client=env)
        assert resp.status == "rejected"
        assert "reg_io_v1" in resp.reason and "ERR" not in resp.reason

    def test_cross_cell_scan_rejected(self, env):
        resp = handle(Request(prompt="pick and place",
                              cell_id="another_cell", scan=CSV),
                      sb_client=env)
        assert resp.status == "rejected"
        assert "line3_fanuc1" in resp.reason
        assert "another_cell" in resp.reason

    def test_matching_scan_accepted_keeps_csv_identity(self, env):
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1", scan=CSV),
                      sb_client=env)
        assert resp.status == "ok"
        assert resp.report.table_source == "scan"
        assert resp.report.scan_used == "2026-07-04T10:42:00"  # CSV's own


class TestRagBackend:                                   # audit A3
    def test_local_backend_rejected_friendly(self, env):
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1", rag_backend="local"),
                      sb_client=env)
        assert resp.status == "rejected"
        assert "local retrieval profile" in resp.reason

    def test_retrieve_fn_receives_the_request_profile(self, env):
        calls = []

        def spy(query, profile):
            calls.append((query, profile))
            return [CHUNK]

        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1"),
                      sb_client=env, retrieve_fn=spy)
        assert resp.status == "ok"
        assert calls and all(profile == "online" for _, profile in calls)


class TestMandatoryRetrieval:                           # audit A6
    def test_auto_retrieves_before_first_draft(self, env):
        calls = []

        def spy(query, profile):
            calls.append(query)
            return [CHUNK]

        recorder = StepsRecorder()
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1"),
                      recorder=recorder, sb_client=env, retrieve_fn=spy)
        assert resp.status == "ok"
        assert len(calls) == 1              # exactly one automatic query
        assert "fixture A" in calls[0]      # derived from the task params
        codegen = [s for s in recorder.steps
                   if s["module"] == "LLM2-Codegen"]
        prompt = codegen[0]["prompt"]["messages"][0]["content"]
        assert "REFERENCE (retrieved" in prompt
        assert "L - linear motion" in prompt

    def test_retrieval_failure_becomes_advisory_not_crash(self, env):
        def broken(query, profile):
            raise RuntimeError("index down")

        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1"),
                      sb_client=env, retrieve_fn=broken)
        assert resp.status == "ok"
        assert any("documentation index" in a
                   for a in resp.report.advisories)


class TestRetryReproducibility:                         # audit A7
    def test_retry_prompt_pins_first_attempt_task(self, env, monkeypatch,
                                                  tmp_path):
        gen = {"action": "generate_program",
               "params": {"task": "pick and place",
                          "travel_speed": "PIN_ME_123"},
               "program_name": "P", "notes": ["keep it short"],
               "inferred": [], "base_draft": None, "fix_guidance": None}
        retry = {**gen,
                 "params": {"task": "pick and place",
                            "travel_speed": "SHOULD_NOT_APPEAR"},
                 "notes": ["a different note"],
                 "base_draft": "last",
                 "fix_guidance": "Write the wait as WAIT 1.00(sec)."}
        p1 = tmp_path / "gen.json"
        p2 = tmp_path / "retry.json"
        p1.write_text(json.dumps(gen), encoding="utf-8")
        p2.write_text(json.dumps(retry), encoding="utf-8")
        monkeypatch.setenv(
            "TP_LLM1", f"mock:{p1},{p2},tests/fixtures/llm1_audit.json")
        monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/v1.ls,"
                                      "tests/fixtures/v2.ls")

        recorder = StepsRecorder()
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1"),
                      recorder=recorder, sb_client=env)
        assert resp.status == "ok" and resp.report.retries == 1
        codegen = [s for s in recorder.steps
                   if s["module"] == "LLM2-Codegen"]
        retry_prompt = codegen[1]["prompt"]["messages"][0]["content"]
        assert "PIN_ME_123" in retry_prompt          # TASK pinned
        assert "SHOULD_NOT_APPEAR" not in retry_prompt
        assert "keep it short" in retry_prompt       # NOTES pinned
        assert "a different note" not in retry_prompt
        assert "PREVIOUS DRAFT" in retry_prompt      # only PREVIOUS+FIX move
        assert "WAIT 1.00(sec)" in retry_prompt


class TestSameClassStopAndFailureReport:                # audit A4 + A5
    def test_third_same_class_failure_stops_mechanically(
            self, env, monkeypatch):
        import tpagent.runtime as rt
        cfg = {"defaults": {"speed": "100mm/sec"},
               "limits": {"max_speed_mmsec": 250, "max_wait_sec": 10},
               "retry": {"max_attempts": 5},        # budget NOT the stopper
               "table": {"max_table_age_hours": 72}}
        monkeypatch.setattr(rt, "static_config", lambda: cfg)
        monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_gen.json,"
                                      "tests/fixtures/llm1_retry.json")
        monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/v1.ls")

        recorder = StepsRecorder()
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1"),
                      recorder=recorder, sb_client=env)
        assert resp.status == "failed"
        assert "same kind of problem" in resp.reason
        codegen = [s for s in recorder.steps
                   if s["module"] == "LLM2-Codegen"]
        assert len(codegen) == 3            # stopped before the 5-cap

        # A4: the failure carries the last verdict's story in the report
        assert resp.report is not None
        assert resp.report.retries == 2
        assert any("problem(s):" in a for a in resp.report.advisories)
        assert any("WAIT" in a for a in resp.report.advisories)


class TestAuditSeesDefaults:                            # audit A9
    def test_audit_payload_includes_effective_defaults(self, env):
        recorder = StepsRecorder()
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1"),
                      recorder=recorder, sb_client=env)
        assert resp.status == "ok"
        [audit] = [s for s in recorder.steps if s["module"] == "LLM1-Audit"]
        payload = json.loads(audit["prompt"]["messages"][1]["content"])
        assert "effective_defaults" in payload
        assert payload["effective_defaults"].get("speed")


class TestDerivedFieldsNotPersisted:                    # audit A8
    def test_cache_row_has_no_derived_fields(self):
        mock = MockSupabase()
        cache_scan("line3_fanuc1", CSV, client=mock)
        entry = mock.data["reg_io_tables"][0]["entries"]["entries"][0]
        assert "category" not in entry and "direction" not in entry

    def test_rehydrate_derives_even_from_tampered_row(self):
        mock = MockSupabase()
        cache_scan("line3_fanuc1", CSV, client=mock)
        # simulate a corrupted row claiming a PR is an IO point
        stored = mock.data["reg_io_tables"][0]["entries"]["entries"]
        stored[0]["category"] = "IO"
        stored[0]["direction"] = "out"
        table, source = materialize("line3_fanuc1", None, client=mock,
                                    config={"table":
                                            {"max_table_age_hours": 1e9}})
        assert source.startswith("cache(")
        pr = table.find("PR", stored[0]["index"])
        assert pr.category == "REG" and pr.direction is None
