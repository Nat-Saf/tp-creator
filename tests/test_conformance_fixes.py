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


class TestReauditFixes:
    """Round 2: findings from the re-audit sweep."""

    def test_missing_column_with_extra_column_rejected(self, env):
        # the original stores-phase finding, finally closed: proper-subset
        # header check let "missing value + extra col" crash with KeyError
        bad = ("# schema: reg_io_v1\n# cell_id: line3_fanuc1\n"
               "# scanned_at: t\n"
               "type,index,comment,initialized,extra\nPR,1,x,TRUE,y\n")
        resp = handle(Request(prompt="pick", cell_id="line3_fanuc1",
                              scan=bad), sb_client=env)
        assert resp.status == "rejected"
        assert "value" in resp.reason and "[" not in resp.reason

    def test_api_shape_survives_malformed_inferred(self, env, monkeypatch):
        from fastapi.testclient import TestClient

        from api.index import app
        from tpagent.contract import Report, Response

        def fake_handle(req, **kw):
            return Response(status="ok", draft_id="d", program_ls="/PROG X",
                            file_ref="outputs/d",
                            report=Report(inferred=["not-a-dict",
                                                    {"text": "t",
                                                     "decision": "d"}]))
        monkeypatch.setenv("DEMO_CELL", "line3_fanuc1")
        monkeypatch.setattr("api.index.runtime.handle", fake_handle)
        r = TestClient(app).post("/api/execute", json={"prompt": "x"})
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"status", "error", "response", "steps"}
        assert body["status"] == "ok" and "not-a-dict" in body["response"]

    def test_uncappable_motion_speeds_refused_under_cap(self):
        from tpagent.validator import run
        limits = {"max_speed_mmsec": 250, "max_wait_sec": 10}
        prog = ("/PROG T\n/MN\n  1:  L PR[5] 4sec FINE ;\n"
                "  2:  L PR[6] 2000deg/sec CNT50 ;\n"
                "  3:  WAIT 2.00(sec) ;\n"
                "  4:  DO[7]=PULSE,0.5sec ;\n/POS\n/END\n")
        verdict = run(prog, None, limits)
        speed_errs = [e for e in verdict.errors if e.layer == "limits"]
        assert len(speed_errs) == 2                 # lines 1 and 2 only
        assert all("mm/sec" in e.message for e in speed_errs)
        assert {e.line for e in speed_errs} == {1, 2}

    def test_post_draft_reretrieve_refreshes_docs(self, env, monkeypatch,
                                                  tmp_path):
        # DESIGN 5 escalation: re-retrieved documentation reaches the retry
        gen = {"action": "generate_program",
               "params": {"task": "pick and place"}, "program_name": "P",
               "notes": [], "inferred": [], "base_draft": None,
               "fix_guidance": None}
        rag = {"action": "rag_retrieve", "query": "WAIT syntax"}
        retry = {**gen, "base_draft": "last", "fix_guidance": "fix WAIT"}
        paths = []
        for name, obj in (("gen", gen), ("rag", rag), ("retry", retry)):
            p = tmp_path / f"{name}.json"
            p.write_text(json.dumps(obj), encoding="utf-8")
            paths.append(str(p))
        monkeypatch.setenv("TP_LLM1", "mock:" + ",".join(
            paths + ["tests/fixtures/llm1_audit.json"]))
        monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/v1.ls,"
                                      "tests/fixtures/v2.ls")
        queries = []

        def spy(query, profile):
            queries.append(query)
            return [SimpleNamespace(text=f"## chunk for {query}")]

        recorder = StepsRecorder()
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1"),
                      recorder=recorder, sb_client=env, retrieve_fn=spy)
        assert resp.status == "ok"
        assert queries == ["pick and place", "WAIT syntax"]
        codegen = [s for s in recorder.steps
                   if s["module"] == "LLM2-Codegen"]
        retry_prompt = codegen[1]["prompt"]["messages"][0]["content"]
        assert "chunk for WAIT syntax" in retry_prompt   # refreshed DOCS

    def test_blank_scan_means_no_scan(self, env):
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1", scan="   \n  "),
                      sb_client=env)
        assert resp.status == "ok"
        assert resp.report.table_source.startswith("cache(")

    def test_friendly_rag_backend_message(self):
        from tpagent.contract import validate_request
        msg = validate_request(Request(prompt="x", cell_id="c",
                                       rag_backend="martian"))
        assert msg is not None and "must be" not in msg
        assert "online" in msg and "local" in msg


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
