"""reg_io_v1 parser tests (SOFTWARE.md 6.2 / 10) against the canonical fixture."""
import pytest

from tests.conftest import FIXTURES
from tpagent.reg_io import SchemaError, parse_reg_io_csv

META = ("# schema: reg_io_v1\n"
        "# cell_id: testcell\n"
        "# scanned_at: 2026-01-01T00:00:00\n")
HEADER = "type,index,comment,initialized,value\n"


@pytest.fixture(scope="module")
def table():
    raw = (FIXTURES / "reg_io_v1_template.csv").read_text(encoding="utf-8")
    return parse_reg_io_csv(raw)


class TestCanonicalFixture:
    def test_metadata_extraction(self, table):
        assert table.cell_id == "line3_fanuc1"
        assert table.scanned_at == "2026-07-04T10:42:00"

    def test_all_25_rows_kept(self, table):
        assert len(table.entries) == 25
        assert len(table.key_set()) == 25

    def test_unknown_type_kept_and_flagged(self, table):
        f = table.find("F", 12)
        assert f is not None and f.category == "UNKNOWN" and f.direction is None
        assert len(table.flags) == 1
        assert "unknown type 'F'" in table.flags[0]

    def test_uninitialized_uncommented_pr(self, table):
        pr10 = table.find("PR", 10)
        assert pr10 is not None
        assert pr10.initialized is False
        assert pr10.comment == ""

    def test_quoted_comma_comment(self, table):
        assert table.find("SR", 2).comment == "recipe name, active"

    def test_unlabeled_but_real_entries(self, table):
        for t, i in (("R", 4), ("DI", 7), ("UI", 5)):
            e = table.find(t, i)
            assert e is not None and e.comment == "", (t, i)

    def test_register_category_and_initialized(self, table):
        pr5 = table.find("PR", 5)
        assert (pr5.category, pr5.direction, pr5.initialized) == ("REG", None, True)
        assert table.find("PL", 1).category == "REG"

    def test_io_direction_and_none_initialized(self, table):
        for t, i, d in (("DI", 3, "in"), ("RI", 1, "in"), ("GI", 1, "in"),
                        ("AI", 1, "in"), ("DO", 7, "out"), ("RO", 2, "out"),
                        ("UO", 1, "out")):
            e = table.find(t, i)
            assert (e.category, e.direction, e.initialized) == ("IO", d, None), (t, i)

    def test_find_miss_returns_none(self, table):
        assert table.find("PR", 99) is None

    def test_by_note_substring_and_type_filter(self, table):
        assert len(table.by_note("conveyor")) == 3       # PR5, PR6, DI4
        assert len(table.by_note("conveyor", "PR")) == 2
        assert table.by_note("FIXTURE A PLACE")[0].index == 8  # case-insensitive

    def test_by_note_excludes_uninitialized(self, table):
        hits = table.by_note("")            # matches every comment
        assert len(hits) == 24              # everything except PR[10]
        assert not any(e.type == "PR" and e.index == 10 for e in hits)


class TestParserBehaviors:
    def test_comment_whitespace_trimmed(self):
        t = parse_reg_io_csv(META + HEADER + "PR,2,  padded note   ,TRUE,\n")
        assert t.find("PR", 2).comment == "padded note"

    def test_non_numeric_index_skipped_and_flagged(self):
        t = parse_reg_io_csv(META + HEADER + "PR,abc,oops,TRUE,\nR,1,ok,TRUE,0\n")
        assert len(t.entries) == 1
        assert any("non-numeric index" in f for f in t.flags)

    def test_extra_columns_tolerated(self):
        t = parse_reg_io_csv(
            META + "type,index,comment,initialized,value,extra\n"
                   "R,1,counter,TRUE,0,ignored\n")
        assert t.find("R", 1) is not None


class TestSchemaErrors:
    def test_missing_schema_header(self):
        raw = ("# cell_id: c\n# scanned_at: t\n" + HEADER)
        with pytest.raises(SchemaError, match="reg_io_v1"):
            parse_reg_io_csv(raw)

    def test_wrong_schema_value(self):
        raw = ("# schema: reg_io_v2\n# cell_id: c\n# scanned_at: t\n" + HEADER)
        with pytest.raises(SchemaError):
            parse_reg_io_csv(raw)

    def test_missing_cell_id(self):
        raw = ("# schema: reg_io_v1\n# scanned_at: t\n" + HEADER)
        with pytest.raises(SchemaError, match="cell_id"):
            parse_reg_io_csv(raw)

    def test_missing_scanned_at(self):
        raw = ("# schema: reg_io_v1\n# cell_id: c\n" + HEADER)
        with pytest.raises(SchemaError, match="scanned_at"):
            parse_reg_io_csv(raw)

    def test_missing_required_column(self):
        raw = META + "type,index,comment,initialized\nPR,1,x,TRUE\n"
        with pytest.raises(SchemaError, match="value"):
            parse_reg_io_csv(raw)

    def test_messages_are_friendly(self):
        for raw in ("# cell_id: c\n# scanned_at: t\n" + HEADER,
                    "# schema: reg_io_v1\n# scanned_at: t\n" + HEADER):
            with pytest.raises(SchemaError) as ei:
                parse_reg_io_csv(raw)
            assert len(str(ei.value)) > 30 and "ERR" not in str(ei.value)
