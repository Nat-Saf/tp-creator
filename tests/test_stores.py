"""Offline stores tests against the record/replay mock supabase client."""
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import FIXTURES
from tests.mock_supabase import MockSupabase
from tpagent.stores import output, session, table
from tpagent.stores.seed import DEFAULT_CSV, seed, show_row

CSV_PATH = FIXTURES / "reg_io_v1_template.csv"
CSV = CSV_PATH.read_text(encoding="utf-8")

CFG = {"table": {"max_table_age_hours": 72},
       "default_index_map": {"PR": {1: "home"}, "IO": {"RO[1]": "gripper close"}}}
CFG_NO_MAP = {"table": {"max_table_age_hours": 72}, "default_index_map": {}}


def hours_ago(h: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=h)).isoformat(
        timespec="seconds")


class TestMaterialize:
    def test_scan_wins_and_persists_cache_row(self):
        mock = MockSupabase()
        t, source = table.materialize("cellX", CSV, client=mock, config=CFG)
        assert source == "scan"
        assert len(t.entries) == 25 and len(t.flags) == 1
        row = mock.data["reg_io_tables"][0]
        assert row["cell_id"] == "cellX" and row["source"] == "scan"
        assert row["scanned_at"] == "2026-07-04T10:42:00"  # the CSV's own header
        assert len(row["entries"]["entries"]) == 25
        assert len(row["entries"]["flags"]) == 1

    def test_fresh_cache_hit_round_trips_the_table(self):
        mock = MockSupabase()
        table.cache_scan("cellX", CSV, scanned_at=hours_ago(3), client=mock)
        t, source = table.materialize("cellX", None, client=mock, config=CFG)
        assert source == "cache(3h)"
        assert len(t.entries) == 25 and len(t.flags) == 1
        assert t.find("PR", 10).initialized is False        # bool round-trip
        assert t.find("DI", 3).initialized is None
        assert t.find("SR", 2).comment == "recipe name, active"
        assert t.find("RO", 2).direction == "out"

    def test_minutes_age_format(self):
        mock = MockSupabase()
        table.cache_scan("cellX", CSV, scanned_at=hours_ago(0.5), client=mock)
        _, source = table.materialize("cellX", None, client=mock, config=CFG)
        assert source == "cache(30m)"

    def test_stale_cache_falls_to_default_map(self):
        mock = MockSupabase()
        table.cache_scan("cellX", CSV, scanned_at=hours_ago(100), client=mock)
        t, source = table.materialize("cellX", None, client=mock, config=CFG)
        assert source == "default_map"
        assert t.key_set() == {("PR", 1), ("RO", 1)}
        ro = t.find("RO", 1)
        assert ro.category == "IO" and ro.direction == "out"
        assert t.find("PR", 1).comment == "home"

    def test_unparseable_scanned_at_refuses_cache(self):
        mock = MockSupabase()
        table.cache_scan("cellX", CSV, scanned_at="not-a-date", client=mock)
        _, source = table.materialize("cellX", None, client=mock, config=CFG)
        assert source == "default_map"

    def test_no_source_raises_friendly_no_table_source(self):
        with pytest.raises(table.NoTableSource) as ei:
            table.materialize("empty_cell", None,
                              client=MockSupabase(), config=CFG_NO_MAP)
        assert "reg_io_v1" in str(ei.value)

    def test_scan_for_other_cell_does_not_leak(self):
        mock = MockSupabase()
        table.cache_scan("cellA", CSV, scanned_at=hours_ago(1), client=mock)
        _, source = table.materialize("cellB", None, client=mock, config=CFG)
        assert source == "default_map"


class TestSession:
    def test_open_creates_row(self):
        mock = MockSupabase()
        sess = session.open("line3_fanuc1", client=mock)
        rows = mock.data["sessions"]
        assert len(rows) == 1 and rows[0]["cell_id"] == "line3_fanuc1"
        assert sess.id == str(rows[0]["id"])

    def test_draft_ids_increment(self):
        sess = session.open("c1", client=MockSupabase())
        d1 = sess.save_draft("/PROG A\n/END")
        d2 = sess.save_draft("/PROG B\n/END")
        assert d1 == f"{sess.id[:8]}_v1" and d2 == f"{sess.id[:8]}_v2"
        assert sess.get_draft(d2)["n"] == 2
        assert sess.get_draft("missing") is None

    def test_verdict_upsert_and_read(self):
        sess = session.open("c1", client=MockSupabase())
        d = sess.save_draft("/PROG A\n/END")
        sess.save_verdict(d, "fail", errors=[{"layer": "grammar"}])
        sess.save_verdict(d, "pass")            # retry overwrites
        v = sess.get_verdict(d)
        assert v["verdict"] == "pass" and v["errors"] == []

    def test_example_pending_inferred_decisions(self):
        sess = session.open("c1", client=MockSupabase())
        sess.save_example("/PROG E\n/END", {"verdict": "pass"})
        sess.set_pending_question("Which fixture should I place on?")
        sess.append_inferred({"text": "gently", "decision": "settle 1.0s"})
        sess.log_decision("chose fixture A")
        row = sess._row()
        assert row["params"]["example_ls"].startswith("/PROG E")
        assert row["pending_question"].startswith("Which fixture")
        assert row["inferred"][0]["text"] == "gently"
        assert row["decisions"] == ["chose fixture A"]
        sess.set_pending_question(None)
        assert sess.pending_question() is None

    def test_save_example_converts_dataclass_report(self):
        from tpagent.contract import Report
        sess = session.open("c1", client=MockSupabase())
        sess.save_example("/PROG E\n/END", Report(table_source="scan"))
        stored = sess._row()["params"]["example_report"]
        assert isinstance(stored, dict) and stored["table_source"] == "scan"

    def test_revision_of_logged(self):
        sess = session.open("c1", revision_of="abc_v1", client=MockSupabase())
        assert sess.revision_of == "abc_v1"
        assert "revision_of=abc_v1" in sess._row()["decisions"]


class TestOutput:
    def test_save_and_load(self):
        mock = MockSupabase()
        ref = output.save("sid-1", "sid1_v2", "PICK_PLACE",
                          "/PROG PICK_PLACE\n/END", {"retries": 1}, client=mock)
        assert ref == "outputs/sid1_v2"
        row = output.load("sid1_v2", client=mock)
        assert row["program_name"] == "PICK_PLACE"
        assert row["report"] == {"retries": 1}
        assert output.load("nope", client=mock) is None


class TestSeed:
    def test_seed_writes_fresh_demo_row(self):
        mock = MockSupabase()
        row = seed("line3_fanuc1", CSV_PATH, client=mock)
        assert row["cell_id"] == "line3_fanuc1" and row["source"] == "seed"
        age = datetime.now(timezone.utc) - datetime.fromisoformat(row["scanned_at"])
        assert age < timedelta(minutes=5)       # stamped at delivery time
        assert len(row["entries"]["entries"]) == 25

    def test_seeded_row_materializes_as_fresh_cache(self):
        mock = MockSupabase()
        seed("line3_fanuc1", CSV_PATH, client=mock)
        t, source = table.materialize("line3_fanuc1", None,
                                      client=mock, config=CFG)
        assert source == "cache(0m)"
        assert len(t.entries) == 25

    def test_default_csv_is_the_canonical_fixture(self):
        assert DEFAULT_CSV == CSV_PATH

    def test_show_row_summary(self):
        mock = MockSupabase()
        seed("line3_fanuc1", CSV_PATH, client=mock)
        text = show_row("line3_fanuc1", client=mock)
        assert "line3_fanuc1" in text and "entries:    25" in text
        assert "PR[1] home" in text
        assert show_row("ghost", client=mock).startswith("no row")
