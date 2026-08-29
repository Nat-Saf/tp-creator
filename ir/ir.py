"""ir.py -- Typed intermediate representation of FANUC TP programs.

Pydantic v2 schema covering the TP instruction set of the R-30iB (Mate) Plus,
HandlingTool V9.40, operator manual Chapter 7. Successor of the fanuc-tp-gen
schema: the 76 stub classes are now filled with fields and validators.

Roles in the tp-creator architecture (this module is NOT in the v0 runtime loop):
  1. Source of truth for RAG "instruction cards" (one card per model, generated).
  2. The future structured-generation path: LLM #2 emitting IR JSON validated
     here, rendered to .ls -- the guaranteed-syntax alternative to free text.
  3. Reference for the validator's grammar families (same taxonomy, same names).

Conventions:
  - Every instruction has a Literal `type` discriminator (snake_case).
  - Cross-field constraints live in model validators; range constraints in Field.
  - Manual section references in each docstring (V9.40 Ch.7 numbering).
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# =====================================================================
# References and helper types
# =====================================================================

class PosRef(Strict):
    """P[i] (program-local) or PR[i] (position register) motion target."""
    kind: Literal["P", "PR"]
    index: int = Field(ge=1, le=9999)
    comment: Optional[str] = Field(default=None, max_length=16)


class RegRef(Strict):
    """R[i] numeric register."""
    index: int = Field(ge=1, le=200)
    comment: Optional[str] = Field(default=None, max_length=16)


class PosRegRef(Strict):
    """PR[i] or element PR[i, j] (j: 1..6 axis / X Y Z W P R)."""
    index: int = Field(ge=1, le=100)
    element: Optional[int] = Field(default=None, ge=1, le=9)
    comment: Optional[str] = Field(default=None, max_length=16)


class StrRegRef(Strict):
    """SR[i] string register."""
    index: int = Field(ge=1, le=25)


class PalletRegRef(Strict):
    """PL[i] pallet register (row, column, layer)."""
    index: int = Field(ge=1, le=32)


class ArgRef(Strict):
    """AR[i] -- argument passed via CALL prog(a1, a2, ...)."""
    index: int = Field(ge=1, le=10)


IOType = Literal["DI", "DO", "RI", "RO", "UI", "UO", "SI", "SO",
                 "GI", "GO", "AI", "AO", "F", "M"]
IO_INPUTS = {"DI", "RI", "UI", "SI", "GI", "AI"}
IO_OUTPUTS = {"DO", "RO", "UO", "SO", "GO", "AO"}


class IORef(Strict):
    io_type: IOType
    index: int = Field(ge=1, le=512)
    comment: Optional[str] = Field(default=None, max_length=16)

    @property
    def is_output(self) -> bool:
        return self.io_type in IO_OUTPUTS or self.io_type in ("F", "M")


class Constant(Strict):
    value: float | int | str | bool


Operand = Union[Constant, RegRef, PosRegRef, StrRegRef, ArgRef, IORef, PalletRegRef]

ArithOp = Literal["+", "-", "*", "/", "DIV", "MOD"]


class ArithTerm(Strict):
    op: ArithOp
    operand: Operand


class ValueExpr(Strict):
    """first [op operand]* -- TP register arithmetic chain (Ch.7.3).
    TP evaluates left to right; a chain may not mix * / with + - freely on
    the pendant, so renderers should parenthesize per manual rules."""
    first: Operand
    terms: list[ArithTerm] = Field(default_factory=list, max_length=5)


CmpOp = Literal["=", "<>", "<", ">", "<=", ">="]


class Comparison(Strict):
    """R[1] > 5, AI[2] <= R[3], DI[7] = ON ... (Ch.7.5, 7.6)."""
    lhs: Operand
    op: CmpOp
    rhs: Union[Operand, Literal["ON", "OFF"]]


class ConditionGroup(Strict):
    """Multiple comparisons joined by AND *or* OR -- TP forbids mixing both
    in one instruction (Ch.7.5.1)."""
    logic: Literal["AND", "OR"]
    terms: list[Comparison] = Field(min_length=2, max_length=5)


Condition = Union[Comparison, ConditionGroup]


class Speed(Strict):
    """Motion speed with unit. Legal units depend on motion type (validated
    in MotionInstr): J -> % | sec | msec ; L/C/A -> mm/sec, cm/min, inch/min,
    deg/sec, sec, msec."""
    value: float = Field(gt=0)
    unit: Literal["%", "mm/sec", "cm/min", "inch/min", "deg/sec", "sec", "msec"]


class Termination(Strict):
    """FINE or CNT0..CNT100 (CD0..CD100 on some options; not modeled v1)."""
    kind: Literal["FINE", "CNT"]
    value: Optional[int] = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def _cnt_needs_value(self):
        if self.kind == "CNT" and self.value is None:
            raise ValueError("CNT termination requires value 0..100")
        if self.kind == "FINE" and self.value is not None:
            raise ValueError("FINE takes no value")
        return self


# ---------------- motion options (Ch.7.2.x) ----------------

class OptWrist(Strict):
    type: Literal["wjnt"] = "wjnt"                       # Wjnt


class OptCoord(Strict):
    type: Literal["coord"] = "coord"                     # COORD


class OptAcceleration(Strict):
    type: Literal["acc"] = "acc"                         # ACC50..ACC150(+)
    value: int = Field(ge=0, le=150)


class OptSkip(Strict):
    type: Literal["skip"] = "skip"                       # Skip,LBL[n]
    label: int = Field(ge=1, le=32767)


class OptBreak(Strict):
    type: Literal["break"] = "break"                     # BREAK


class OptOffsetPR(Strict):
    type: Literal["offset_pr"] = "offset_pr"             # Offset,PR[n]
    pr: PosRegRef


class OptOffsetCond(Strict):
    type: Literal["offset_cond"] = "offset_cond"         # Offset (uses OFFSET CONDITION)


class OptToolOffsetPR(Strict):
    type: Literal["tool_offset_pr"] = "tool_offset_pr"   # Tool_Offset,PR[n]
    pr: PosRegRef


class OptToolOffsetCond(Strict):
    type: Literal["tool_offset_cond"] = "tool_offset_cond"


class OptIncremental(Strict):
    type: Literal["inc"] = "inc"                         # INC


class OptTimeBefore(Strict):
    """TB t sec, CALL prog / DO[n]=ON (Ch.7.2: TIME BEFORE)."""
    type: Literal["time_before"] = "time_before"
    seconds: float = Field(ge=0, le=30)
    action_call: Optional[str] = None
    action_io: Optional["IOAssignInstr"] = None

    @model_validator(mode="after")
    def _one_action(self):
        if bool(self.action_call) == bool(self.action_io):
            raise ValueError("TB takes exactly one action: CALL or IO assign")
        return self


class OptTimeAfter(OptTimeBefore.__base__ if False else Strict):  # keep simple
    type: Literal["time_after"] = "time_after"
    seconds: float = Field(ge=0, le=30)
    action_call: Optional[str] = None
    action_io: Optional["IOAssignInstr"] = None

    @model_validator(mode="after")
    def _one_action(self):
        if bool(self.action_call) == bool(self.action_io):
            raise ValueError("TA takes exactly one action: CALL or IO assign")
        return self


class OptDistanceBefore(Strict):
    type: Literal["distance_before"] = "distance_before"  # DB d mm, action
    mm: float = Field(gt=0)
    action_call: str


class OptPath(Strict):
    type: Literal["pth"] = "pth"                          # PTH


class OptApproachLD(Strict):
    type: Literal["ap_ld"] = "ap_ld"                      # AP_LDn
    value: int = Field(ge=1, le=100)


class OptRetractLD(Strict):
    type: Literal["rt_ld"] = "rt_ld"                      # RT_LDn
    value: int = Field(ge=1, le=100)


class OptEV(Strict):
    type: Literal["ev"] = "ev"                            # EV n% (extended axis)
    percent: int = Field(ge=1, le=100)


class OptIndEV(Strict):
    type: Literal["ind_ev"] = "ind_ev"                    # Ind.EV n%
    percent: int = Field(ge=1, le=100)


class OptMROT(Strict):
    type: Literal["mrot"] = "mrot"                        # MROT (minimal rotation)


MotionOption = Annotated[
    Union[OptWrist, OptCoord, OptAcceleration, OptSkip, OptBreak,
          OptOffsetPR, OptOffsetCond, OptToolOffsetPR, OptToolOffsetCond,
          OptIncremental, OptTimeBefore, OptTimeAfter, OptDistanceBefore,
          OptPath, OptApproachLD, OptRetractLD, OptEV, OptIndEV, OptMROT],
    Field(discriminator="type")]


# =====================================================================
# Instructions
# =====================================================================

# ---------------- 1. Motion (Ch.7.2) ----------------

class MotionInstr(Strict):
    """J P[1] 100% FINE ; L PR[5] 100mm/sec CNT50 Offset,PR[2] ;
    C P[2] P[3] 200mm/sec FINE ; A P[4] 150mm/sec FINE (4D graphics arc)."""
    type: Literal["motion"] = "motion"
    motion: Literal["J", "L", "C", "A"]
    target: PosRef
    via: Optional[PosRef] = None                 # circle mid-point (C only)
    speed: Speed
    term: Termination
    options: list[MotionOption] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def _rules(self):
        if self.motion == "C" and self.via is None:
            raise ValueError("C motion requires a via point")
        if self.motion != "C" and self.via is not None:
            raise ValueError("via point only on C motion")
        joint_units = {"%", "sec", "msec"}
        path_units = {"mm/sec", "cm/min", "inch/min", "deg/sec", "sec", "msec"}
        ok = joint_units if self.motion == "J" else path_units
        if self.speed.unit not in ok:
            raise ValueError(f"{self.motion} motion cannot use unit {self.speed.unit}")
        return self


# ---------------- 2. Registers (Ch.7.3) ----------------

class RegisterAssignInstr(Strict):
    """R[1]=R[2]+5 ; R[3]=DI[1] ; R[4]=TIMER[1] not modeled (v2)."""
    type: Literal["register_assign"] = "register_assign"
    target: RegRef
    value: ValueExpr


class PosRegAssignInstr(Strict):
    """PR[1]=LPOS / JPOS / P[2] / PR[3] / UFRAME[1] / UTOOL[1]."""
    type: Literal["posreg_assign"] = "posreg_assign"
    target: PosRegRef
    source: Union[Literal["LPOS", "JPOS"], PosRef, PosRegRef]
    arith: Optional[tuple[Literal["+", "-"], PosRegRef]] = None


class PosRegElemAssignInstr(Strict):
    """PR[1,3]=R[2]+10 ; element arithmetic."""
    type: Literal["posreg_elem_assign"] = "posreg_elem_assign"
    target: PosRegRef
    value: ValueExpr

    @model_validator(mode="after")
    def _needs_element(self):
        if self.target.element is None:
            raise ValueError("element assignment requires PR[i, j]")
        return self


class StrRegAssignInstr(Strict):
    """SR[1]='ABC' ; SR[1]=SR[2]+SR[3] (concat)."""
    type: Literal["strreg_assign"] = "strreg_assign"
    target: StrRegRef
    parts: list[Union[Constant, StrRegRef, RegRef]] = Field(min_length=1, max_length=3)


class PalletRegAssignInstr(Strict):
    """PL[1]=[1,1,1] ; PL[1]=PL[2]."""
    type: Literal["palletreg_assign"] = "palletreg_assign"
    target: PalletRegRef
    value: Union[tuple[int, int, int], PalletRegRef]


# ---------------- 3. I/O (Ch.7.4) ----------------

class IOAssignInstr(Strict):
    """DO[1]=ON ; RO[2]=OFF ; DO[3]=R[1] ; GO[1]=R[2] ; AO[1]=4.5 ;
    F[1]=(ON) flags."""
    type: Literal["io_assign"] = "io_assign"
    target: IORef
    value: Union[Literal["ON", "OFF"], ValueExpr]

    @model_validator(mode="after")
    def _outputs_only(self):
        if not self.target.is_output:
            raise ValueError(f"cannot assign to input {self.target.io_type}[{self.target.index}]")
        return self


class IOPulseInstr(Strict):
    """DO[1]=PULSE ; DO[1]=PULSE,2.0sec."""
    type: Literal["io_pulse"] = "io_pulse"
    target: IORef
    width_sec: Optional[float] = Field(default=None, gt=0, le=25.5)

    @model_validator(mode="after")
    def _digital_output_only(self):
        if self.target.io_type not in ("DO", "RO", "UO", "F"):
            raise ValueError("PULSE only on digital outputs")
        return self


# ---------------- 4. Branching (Ch.7.5 / 7.7) ----------------

class LabelInstr(Strict):
    type: Literal["label"] = "label"                    # LBL[n:comment]
    label: int = Field(ge=1, le=32767)
    comment: Optional[str] = Field(default=None, max_length=16)


class JumpInstr(Strict):
    type: Literal["jump"] = "jump"                      # JMP LBL[n]
    label: int = Field(ge=1, le=32767)


class CallInstr(Strict):
    type: Literal["call"] = "call"                      # CALL PROG(1, R[2], 'S')
    program: str = Field(pattern=r"^[A-Z_][A-Z0-9_]{0,35}$")
    args: list[Union[Constant, RegRef, StrRegRef]] = Field(default_factory=list, max_length=10)


class RunInstr(Strict):
    type: Literal["run"] = "run"                        # RUN PROG (multitask)
    program: str = Field(pattern=r"^[A-Z_][A-Z0-9_]{0,35}$")


IfAction = Union[JumpInstr, CallInstr, IOAssignInstr, "RegisterAssignInstr", IOPulseInstr]


class IfInstr(Strict):
    """IF R[1]>5, JMP LBL[10] ; IF DI[2]=ON, CALL OPEN_GRIP."""
    type: Literal["if"] = "if"
    condition: Condition
    action: IfAction


class IfThenInstr(Strict):
    """IF (R[1]>=3 AND DI[1]=ON) THEN  -- mixed-logic block form."""
    type: Literal["if_then"] = "if_then"
    condition: Condition


class ElseInstr(Strict):
    type: Literal["else"] = "else"


class EndIfInstr(Strict):
    type: Literal["endif"] = "endif"


class SelectCase(Strict):
    match: Union[Constant, RegRef, Literal["ELSE"]]
    action: Union[JumpInstr, CallInstr]


class SelectInstr(Strict):
    """SELECT R[1]=1, CALL A  =2, CALL B  ELSE, JMP LBL[99]."""
    type: Literal["select"] = "select"
    reg: RegRef
    cases: list[SelectCase] = Field(min_length=1, max_length=32)


class ForInstr(Strict):
    """FOR R[1]=1 TO 10 / FOR R[1]=10 DOWNTO 1."""
    type: Literal["for"] = "for"
    counter: RegRef
    start: Union[Constant, RegRef]
    direction: Literal["TO", "DOWNTO"]
    end: Union[Constant, RegRef]


class EndForInstr(Strict):
    type: Literal["endfor"] = "endfor"


# ---------------- 5. Wait / Skip (Ch.7.6, 7.9) ----------------

class WaitTimeInstr(Strict):
    """WAIT 1.50(sec) ; WAIT R[1]."""
    type: Literal["wait_time"] = "wait_time"
    seconds: Union[float, RegRef]

    @model_validator(mode="after")
    def _range(self):
        if isinstance(self.seconds, float) and not (0 < self.seconds <= 327.67):
            raise ValueError("WAIT time out of range")
        return self


class WaitCondInstr(Strict):
    """WAIT DI[3]=ON ; WAIT R[1]>=5 AND DI[2]=ON, TIMEOUT LBL[99]."""
    type: Literal["wait_cond"] = "wait_cond"
    condition: Condition
    timeout_label: Optional[int] = Field(default=None, ge=1, le=32767)


class SkipConditionInstr(Strict):
    """SKIP CONDITION DI[1]=ON -- pairs with Skip,LBL[n] motion option."""
    type: Literal["skip_condition"] = "skip_condition"
    condition: Condition


# ---------------- 6. Frames / offsets (Ch.7.8) ----------------

class UFrameNumInstr(Strict):
    type: Literal["uframe_num"] = "uframe_num"          # UFRAME_NUM=n | R[i]
    value: Union[int, RegRef]

    @model_validator(mode="after")
    def _range(self):
        if isinstance(self.value, int) and not (0 <= self.value <= 9):
            raise ValueError("UFRAME_NUM 0..9")
        return self


class UToolNumInstr(Strict):
    type: Literal["utool_num"] = "utool_num"            # UTOOL_NUM=n | R[i]
    value: Union[int, RegRef]

    @model_validator(mode="after")
    def _range(self):
        if isinstance(self.value, int) and not (1 <= self.value <= 10):
            raise ValueError("UTOOL_NUM 1..10")
        return self


class UFrameAssignInstr(Strict):
    type: Literal["uframe_assign"] = "uframe_assign"    # UFRAME[i]=PR[j]
    frame: int = Field(ge=1, le=9)
    pr: PosRegRef


class UToolAssignInstr(Strict):
    type: Literal["utool_assign"] = "utool_assign"      # UTOOL[i]=PR[j]
    tool: int = Field(ge=1, le=10)
    pr: PosRegRef


class OffsetConditionInstr(Strict):
    """OFFSET CONDITION PR[n] (,UFRAME[m])."""
    type: Literal["offset_condition"] = "offset_condition"
    pr: PosRegRef
    uframe: Optional[int] = Field(default=None, ge=0, le=9)


class ToolOffsetConditionInstr(Strict):
    type: Literal["tool_offset_condition"] = "tool_offset_condition"
    pr: PosRegRef
    utool: Optional[int] = Field(default=None, ge=1, le=10)


class PayloadInstr(Strict):
    type: Literal["payload"] = "payload"                # PAYLOAD[n]
    schedule: int = Field(ge=1, le=10)


# ---------------- 7. Palletizing (Ch.7.15, option) ----------------

class PalletizingInstr(Strict):
    """PALLETIZING-B_i / BX / E / EX header line."""
    type: Literal["palletizing"] = "palletizing"
    variant: Literal["B", "BX", "E", "EX"]
    number: int = Field(ge=1, le=16)


class PalletizingMotionInstr(Strict):
    """J PAL_i[A_1] 100% FINE -- approach/bottom/retract points."""
    type: Literal["palletizing_motion"] = "palletizing_motion"
    motion: Literal["J", "L"]
    number: int = Field(ge=1, le=16)
    point: Literal["A_2", "A_1", "BTM", "R_1", "R_2"]
    speed: Speed
    term: Termination


class PalletizingEndInstr(Strict):
    type: Literal["palletizing_end"] = "palletizing_end"  # PALLETIZING-END_i
    number: int = Field(ge=1, le=16)


# ---------------- 8. Program control / misc (Ch.7.10 - 7.14) ----------------

class AbortInstr(Strict):
    type: Literal["abort"] = "abort"


class PauseInstr(Strict):
    type: Literal["pause"] = "pause"


class OverrideInstr(Strict):
    type: Literal["override"] = "override"              # OVERRIDE=n%
    percent: Union[int, RegRef]

    @model_validator(mode="after")
    def _range(self):
        if isinstance(self.percent, int) and not (1 <= self.percent <= 100):
            raise ValueError("OVERRIDE 1..100%")
        return self


class TimerInstr(Strict):
    type: Literal["timer"] = "timer"                    # TIMER[n]=START/STOP/RESET
    timer: int = Field(ge=1, le=20)
    action: Literal["START", "STOP", "RESET"]


class MessageInstr(Strict):
    type: Literal["message"] = "message"                # MESSAGE[text]
    text: str = Field(max_length=24)


class UserAlarmInstr(Strict):
    type: Literal["user_alarm"] = "user_alarm"          # UALM[n]
    alarm: int = Field(ge=1, le=99)


class RsrInstr(Strict):
    type: Literal["rsr"] = "rsr"                        # RSR[n]=ENABLE/DISABLE
    rsr: int = Field(ge=1, le=8)
    state: Literal["ENABLE", "DISABLE"]


class CollisionDetectInstr(Strict):
    type: Literal["col_detect"] = "col_detect"          # COL DETECT ON/OFF
    state: Literal["ON", "OFF"]


class CollisionGuardAdjustInstr(Strict):
    type: Literal["col_guard_adjust"] = "col_guard_adjust"  # COL GUARD ADJUST n
    value: Union[int, RegRef]


class MonitorInstr(Strict):
    type: Literal["monitor"] = "monitor"                # MONITOR cond_prog
    program: str


class MonitorEndInstr(Strict):
    type: Literal["monitor_end"] = "monitor_end"        # MONITOR END cond_prog
    program: str


class LockPregInstr(Strict):
    type: Literal["lock_preg"] = "lock_preg"


class UnlockPregInstr(Strict):
    type: Literal["unlock_preg"] = "unlock_preg"


class CommentInstr(Strict):
    type: Literal["comment"] = "comment"                # ! text
    text: str = Field(max_length=32)


class RemarkInstr(Strict):
    type: Literal["remark"] = "remark"                  # // text (remark lines)
    text: str = Field(max_length=32)


class EmptyInstr(Strict):
    type: Literal["empty"] = "empty"                    # ;


# =====================================================================
# The union, the program, and the registry
# =====================================================================

Instruction = Annotated[
    Union[
        MotionInstr,
        RegisterAssignInstr, PosRegAssignInstr, PosRegElemAssignInstr,
        StrRegAssignInstr, PalletRegAssignInstr,
        IOAssignInstr, IOPulseInstr,
        LabelInstr, JumpInstr, CallInstr, RunInstr,
        IfInstr, IfThenInstr, ElseInstr, EndIfInstr, SelectInstr,
        ForInstr, EndForInstr,
        WaitTimeInstr, WaitCondInstr, SkipConditionInstr,
        UFrameNumInstr, UToolNumInstr, UFrameAssignInstr, UToolAssignInstr,
        OffsetConditionInstr, ToolOffsetConditionInstr, PayloadInstr,
        PalletizingInstr, PalletizingMotionInstr, PalletizingEndInstr,
        AbortInstr, PauseInstr, OverrideInstr, TimerInstr, MessageInstr,
        UserAlarmInstr, RsrInstr, CollisionDetectInstr, CollisionGuardAdjustInstr,
        MonitorInstr, MonitorEndInstr, LockPregInstr, UnlockPregInstr,
        CommentInstr, RemarkInstr, EmptyInstr,
    ],
    Field(discriminator="type"),
]


class Line(Strict):
    """One numbered /MN line."""
    instr: Instruction


class PositionRep(Strict):
    """A /POS entry for P[i]: Cartesian (config + xyzwpr) or Joint."""
    index: int = Field(ge=1, le=9999)
    rep: Literal["C", "J"]
    group: int = Field(default=1, ge=1, le=5)
    config: Optional[str] = None                 # e.g. "N U T, 0, 0, 0" (C only)
    values: list[float] = Field(min_length=6, max_length=9)
    uframe: int = Field(default=1, ge=0, le=9)
    utool: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def _cfg(self):
        if self.rep == "C" and not self.config:
            raise ValueError("Cartesian position requires a config string")
        return self


class ProgramAttr(Strict):
    owner: str = "MNEDITOR"
    comment: str = Field(default="", max_length=32)
    prog_size: Optional[int] = None
    group_mask: str = "1,*,*,*,*"


class Program(Strict):
    """The full .ls file: /PROG name, /ATTR, /MN lines, /POS entries."""
    name: str = Field(pattern=r"^[A-Z_][A-Z0-9_]{0,35}$")
    attr: ProgramAttr = Field(default_factory=ProgramAttr)
    lines: list[Line] = Field(min_length=1)
    positions: list[PositionRep] = Field(default_factory=list)

    @model_validator(mode="after")
    def _refs_resolve(self):
        declared = {p.index for p in self.positions}
        used_p = {ln.instr.target.index for ln in self.lines
                  if getattr(ln.instr, "type", "") == "motion"
                  and ln.instr.target.kind == "P"}
        missing = used_p - declared
        if missing:
            raise ValueError(f"P positions used but not declared in /POS: {sorted(missing)}")
        labels = {ln.instr.label for ln in self.lines if ln.instr.type == "label"}
        jumps = {ln.instr.label for ln in self.lines if ln.instr.type == "jump"}
        jumps |= {ln.instr.action.label for ln in self.lines
                  if ln.instr.type == "if" and isinstance(ln.instr.action, JumpInstr)}
        jumps |= {ln.instr.timeout_label for ln in self.lines
                  if ln.instr.type == "wait_cond" and ln.instr.timeout_label}
        dangling = jumps - labels
        if dangling:
            raise ValueError(f"JMP/TIMEOUT to undeclared labels: {sorted(dangling)}")
        return self


def instruction_registry() -> dict[str, type]:
    """type-discriminator -> model class, for card generation and the
    validator's family taxonomy."""
    import typing
    union = typing.get_args(typing.get_args(Instruction)[0])
    return {m.model_fields["type"].default: m for m in union}


OptTimeAfter.model_rebuild()
OptTimeBefore.model_rebuild()
