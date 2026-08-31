"""Offline stores tests: table sources (upload > default > none) + the
Supabase-backed session/output stores against the record/replay mock."""
import pytest

from tests.conftest import FIXTURES
from tests.mock_supabase import MockSupabase
from tpagent.stores import output, session, table
from tpagent.stores.table import SchemaError, materialize, normalize_scan

CSV_PATH = FIXTURES / "reg_io_v1_template.csv"
CSV = CSV_PATH.read_text(encoding="utf-8")

BARE = ("type,index,comment\n"
        "PR,1,home\n"
        'SR,2,"recipe name, active"\n'
        "DO,7,green lamp\n")


class TestMaterialize:
    def test_uploaded_strict_scan_wins(self):
        t, source = materialize("line3_fanuc1", CSV)
        assert source == "scan"
        assert len(t.entries) == 25 and len(t.flags) == 1
        assert t.scanned_at == "2026-07-04T10:42:00"    # the CSV's own header

    def test_default_table_serves_when_no_scan(self):
        t, source = materialize("line3_fanuc1", None)
        assert source == "default_table"
        assert len(t.entries) == 25
        assert t.find("PR", 5).comment == "conveyor pick"

    def test_blank_scan_falls_to_default(self):
        _, source = materialize("line3_fanuc1", "   \n ")
        assert source == "default_table"

    def test_foreign_cell_gets_empty_robot_from_default(self):
        # the strict default file names line3_fanuc1; other cells get none
        t, source = materialize("another_cell", None)
        assert source == "none" and t.entries == []

    def test_missing_default_file_means_empty_robot(self, monkeypatch,
                                                    tmp_path):
        monkeypatch.setattr(table, "DEFAULT_TABLE", tmp_path / "nope.csv")
        t, source = materialize("line3_fanuc1", None)
        assert source == "none" and t.entries == []

    def test_broken_default_file_means_empty_robot(self, monkeypatch,
                                                   tmp_path):
        bad = tmp_path / "default.csv"
        bad.write_text("just,garbage\n1,2\n", encoding="utf-8")
        monkeypatch.setattr(table, "DEFAULT_TABLE", bad)
        _, source = materialize("line3_fanuc1", None)
        assert source == "none"

    def test_cross_cell_strict_upload_rejected(self):
        with pytest.raises(SchemaError, match="another_cell"):
            materialize("another_cell", CSV)

    def test_default_table_parsed_once_until_file_changes(self, monkeypatch,
                                                          tmp_path):
        import os
        f = tmp_path / "default.csv"
        f.write_text("type,index,comment\nPR,1,home\n", encoding="utf-8")
        monkeypatch.setattr(table, "DEFAULT_TABLE", f)
        t1, _ = materialize("c1", None)
        t2, _ = materialize("c1", None)
        assert t1 is t2                     # same cached parse
        f.write_text("type,index,comment\nPR,2,dock\n", encoding="utf-8")
        os.utime(f, (1, 1))                 # force a distinct mtime
        t3, _ = materialize("c1", None)
        assert t3 is not t1 and t3.find("PR", 2) is not None


class TestNormalization:
    def test_strict_file_passes_verbatim(self):
        assert normalize_scan(CSV, "line3_fanuc1") == CSV

    def test_bare_csv_uploads_as_scan(self):
        t, source = materialize("line3_fanuc1", BARE)
        assert source == "scan"
        assert t.cell_id == "line3_fanuc1"              # synthesized meta
        assert t.find("PR", 1).comment == "home"
        assert t.find("PR", 1).initialized is True      # padded TRUE
        assert t.find("SR", 2).comment == "recipe name, active"
        assert t.find("DO", 7).direction == "out"

    def test_ragged_rows_padded(self):
        t, _ = materialize("c1", "type,index,comment\nPR,3\nR,1,counter\n")
        assert t.find("PR", 3).comment == ""
        assert t.find("R", 1).comment == "counter"

    def test_full_bare_header_kept(self):
        bare = ("type,index,comment,initialized,value\n"
                "PR,9,fixture B,FALSE,\n")
        t, _ = materialize("c1", bare)
        assert t.find("PR", 9).initialized is False     # not padded over

    def test_missing_type_or_index_rejected_friendly(self):
        with pytest.raises(SchemaError, match="'type' and 'index'"):
            materialize("c1", "name,pos\nfoo,1\n")

    def test_blank_upload_is_no_scan_but_empty_normalize_rejects(self):
        # materialize treats whitespace-only as "no scan sent"...
        _, source = materialize("another_cell", "\n  \n")
        assert source == "none"
        # ...while the normalizer itself names the empty-file problem
        with pytest.raises(SchemaError, match="empty"):
            normalize_scan("\n  \n", "c1")


class TestApplyEdits:
    """apply_edits: add new entries or update existing note/value; the
    input table (and any file) is never touched."""

    def test_new_register_added_untaught(self):
        t, _ = materialize("line3_fanuc1", CSV)
        t2, added, updated, refused = table.apply_edits(
            t, [{"type": "PR", "index": 2, "comment": "position 2"}])
        assert [(e.type, e.index) for e in added] == [("PR", 2)]
        assert updated == [] and refused == []
        assert t2.find("PR", 2).initialized is False    # new = untaught
        assert t2.find("PR", 2).comment == "position 2"
        assert t.find("PR", 2) is None      # the input table is untouched

    def test_existing_entry_note_updated_taught_state_kept(self):
        t, _ = materialize("line3_fanuc1", CSV)
        t2, added, updated, refused = table.apply_edits(
            t, [{"type": "PR", "index": 5, "comment": "main pick point"}])
        assert added == [] and refused == []
        assert [(e.type, e.index) for e in updated] == [("PR", 5)]
        assert t2.find("PR", 5).comment == "main pick point"
        assert t2.find("PR", 5).initialized is True   # taught state kept
        assert t.find("PR", 5).comment == "conveyor pick"   # input intact

    def test_identical_update_is_a_noop(self):
        t, _ = materialize("line3_fanuc1", CSV)
        t2, added, updated, _ = table.apply_edits(
            t, [{"type": "PR", "index": 5, "comment": "conveyor pick"}])
        assert added == [] and updated == [] and t2 is t

    def test_io_direction_and_bad_entries(self):
        t, _ = materialize("line3_fanuc1", CSV)
        t2, added, updated, refused = table.apply_edits(t, [
            {"type": "DO", "index": 9, "comment": "spare lamp"},
            {"type": "XX", "index": 1},
            {"type": "DO", "index": 0}])
        assert [(e.type, e.index) for e in added] == [("DO", 9)]
        assert t2.find("DO", 9).direction == "out"
        assert len(refused) == 2

    def test_value_recorded_and_round_trips(self):
        t, _ = materialize("line3_fanuc1", CSV)
        t2, added, updated, _ = table.apply_edits(t, [
            {"type": "DO", "index": 100, "comment": "dispenser on",
             "value": "OFF"}])
        assert t2.find("DO", 100).value == "OFF"
        back = table.parse_scan(table.to_csv(t2))     # writer round-trips
        assert back.find("DO", 100).comment == "dispenser on"
        assert back.find("DO", 100).value == "OFF"
        assert len(back.entries) == len(t2.entries)
        assert back.cell_id == t2.cell_id

    def test_duplicate_within_request_last_wins_as_update(self):
        t, _ = materialize("line3_fanuc1", CSV)
        t2, added, updated, refused = table.apply_edits(t, [
            {"type": "R", "index": 40, "comment": "a"},
            {"type": "R", "index": 40, "comment": "b"}])
        assert len(added) == 1 and len(updated) == 1 and refused == []
        assert t2.find("R", 40).comment == "b"


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
