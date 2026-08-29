"""Level-A gate tests for tpagent/contract.py (SOFTWARE.md 6.1)."""
from tpagent.contract import (
    LIMIT_KEYS,
    OVERRIDABLE_DEFAULTS,
    Report,
    Request,
    Response,
    validate_request,
)


def make_request(**kw) -> Request:
    base = dict(prompt="pick a part from the conveyor", cell_id="line3_fanuc1")
    base.update(kw)
    return Request(**base)


class TestValidateRequest:
    def test_valid_minimal_request_passes(self):
        assert validate_request(make_request()) is None

    def test_valid_override_passes(self):
        req = make_request(config_overrides={"speed": "80mm/sec"})
        assert validate_request(req) is None

    def test_every_overridable_default_passes(self):
        req = make_request(config_overrides={k: "x" for k in OVERRIDABLE_DEFAULTS})
        assert validate_request(req) is None

    def test_empty_prompt_rejected(self):
        msg = validate_request(make_request(prompt=""))
        assert msg is not None and "empty" in msg.lower()

    def test_whitespace_prompt_rejected(self):
        assert validate_request(make_request(prompt="   \n\t")) is not None

    def test_missing_cell_id_rejected(self):
        msg = validate_request(make_request(cell_id=""))
        assert msg is not None and "cell" in msg.lower()

    def test_limit_override_rejected(self):
        for key in LIMIT_KEYS:
            msg = validate_request(make_request(config_overrides={key: 1}))
            assert msg is not None and "limit" in msg.lower(), key

    def test_limit_override_rejected_even_alongside_valid_keys(self):
        req = make_request(
            config_overrides={"speed": "80mm/sec", "max_speed_mmsec": 9000})
        assert validate_request(req) is not None

    def test_unknown_override_key_rejected_and_lists_valid_keys(self):
        msg = validate_request(make_request(config_overrides={"turbo": True}))
        assert msg is not None and "turbo" in msg
        assert "speed" in msg  # names the overridable defaults

    def test_invalid_rag_backend_rejected(self):
        assert validate_request(make_request(rag_backend="cloud")) is not None

    def test_both_rag_backends_pass(self):
        assert validate_request(make_request(rag_backend="online")) is None
        assert validate_request(make_request(rag_backend="local")) is None

    def test_messages_are_friendly_sentences(self):
        # Language rule: no status-code language reaches a human.
        for bad in (make_request(prompt=""),
                    make_request(cell_id=""),
                    make_request(config_overrides={"max_wait_sec": 1}),
                    make_request(config_overrides={"warp": 1})):
            msg = validate_request(bad)
            assert msg and len(msg) > 20 and "ERR" not in msg


class TestJsonRoundTrip:
    def test_request_round_trip(self):
        req = make_request(scan="# schema: reg_io_v1\n...",
                           config_overrides={"speed": "80mm/sec"},
                           answers={"reply": "fixture A"})
        assert Request.from_json(req.to_json()) == req

    def test_response_round_trip_rebuilds_report(self):
        resp = Response(status="ok", draft_id="d1", program_ls="/PROG X\n/END",
                        report=Report(table_source="scan", retries=1))
        back = Response.from_json(resp.to_json())
        assert back == resp
        assert isinstance(back.report, Report)

    def test_response_without_report_round_trips(self):
        resp = Response(status="needs_clarification",
                        questions=["Which fixture should I place on?"])
        assert Response.from_json(resp.to_json()) == resp
