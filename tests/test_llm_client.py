"""LLMClient tests: mock transport, mock backend, retries, steps discipline."""
import httpx
import pytest

from tpagent import llm_client, modules
from tpagent.llm_client import LLMClient, LLMClientError
from tpagent.steps import StepsRecorder

CHAT_JSON = {"choices": [{"message": {"role": "assistant",
                                      "content": "generated"}}]}
EMBED_JSON = {"data": [{"index": 1, "embedding": [0.3, 0.4]},
                       {"index": 0, "embedding": [0.1, 0.2]}]}


@pytest.fixture()
def env(monkeypatch):
    from tpagent import config
    monkeypatch.setattr(config, "load_dotenv", lambda path=None: None)
    monkeypatch.setenv("LLMOD_BASE_URL", "https://llmod.test")
    monkeypatch.setenv("LLMOD_API_KEY", "test-key")
    monkeypatch.setenv("TP_LLM1", "llmod:mini-1")
    monkeypatch.setenv("TP_LLM2", "mock:tests/fixtures/v1.ls")
    monkeypatch.setenv("EMBED_MODEL", "embed-1")
    monkeypatch.setattr(llm_client, "RETRY_BACKOFF_SEC", 0)


def make_client(handler):
    rec = StepsRecorder()
    return LLMClient(rec, transport=httpx.MockTransport(handler)), rec


class TestScriptedFlow:
    def test_two_call_flow_yields_two_ordered_registry_steps(self, env):
        requests = []

        def handler(request):
            requests.append(request)
            if request.url.path.endswith("/chat/completions"):
                return httpx.Response(200, json=CHAT_JSON)
            return httpx.Response(200, json=EMBED_JSON)

        client, rec = make_client(handler)
        text = client.chat(modules.LLM1_INTAKE,
                           [{"role": "user", "content": "pick a part"}],
                           role="llm1")
        vectors = client.embed(modules.RAG_EMBED, ["WAIT syntax"])

        assert text == "generated"
        assert vectors == [[0.1, 0.2], [0.3, 0.4]]   # input order via index
        steps = rec.steps
        assert len(steps) == 2 and len(requests) == 2
        assert [s["module"] for s in steps] == ["LLM1-Intake", "RAG-Embed"]
        assert all(set(s) == {"module", "prompt", "response"} for s in steps)
        assert steps[0]["prompt"]["messages"][0]["content"] == "pick a part"
        assert steps[0]["response"] == CHAT_JSON
        assert steps[1]["prompt"] == {"model": "embed-1",
                                      "input": ["WAIT syntax"]}
        # the trace keeps the call but compacts the vectors (dim + preview)
        assert steps[1]["response"] == {"data": [
            {"index": 1, "embedding": {
                "dim": 2, "preview": [0.3, 0.4],
                "note": "full vector omitted from the trace"}},
            {"index": 0, "embedding": {
                "dim": 2, "preview": [0.1, 0.2],
                "note": "full vector omitted from the trace"}},
        ]}

    def test_budget_rules_in_payload_and_auth_header(self, env):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=CHAT_JSON)

        client, _ = make_client(handler)
        client.chat(modules.LLM1_INTAKE, [{"role": "user", "content": "x"}],
                    role="llm1")
        import json
        payload = json.loads(requests[0].content)
        assert payload["temperature"] == 0
        assert payload["max_tokens"] == 2000          # llm1 cap in static_config
        assert payload["model"] == "mini-1"
        assert requests[0].headers["authorization"] == "Bearer test-key"
        assert requests[0].url == "https://llmod.test/v1/chat/completions"

    def test_gpt5_models_get_litellm_compatible_payload(self, env, monkeypatch):
        monkeypatch.setenv("TP_LLM1", "llmod:NBUECSE-gpt-5-mini")
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=CHAT_JSON)

        client, _ = make_client(handler)
        client.chat(modules.LLM1_INTAKE, [{"role": "user", "content": "x"}],
                    role="llm1")
        import json
        payload = json.loads(requests[0].content)
        assert payload["max_completion_tokens"] == 2000
        assert payload["reasoning_effort"] == "low"   # per-role: llm1=low
        assert "temperature" not in payload      # gpt-5 rejects temperature=0
        assert "max_tokens" not in payload

    def test_max_tokens_comes_from_static_config_not_fallback(
            self, env, monkeypatch):
        from tpagent import config
        monkeypatch.setattr(config, "static_config",
                            lambda: {"llm": {"max_tokens": {"llm1": 123}}})
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=CHAT_JSON)

        client, _ = make_client(handler)
        client.chat(modules.LLM1_INTAKE, [{"role": "user", "content": "x"}],
                    role="llm1")
        import json
        assert json.loads(requests[0].content)["max_tokens"] == 123


class TestMockBackend:
    def test_mock_chat_reads_fixture_no_network(self, env):
        def handler(request):                        # any HTTP call is a bug
            raise AssertionError("mock backend must not touch the network")

        client, rec = make_client(handler)
        text = client.chat(modules.LLM2_CODEGEN, [
            {"role": "user", "content": "prompt"}], role="llm2")
        assert text.startswith("/PROG")
        steps = rec.steps
        assert len(steps) == 1
        assert steps[0]["module"] == "LLM2-Codegen"
        assert steps[0]["prompt"]["backend"] == "mock"
        assert steps[0]["prompt"]["max_tokens"] == 3000
        assert steps[0]["response"]["choices"][0]["message"]["content"] == text

    def test_unknown_backend_rejected(self, env, monkeypatch):
        monkeypatch.setenv("TP_LLM1", "openai:gpt")
        client, rec = make_client(lambda r: httpx.Response(200, json={}))
        with pytest.raises(LLMClientError, match="llmod:<model> or mock:<path>"):
            client.chat(modules.LLM1_INTAKE, [], role="llm1")
        assert len(rec.steps) == 0

    def test_missing_key_is_friendly(self, env, monkeypatch):
        monkeypatch.setenv("LLMOD_API_KEY", "")
        client, _ = make_client(lambda r: httpx.Response(200, json=CHAT_JSON))
        with pytest.raises(LLMClientError, match="LLMOD_API_KEY"):
            client.chat(modules.LLM1_INTAKE, [], role="llm1")


class TestRetries:
    def test_transient_failure_retried_once_step_recorded_once(self, env):
        codes = iter([500, 200])

        def handler(request):
            code = next(codes)
            return httpx.Response(code, json=CHAT_JSON if code == 200 else {})

        client, rec = make_client(handler)
        text = client.chat(modules.LLM1_INTAKE, [
            {"role": "user", "content": "x"}], role="llm1")
        assert text == "generated"
        assert len(rec.steps) == 1                   # one logical call

    def test_definitive_4xx_fails_fast_no_retry(self, env):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(401, json={"error": "bad key"})

        client, rec = make_client(handler)
        with pytest.raises(LLMClientError, match="rejected the request"):
            client.chat(modules.LLM1_INTAKE, [
                {"role": "user", "content": "x"}], role="llm1")
        assert len(calls) == 1                       # definitive: no retries
        steps = rec.steps
        assert len(steps) == 1
        assert "HTTP" not in steps[0]["response"]["error"]   # language rule
        assert steps[0]["response"]["detail"] == "HTTP 401"

    def test_non_json_200_body_is_retried_and_recorded(self, env):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, text="<html>gateway hiccup</html>")

        client, rec = make_client(handler)
        with pytest.raises(LLMClientError, match="didn't answer"):
            client.chat(modules.LLM1_INTAKE, [
                {"role": "user", "content": "x"}], role="llm1")
        assert len(calls) == 3
        steps = rec.steps                            # no-bypass: still traced
        assert len(steps) == 1
        assert "valid JSON" in steps[0]["response"]["detail"]

    def test_exhausted_retries_record_error_step_then_raise(self, env):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(503, json={})

        client, rec = make_client(handler)
        with pytest.raises(LLMClientError, match="didn't answer"):
            client.chat(modules.LLM1_INTAKE, [
                {"role": "user", "content": "x"}], role="llm1")
        assert len(calls) == 3                       # 1 try + 2 retries, capped
        steps = rec.steps
        assert len(steps) == 1
        assert "error" in steps[0]["response"]
        assert steps[0]["response"]["detail"] == "HTTP 503"
