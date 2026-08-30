"""contract.py -- Request/Response contract per Design Document Section 2 (v1.2).

The console (caller) and the unit speak ONLY these types. No other imports cross
the boundary in either direction.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional
import json

Status = Literal["ok", "needs_clarification", "rejected", "failed"]

# defaults keys the caller may override; anything else in config_overrides -> level-A reject
OVERRIDABLE_DEFAULTS = {"speed", "pick_speed", "term", "utool", "uframe", "gripper_settle_sec"}
LIMIT_KEYS = {"max_speed_mmsec", "max_wait_sec"}


@dataclass
class Request:
    prompt: str
    cell_id: str
    scan: Optional[str] = None          # reg_io_v1 CSV, verbatim (Section 2c when absent)
    config_overrides: dict = field(default_factory=dict)   # DEFAULTS ONLY, never limits
    rag_backend: str = "online"          # "online" | "local"
    example_ls: Optional[str] = None
    revision_of: Optional[str] = None    # previous draft_id
    answers: dict = field(default_factory=dict)  # {"reply": "<raw text>"} or {key: value}

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @staticmethod
    def from_json(s: str) -> "Request":
        return Request(**json.loads(s))


@dataclass
class Report:
    scan_used: Optional[str] = None          # timestamp of the mapping used
    table_source: Optional[str] = None       # "scan" | "cache(<age>)" | "none"
    mapping_confidence: Optional[str] = None  # "verified" | "unverified"
    effective_defaults: dict = field(default_factory=dict)
    positions: dict = field(default_factory=dict)   # "PR[5]": "note 'conveyor pick'"
    inferred: list = field(default_factory=list)    # [{"text":..., "decision":...}]
    retries: int = 0
    advisories: list = field(default_factory=list)  # friendly language, never blocking


@dataclass
class Response:
    status: Status
    draft_id: Optional[str] = None
    program_ls: Optional[str] = None
    file_ref: Optional[str] = None
    report: Optional[Report] = None
    questions: list = field(default_factory=list)   # plain, friendly, self-contained
    reason: Optional[str] = None                    # rejected/failed: friendly one-liner

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, indent=2)

    @staticmethod
    def from_json(s: str) -> "Response":
        d = json.loads(s)
        if d.get("report"):
            d["report"] = Report(**d["report"])
        return Response(**d)


def validate_request(req: Request) -> Optional[str]:
    """Level-A contract validation (Runtime, mechanical -- Design Doc Section 2b).

    Predefined parameters only. No reasoning. Returns a pre-written friendly
    rejection message, or None when the request passes to LLM #1's intake.
    """
    if not req.prompt or not req.prompt.strip():
        return "I received an empty request. Please describe the TP program you need."
    if not req.cell_id:
        return ("I'm missing the cell identifier, so I can't tell which robot cell "
                "this program is for. Please include a cell_id.")
    bad = set(req.config_overrides) & LIMIT_KEYS
    if bad:
        return (f"The settings {sorted(bad)} are safety limits and can't be changed "
                f"per request. You can override defaults like speed or termination, "
                f"but limits are fixed in this unit's configuration.")
    unknown = set(req.config_overrides) - OVERRIDABLE_DEFAULTS - LIMIT_KEYS
    if unknown:
        return (f"I don't recognize these settings: {sorted(unknown)}. "
                f"The defaults you can override are: {sorted(OVERRIDABLE_DEFAULTS)}.")
    if req.rag_backend not in ("online", "local"):
        return ("I don't recognize that documentation profile. Please set "
                "rag_backend to 'online' or 'local'.")
    return None
