"""Renderer snapshot tests (SOFTWARE.md 6.5): byte-identical prompts."""
import json
from pathlib import Path

from tests.conftest import FIXTURES
from tpagent.renderer import GenerateArgs, RenderSession, render
from tpagent.stores.table import parse_scan

SNAPSHOTS = Path(__file__).parent / "snapshots"

CFG = {"defaults": {"speed": "100mm/sec", "pick_speed": "50mm/sec",
                    "term": "FINE", "utool": 1, "uframe": 1,
                    "gripper_settle_sec": 0.5},
       "limits": {"max_speed_mmsec": 250, "max_wait_sec": 10}}


def table():
    return parse_scan(
        (FIXTURES / "reg_io_v1_template.csv").read_text(encoding="utf-8"))


def gen_args() -> GenerateArgs:
    action = json.loads(
        (FIXTURES / "llm1_gen.json").read_text(encoding="utf-8"))
    return GenerateArgs(params=action["params"],
                        program_name=action["program_name"],
                        notes=action["notes"],
                        chunks=["## L - linear motion\nSyntax: L ..."])


def first_prompt() -> str:
    return render(CFG, table(), RenderSession(), gen_args())


def retry_prompt() -> str:
    args = gen_args()
    args.base_draft = "d1"
    args.errors = [{"layer": "grammar", "line": 8, "found": "1.0sec",
                    "suggestion": "WAIT 1.00(sec)"}]
    args.fix_guidance = "Write the wait as WAIT 1.00(sec)."
    sess = RenderSession(
        drafts={"d1": (FIXTURES / "v1.ls").read_text(encoding="utf-8")})
    return render(CFG, table(), sess, args)


class TestSnapshots:
    def test_first_attempt_matches_snapshot(self):
        expected = (SNAPSHOTS / "prompt_first.txt").read_text(
            encoding="utf-8")
        assert first_prompt() == expected

    def test_retry_matches_snapshot(self):
        expected = (SNAPSHOTS / "prompt_retry.txt").read_text(
            encoding="utf-8")
        assert retry_prompt() == expected

    def test_byte_identical_on_repeat(self):
        assert first_prompt() == first_prompt()
        assert retry_prompt() == retry_prompt()


class TestStructure:
    def test_fixed_section_order(self):
        prompt = retry_prompt()
        order = [prompt.find(marker) for marker in (
            "You are a senior FANUC TP programmer", "CELL ", "REFERENCE",
            "TASK:", "PROGRAM NAME:", "PREVIOUS DRAFT")]
        assert all(i >= 0 for i in order) and order == sorted(order)

    def test_table_inserted_verbatim_with_uninitialized_marker(self):
        prompt = first_prompt()
        assert "use ONLY these" in prompt
        assert "PR[5] conveyor pick" in prompt
        assert "PR[10] (no label) (uninitialized)" in prompt

    def test_empty_robot_cell_section(self):
        from tpagent.reg_io import RegIOTable
        prompt = render(CFG, RegIOTable(cell_id="c1", scanned_at=""),
                        RenderSession(), gen_args())
        assert "empty robot" in prompt
        assert "allocate\nsequentially" in prompt or \
               "allocate sequentially" in prompt.replace("\n", " ")

    def test_example_only_when_present(self):
        assert "STYLE EXAMPLE" not in first_prompt()
        sess = RenderSession(example_ls="/PROG E\n/END")
        prompt = render(CFG, table(), sess, gen_args())
        assert "STYLE EXAMPLE" in prompt and "/PROG E" in prompt

    def test_no_leakage_generate_args_has_no_table_or_config_field(self):
        fields = set(GenerateArgs.__dataclass_fields__)
        assert fields == {"params", "program_name", "notes", "chunks",
                          "base_draft", "errors", "fix_guidance"}
