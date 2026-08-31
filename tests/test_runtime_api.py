"""Phase 5 e2e: runtime.handle + POST /api/execute with mock LLMs.

TP_LLM1 serves scripted JSON actions in call order; TP_LLM2 serves
v1.ls (two seeded errors) then v2.ls (clean) - so the loop must show
draft -> validate fail -> retry -> pass -> audit.
"""
import pytest
from fastapi.testclient import TestClient

from api.index import app
from tests.conftest import FIXTURES
from tests.mock_supabase import MockSupabase
from tpagent.contract import Request
from tpagent.runtime import handle
from tpagent.steps import StepsRecorder
from tpagent.stores import client as sb_client_mod


@pytest.fixture()
def env(monkeypatch):
    from tpagent import config
    monkeypatch.setattr(config, "load_dotenv", lambda path=None: None)
    monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_gen.json,"
                                  "tests/fixtures/llm1_retry.json,"
                                  "tests/fixtures/llm1_audit.json")
    monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/v1.ls,"
                                  "tests/fixtures/v2.ls")
    monkeypatch.setenv("DEMO_CELL", "line3_fanuc1")
    mock = MockSupabase()
    sb_client_mod.use_client(mock)
    yield mock
    sb_client_mod.use_client(None)


class TestHandle:
    def test_retry_loop_delivers_v2(self, env):
        recorder = StepsRecorder()
        resp = handle(Request(prompt="pick a part from the conveyor and put "
                                     "it on fixture A, gently",
                              cell_id="line3_fanuc1"), recorder=recorder)
        assert resp.status == "ok"
        assert "PR[6:conveyor approach]" in resp.program_ls
        assert resp.report.retries == 1
        assert resp.report.table_source == "default_table"
        assert resp.report.mapping_confidence == "verified"
        assert resp.report.positions["PR[5]"] == "note 'conveyor pick'"
        assert any("approach" in a for a in resp.report.advisories)
        assert resp.file_ref == f"outputs/{resp.draft_id}"

        modules_seen = [s["module"] for s in recorder.steps]
        assert modules_seen == ["LLM1-Intake", "LLM2-Codegen",
                                "LLM1-Intake", "LLM2-Codegen", "LLM1-Audit"]

    def test_stores_hold_drafts_verdicts_output(self, env):
        resp = handle(Request(prompt="pick and place", cell_id="line3_fanuc1"))
        drafts = env.data["drafts"]
        verdicts = {v["draft_id"]: v for v in env.data["verdicts"]}
        assert len(drafts) == 2
        assert verdicts[drafts[0]["id"]]["verdict"] == "fail"
        assert verdicts[drafts[1]["id"]]["verdict"] == "pass"
        assert env.data["outputs"][0]["program_name"] == "PICK_PLACE_A"
        assert resp.report.scan_used                  # cache timestamp

    def test_user_requested_table_addition(self, env, monkeypatch):
        # "add pr2 to the table": the runtime merges the new entry (so the
        # validator accepts PR[2]) and updates PR[5]'s note in-conversation
        monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_add.json,"
                                      "tests/fixtures/llm1_audit.json")
        monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/move_p2.ls")
        resp = handle(Request(
            prompt="user: create a tp program to move the robot from "
                   "position 1 to position 2\n"
                   "assistant: I couldn't find PR[2] in your table - which "
                   "register should I move to instead, or say 'add PR[2]'?\n"
                   "user: add pr2 to the table",
            cell_id="line3_fanuc1"))
        assert resp.status == "ok"
        assert "PR[2:position 2]" in resp.program_ls
        ads = " ".join(resp.report.advisories)
        assert "added PR[2]" in ads                 # the addition, reported
        assert "updated PR[5]" in ads               # the update, reported
        assert resp.report.positions["PR[2]"] == "note 'position 2'"

    def test_edit_table_turn_changes_no_program(self, env, monkeypatch):
        # a table-only request: no program, the updated CSV rides back
        monkeypatch.setenv("TP_LLM1",
                           "mock:tests/fixtures/llm1_edit_table.json")
        recorder = StepsRecorder()
        resp = handle(Request(prompt="add DO[100] to the table with "
                                     "description dispenser on, set false",
                              cell_id="line3_fanuc1"), recorder=recorder)
        assert resp.status == "needs_clarification"
        assert "DO[100]" in resp.questions[0]
        assert "DO,100,dispenser on,,OFF" in resp.table_csv
        assert "# cell_id: line3_fanuc1" in resp.table_csv
        assert [s["module"] for s in recorder.steps] == ["LLM1-Intake"]

    def test_edit_previous_sends_program_to_renderer(self, env, monkeypatch):
        import json as _json
        monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_editprev.json,"
                                      "tests/fixtures/llm1_audit.json")
        monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/edited_fixA.ls")
        recorder = StepsRecorder()
        old = ("/PROG OLDPROG\n/ATTR\nOWNER = MNEDITOR;\n/MN\n"
               "   1:  J PR[1:home] 100% FINE ;\n/POS\n/END\n")
        resp = handle(Request(prompt="edit the program - end at fixture A",
                              previous_ls=old,
                              cell_id="line3_fanuc1"), recorder=recorder)
        assert resp.status == "ok"
        codegen = next(s for s in recorder.steps
                       if s["module"] == "LLM2-Codegen")
        blob = _json.dumps(codegen["prompt"])
        assert "PREVIOUS PROGRAM" in blob and "OLDPROG" in blob

    def test_audit_must_fix_triggers_one_retry(self, env, monkeypatch):
        monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_gen.json,"
                                      "tests/fixtures/llm1_audit_mustfix.json,"
                                      "tests/fixtures/llm1_audit.json")
        monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/v2.ls,"
                                      "tests/fixtures/v2.ls")
        recorder = StepsRecorder()
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1"), recorder=recorder)
        assert resp.status == "ok"
        modules_seen = [s["module"] for s in recorder.steps]
        assert modules_seen == ["LLM1-Intake", "LLM2-Codegen", "LLM1-Audit",
                               "LLM2-Codegen", "LLM1-Audit"]
        assert resp.report.retries == 1
        assert any("requested one correction" in a
                   for a in resp.report.advisories)

    def test_ask_user_flow(self, env, monkeypatch):
        monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_ask.json")
        resp = handle(Request(prompt="put it on the fixture",
                              cell_id="line3_fanuc1"))
        assert resp.status == "needs_clarification"
        assert "fixture A" in resp.questions[0]

    def test_budget_exhaustion_fails_friendly(self, env, monkeypatch):
        monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_gen.json")
        monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/v1.ls")  # never fixed
        recorder = StepsRecorder()
        resp = handle(Request(prompt="pick and place",
                              cell_id="line3_fanuc1"), recorder=recorder)
        assert resp.status == "failed"
        # v1.ls fails with the same class every attempt -> the mechanical
        # same-class stop fires (design: the old strategy can't spend more)
        assert "same kind of problem" in resp.reason
        codegen = [s for s in recorder.steps if s["module"] == "LLM2-Codegen"]
        assert len(codegen) == 3            # retry.max_attempts, enforced

    def test_level_a_reject(self, env):
        resp = handle(Request(prompt="", cell_id="line3_fanuc1"))
        assert resp.status == "rejected" and "empty" in resp.reason


class TestApiExecute:
    def test_exact_schema_and_steps_trace(self, env):
        client = TestClient(app)
        r = client.post("/api/execute", json={
            "prompt": "pick a part from the conveyor and put it on fixture "
                      "A, gently"})
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"status", "error", "response", "steps"}
        assert body["status"] == "ok" and body["error"] is None
        assert "/PROG PICK_PLACE_A" in body["response"]
        assert "--- report ---" in body["response"]

        modules_seen = [s["module"] for s in body["steps"]]
        assert modules_seen.count("LLM2-Codegen") == 2   # the retry, visible
        assert "LLM1-Audit" in modules_seen
        assert all(set(s) == {"module", "prompt", "response"}
                   for s in body["steps"])

    def test_clarification_maps_to_ok_with_question(self, env, monkeypatch):
        monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_ask.json")
        body = TestClient(app).post(
            "/api/execute", json={"prompt": "put it on the fixture"}).json()
        assert set(body) == {"status", "error", "response", "steps"}
        assert body["status"] == "ok" and body["error"] is None
        assert "Which fixture" in body["response"]
        assert [s["module"] for s in body["steps"]] == ["LLM1-Intake"]

    def test_internal_failure_maps_to_error_with_partial_steps(
            self, env, monkeypatch):
        monkeypatch.setenv("TP_LLM1", "mock:tests/fixtures/llm1_gen.json")
        monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/v1.ls")
        body = TestClient(app).post(
            "/api/execute", json={"prompt": "pick and place"}).json()
        assert set(body) == {"status", "error", "response", "steps"}
        assert body["status"] == "error" and body["response"] is None
        assert body["error"] and "HTTP" not in body["error"]
        assert len(body["steps"]) >= 6      # partial trace kept

    def test_provider_rejection_error_is_humanized(self, env, monkeypatch):
        # a definitive provider 4xx must not leak "HTTP 401" to the human
        import httpx

        from tpagent import llm_client as lc
        monkeypatch.setenv("TP_LLM1", "llmod:mini")
        monkeypatch.setenv("LLMOD_BASE_URL", "https://llmod.test")
        monkeypatch.setenv("LLMOD_API_KEY", "bad")
        transport = httpx.MockTransport(
            lambda r: httpx.Response(401, json={}))
        orig = lc.LLMClient

        class Patched(orig):
            def __init__(self, recorder, transport=None):
                super().__init__(recorder, transport=transport)
                self._transport = httpx.MockTransport(
                    lambda r: httpx.Response(401, json={}))

        monkeypatch.setattr("tpagent.runtime.LLMClient", Patched)
        body = TestClient(app).post(
            "/api/execute", json={"prompt": "pick and place"}).json()
        assert body["status"] == "error"
        assert "HTTP" not in body["error"] and "401" not in body["error"]
        assert body["steps"][-1]["response"]["detail"] == "HTTP 401"

    def test_malformed_body_keeps_exact_shape(self, env):
        body = TestClient(app).post("/api/execute", json={"wrong": 1}).json()
        assert set(body) == {"status", "error", "response", "steps"}
        assert body["status"] == "error" and body["response"] is None

    def test_root_serves_gui(self, env):
        r = TestClient(app).get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        for marker in (">Run<", "New task", "textarea",
                       "/api/execute", "Steps trace",
                       "Load registers/IO table", "Show table"):
            assert marker in r.text, marker

    def test_transcript_prompt_passes_through(self, env):
        transcript = ("user: put it on the fixture\n"
                      "assistant: Which fixture - A or B?\n"
                      "user: fixture A, gently")
        body = TestClient(app).post(
            "/api/execute", json={"prompt": transcript}).json()
        assert body["status"] == "ok"
        prompt_msg = body["steps"][0]["prompt"]["messages"][1]["content"]
        assert "fixture A, gently" in prompt_msg
