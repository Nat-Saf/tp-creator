"""Table-driven validator tests (old guide Phase 2; DESIGN.md 4.9 / 8)."""
import pytest

from tests.conftest import FIXTURES
from tpagent.stores.table import parse_scan
from tpagent.validator import run

LIMITS = {"max_speed_mmsec": 250, "max_wait_sec": 10}


@pytest.fixture(scope="module")
def table():
    return parse_scan(
        (FIXTURES / "reg_io_v1_template.csv").read_text(encoding="utf-8"))


def make_prog(*body_lines: str) -> str:
    mn = "\n".join(f"  {i}:  {line} ;" for i, line in enumerate(body_lines, 1))
    return f"/PROG TEST\n/ATTR\nOWNER = MNEDITOR;\n/MN\n{mn}\n/POS\n/END\n"


KNOWN_GOOD_15 = [
    "UFRAME_NUM=1",
    "UTOOL_NUM=3",
    "!pick from conveyor",
    "J PR[1:home] 100% FINE",
    "L P[2:SafeAbove] R[63:TravelSpd]mm/sec CNT100",
    "L PR[5:conveyor pick] 50mm/sec FINE Offset,PR[2]",
    "C P[2] P[3:end of arc] 150mm/sec FINE",
    "RO[1:gripper close]=ON",
    "DO[375:AirBlow]=PULSE,0.5sec",
    "R[26:PickStep]=1",
    "R[31:Tmp]=R[156:IdxX]*R[158:PitchX]",
    "PR[8,1:PickLoc]=PR[8,1:PickLoc]+R[31:Tmp]",
    "IF DI[592:Tray in]=ON,JMP LBL[11]",
    "SELECT R[26:PickStep]=0,JMP LBL[10]",
    "WAIT DI[370:VacuumReached]=ON TIMEOUT,LBL[90]",
]


class TestGrammar:
    def test_fifteen_known_good_lines_pass(self):
        verdict = run(make_prog(*KNOWN_GOOD_15), None, LIMITS)
        assert verdict.errors == []
        assert verdict.verdict == "pass"
        assert verdict.stats["mn_lines"] == 15
        assert verdict.stats["parsed_ok"] == 15

    def test_empty_bracket_label_rejected(self):
        # PR[10,3:] slipped through a live run - a colon with no label
        # is not pendant syntax
        verdict = run(make_prog("PR[10,3:]=PR[10,3:]-100.0"), None, LIMITS)
        assert verdict.verdict == "fail"
        assert any("empty label" in (e.message or "") for e in verdict.errors)

    def test_more_good_forms(self):
        verdict = run(make_prog(
            "LBL[10]", "JMP LBL[99]", "CALL SET_STR('No PBS tray',10)",
            "WAIT   0.50(sec)", "=1,JMP LBL[20]", "ELSE,JMP LBL[10]",
            "PAUSE", "TIMER[2]=START", "OVERRIDE=50%",
            "PR[8:PickLoc]=P[1:Slot00]", "R[10:Error Code]=201",
        ), None, LIMITS)
        assert verdict.errors == []

    def test_invented_instruction_lists_keyword_set(self):
        verdict = run(make_prog("GRIP_SOFT RO[1]"), None, LIMITS)
        [err] = verdict.errors
        assert err.layer == "grammar" and err.line == 1
        assert err.found == "GRIP_SOFT"
        assert "WAIT" in err.expected and "J" in err.expected
        assert err.suggestion is None       # nothing within distance 2

    def test_typo_gets_unique_suggestion(self):
        verdict = run(make_prog("WIAT 1.00(sec)"), None, LIMITS)
        [err] = verdict.errors
        assert err.suggestion == "WAIT"

    def test_invented_option_after_fine(self):
        verdict = run(make_prog("L PR[5:conveyor pick] 100mm/sec FINE Grip"),
                      None, LIMITS)
        [err] = verdict.errors
        assert err.layer == "grammar" and err.found == "Grip"
        assert "Offset,PR[i]" in err.expected and "ACC<n>" in err.expected

    def test_wait_wrong_form_with_suggestion(self):
        verdict = run(make_prog("WAIT 1.0sec"), None, LIMITS)
        [err] = verdict.errors
        assert err.layer == "grammar"
        assert err.found == "1.0sec"
        assert err.expected_form.startswith("WAIT <t>.00(sec)")
        assert err.suggestion == "WAIT 1.00(sec)"

    def test_cnt_out_of_range(self):
        verdict = run(make_prog("L PR[5] 100mm/sec CNT150"), None, LIMITS)
        [err] = verdict.errors
        assert sorted(err.expected) == ["CNT0-100", "FINE"]

    def test_joint_speed_unit_on_linear_rejected(self):
        verdict = run(make_prog("L PR[5] 100% FINE"), None, LIMITS)
        [err] = verdict.errors
        assert any("mm/sec" in e for e in err.expected)

    def test_mixed_and_or_rejected(self):
        verdict = run(make_prog(
            "IF DI[3]=ON AND DI[4]=ON OR R[1]=1,JMP LBL[1]"), None, LIMITS)
        [err] = verdict.errors
        assert "never both" in err.message

    def test_missing_envelope(self):
        verdict = run("1: J P[1] 100% FINE ;", None, LIMITS)
        [err] = verdict.errors
        assert "missing" in err.message and "/PROG" in err.message


class TestVerifierRegressions:
    """Fixes driven by the adversarial verification pass."""

    def test_parenthesized_rhs_from_our_programs(self):
        verdict = run(make_prog(
            "R[31:PickTmp]=(R[156:PBSPickX]*R[158:PBSPitchX])",
            "PR[8,1]=(PR[8,1]+R[31:PickTmp])",
            "R[156:PBSPickX]=(R[156:PBSPickX]+1)"), None, LIMITS)
        assert verdict.errors == []

    def test_unclosed_paren_rejected(self):
        verdict = run(make_prog("R[1]=(-5"), None, LIMITS)
        [err] = verdict.errors
        assert ")" in err.expected

    def test_leading_dot_and_register_waits(self):
        verdict = run(make_prog("WAIT .1(sec)", "WAIT   .50(sec)",
                                "WAIT R[3:settle time](sec)"), None, LIMITS)
        assert verdict.errors == []

    def test_malformed_assignment_errors_not_crashes(self):
        for bad in ("R=5", "RO=ON", "R[ 1 ]=5", "R[R[1]]=25",
                    "PR[R[2]]=LPOS"):
            verdict = run(make_prog(bad), None, LIMITS)
            assert verdict.verdict == "fail", bad
            assert verdict.errors[0].layer == "grammar", bad

    def test_joint_speed_percent_range(self):
        for bad in ("J P[1] 150% FINE", "J P[1] 0% FINE"):
            verdict = run(make_prog(bad), None, LIMITS)
            [err] = verdict.errors
            assert "<1-100>%" in err.expected, bad
        assert run(make_prog("J P[1] 100% FINE",
                             "J P[1] R[7]% FINE"), None, LIMITS).errors == []

    def test_other_units_converted_for_speed_cap(self):
        verdict = run(make_prog("L P[1] 60000cm/min FINE"), None, LIMITS)
        [err] = verdict.errors
        assert err.layer == "limits" and "10000" in err.message

    def test_zero_speed_rejected(self):
        verdict = run(make_prog("L P[1] 0mm/sec FINE"), None, LIMITS)
        [err] = verdict.errors
        assert "greater than zero" in err.message

    def test_select_trailing_garbage_rejected(self):
        for bad in ("SELECT R[1]=1,JMP LBL[10] junk",
                    "=1,JMP LBL[20] junk", "ELSE,JMP LBL[30] junk"):
            assert run(make_prog(bad), None, LIMITS).verdict == "fail", bad

    def test_wait_mixed_and_or_rejected(self):
        verdict = run(make_prog(
            "WAIT DI[3]=ON AND DI[4]=ON OR R[1]=1"), None, LIMITS)
        [err] = verdict.errors
        assert "never both" in err.message

    def test_flag_refs_existence_checked(self, table):
        verdict = run(make_prog("F[99]=ON"), table, LIMITS)
        [err] = verdict.errors
        assert err.layer == "existence" and err.ref == "F[99]"

    def test_pos_section_optional(self):
        text = ("/PROG NOPOS\n/MN\n  1:  J PR[1] 100% FINE ;\n"
                "  2:  L PR[2] 400mm/sec FINE ;\n/END\n")
        verdict = run(text, None, LIMITS)
        [err] = verdict.errors            # limits still sees the body
        assert err.layer == "limits"
        assert verdict.stats["mn_lines"] == 2

    def test_override_forms_and_range(self):
        assert run(make_prog("OVERRIDE=50%", "OVERRIDE=R[8:line speed]%"),
                   None, LIMITS).errors == []
        [err] = run(make_prog("OVERRIDE=250%"), None, LIMITS).errors
        assert "1% and 100%" in err.message

    def test_payload_group_form(self):
        assert run(make_prog("PAYLOAD[GP1:2]", "PAYLOAD[1]"),
                   None, LIMITS).errors == []

    def test_scalar_types_reject_2d_index(self):
        assert run(make_prog("R[1,2]=5"), None, LIMITS).verdict == "fail"

    def test_dedupe_adopts_later_label_for_suggestion(self, table):
        verdict = run(make_prog(
            "L PR[10] 100mm/sec FINE",
            "L PR[10:conveyor approach] 50mm/sec FINE"), table, LIMITS)
        assert verdict.errors == []
        [warning] = verdict.warnings
        assert "PR[6]" in warning


class TestExistence:
    def test_not_in_table_carries_known_set(self, table):
        verdict = run(make_prog("L PR[99] 100mm/sec FINE"), table, LIMITS)
        [err] = verdict.errors
        assert err.layer == "existence" and err.ref == "PR[99]"
        assert "not in this cell's register map" in err.message
        assert err.known["5"] == "conveyor pick"
        assert "10" not in err.known        # uninitialized rows aren't offered

    def test_exists_uninitialized_is_warning_with_did_you_mean(self, table):
        # owner decision: untaught-but-existing refs warn, never block
        verdict = run(make_prog(
            "L PR[10:conveyor approach] 100mm/sec FINE"), table, LIMITS)
        assert verdict.verdict == "pass" and verdict.errors == []
        [warning] = verdict.warnings
        assert "PR[10]" in warning and "PR[6]" in warning
        assert "teach it" in warning

    def test_uninitialized_without_label_plain_warning(self, table):
        verdict = run(make_prog("L PR[10] 100mm/sec FINE"), table, LIMITS)
        assert verdict.errors == []
        [warning] = verdict.warnings
        assert "not yet taught" in warning and "PR[6]" not in warning

    def test_duplicate_refs_reported_once_first_line(self, table):
        verdict = run(make_prog("L PR[99] 100mm/sec FINE",
                                "L PR[99] 50mm/sec FINE"), table, LIMITS)
        [err] = verdict.errors
        assert err.line == 1

    def test_empty_robot_skips_existence(self):
        verdict = run(make_prog("L PR[99] 100mm/sec FINE",
                                "RO[77]=ON"), None, LIMITS)
        assert verdict.errors == [] and verdict.verdict == "pass"

    def test_taught_positions_not_symbol_checked(self, table):
        verdict = run(make_prog("L P[42:nowhere] 100mm/sec FINE"),
                      table, LIMITS)
        assert verdict.errors == []

    def test_comment_refs_ignored(self, table):
        verdict = run(make_prog("!uses PR[99] later"), table, LIMITS)
        assert verdict.errors == []


class TestSeededDestination:
    def test_seeding_an_untaught_destination_blocks(self, table):
        v = run(make_prog("PR[10]=PR[1]",
                          "J PR[1:home] 100% FINE",
                          "L PR[10] 100mm/sec FINE"), table, LIMITS)
        assert v.verdict == "fail"
        assert any("untaught and used as a move target" in (e.message or "")
                   for e in v.errors)

    def test_disguised_seeding_with_filler_offsets_blocks(self, table):
        # the model gamed the old code-shape exemption with a fake
        # element line - only a scratch table note unlocks writes now
        v = run(make_prog("PR[10]=PR[1]",
                          "PR[10,3]=PR[10,3]+100",
                          "J PR[1:home] 100% FINE",
                          "L PR[10] 100mm/sec FINE"), table, LIMITS)
        assert v.verdict == "fail"
        assert any("untaught and used as a move target" in (e.message or "")
                   for e in v.errors)

    def test_note_marked_scratch_register_may_be_written(self, table):
        from tpagent.stores.table import apply_edits
        marked, _, _, _ = apply_edits(table, [
            {"type": "PR", "index": 10, "comment": "scratch for offsets"}])
        v = run(make_prog("PR[10]=PR[6]",
                          "PR[10,3]=PR[10,3]-100",
                          "L PR[10] 50mm/sec FINE"), marked, LIMITS)
        assert not [e for e in v.errors if e.layer == "existence"]
        assert any("not yet taught" in w for w in v.warnings)


class TestLimits:
    def test_speed_over_limit(self, table):
        verdict = run(make_prog("L PR[5] 400mm/sec FINE"), table, LIMITS)
        [err] = verdict.errors
        assert err.layer == "limits" and "400mm/sec" in err.found
        assert "250" in err.message
        assert verdict.stats["limits_ok"] is False

    def test_wait_over_limit(self):
        verdict = run(make_prog("WAIT 12.00(sec)"), None, LIMITS)
        [err] = verdict.errors
        assert err.layer == "limits" and "10" in err.message

    def test_within_limits_ok(self, table):
        verdict = run(make_prog("L PR[5] 250mm/sec FINE",
                                "WAIT 10.00(sec)"), table, LIMITS)
        assert verdict.errors == [] and verdict.stats["limits_ok"] is True


class TestModes:
    def test_syntax_report_runs_grammar_only(self, table):
        prog = make_prog("GRIP_SOFT RO[1]",           # grammar error
                         "L PR[99] 400mm/sec FINE")   # existence + limits
        verdict = run(prog, table, LIMITS, mode="syntax_report")
        assert [e.layer for e in verdict.errors] == ["grammar"]
        assert "limits_ok" not in verdict.stats

    def test_gate_runs_all_three(self, table):
        prog = make_prog("GRIP_SOFT RO[1]",
                         "L PR[99] 400mm/sec FINE")
        verdict = run(prog, table, LIMITS)
        assert sorted(e.layer for e in verdict.errors) == [
            "existence", "grammar", "limits"]


class TestV1Fixture:
    """DESIGN.md section 8: the canonical seeded-errors program."""

    def test_full_verdict(self, table):
        text = (FIXTURES / "v1.ls").read_text(encoding="utf-8")
        verdict = run(text, table, LIMITS)
        assert verdict.verdict == "fail"

        [wait_err] = verdict.errors
        assert wait_err.layer == "grammar" and wait_err.line == 8
        assert wait_err.found == "1.0sec"
        assert wait_err.suggestion == "WAIT 1.00(sec)"

        [pr_warning] = verdict.warnings   # PR[10] untaught -> advisory
        assert "PR[10]" in pr_warning and "PR[6]" in pr_warning

        assert verdict.stats == {"mn_lines": 14, "parsed_ok": 13,
                                 "limits_ok": True}

    def test_v1_syntax_report_only_wait_error(self, table):
        text = (FIXTURES / "v1.ls").read_text(encoding="utf-8")
        verdict = run(text, table, LIMITS, mode="syntax_report")
        assert [e.line for e in verdict.errors] == [8]
