"""app_state.py -- the GUI's brain, kept tkinter-free so it is testable headless.

Owns: config load/save, conversation state (last_draft, pending), and the
mechanical Request assembly. The window layer (gui.py) only forwards events.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import copy

import yaml

from contract import Request, Response, OVERRIDABLE_DEFAULTS

APP_CONFIG = Path(__file__).parent / "app_config.yaml"
RAG_CONFIG = Path(__file__).parent / "rag_config.yaml"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")


@dataclass
class AppState:
    cfg: dict = field(default_factory=dict)          # app_config.yaml contents
    baseline_defaults: dict = field(default_factory=dict)
    overrides: dict = field(default_factory=dict)    # only user-CHANGED values
    scan_csv: str | None = None
    scan_sent: bool = False
    example_ls: str | None = None
    last_draft: str | None = None
    last_program: str | None = None
    last_report = None
    pending_questions: list = field(default_factory=list)

    # ---------- config ----------
    @classmethod
    def load(cls, path: Path = APP_CONFIG) -> "AppState":
        cfg = load_yaml(path)
        st = cls(cfg=cfg,
                 baseline_defaults=copy.deepcopy(cfg.get("overridable_defaults", {})))
        sp = cfg.get("scan_path")
        if sp and Path(sp).exists():
            st.scan_csv = Path(sp).read_text(encoding="utf-8")
        return st

    def save_app_config(self, path: Path = APP_CONFIG) -> None:
        save_yaml(path, self.cfg)

    # ---------- settings edits (from the GUI Settings tab) ----------
    def set_default(self, key: str, value) -> None:
        if key not in OVERRIDABLE_DEFAULTS:
            raise ValueError(f"'{key}' is not an overridable default")
        if str(value) == str(self.baseline_defaults.get(key)):
            self.overrides.pop(key, None)            # back to baseline -> not sent
        else:
            self.overrides[key] = value

    def set_cell(self, cell_id: str) -> None:
        self.cfg["cell_id"] = cell_id.strip()

    def set_backend(self, backend: str) -> None:
        self.cfg["rag_backend"] = backend

    def load_scan(self, path: str | Path) -> str:
        self.scan_csv = Path(path).read_text(encoding="utf-8")
        self.scan_sent = False
        self.cfg["scan_path"] = str(path)
        first = self.scan_csv.splitlines()[:3]
        return " | ".join(l.lstrip("# ").strip() for l in first)

    def attach_example(self, path: str | Path | None) -> None:
        self.example_ls = Path(path).read_text(encoding="utf-8") if path else None

    def new_program(self) -> None:
        self.last_draft = self.last_program = None
        self.pending_questions = []

    # ---------- the envelope: mechanical, prompt untouched ----------
    def build_request(self, user_text: str) -> Request:
        req = Request(
            prompt=user_text,
            cell_id=self.cfg.get("cell_id", ""),
            scan=None if self.scan_sent else self.scan_csv,
            config_overrides=dict(self.overrides),
            rag_backend=self.cfg.get("rag_backend", "online"),
            example_ls=self.example_ls,
            revision_of=self.last_draft,
            answers={"reply": user_text} if self.pending_questions else {},
        )
        return req

    def apply_response(self, req: Request, resp: Response) -> None:
        if req.scan is not None:
            self.scan_sent = True                     # relayed once; unit persists
        self.example_ls = None                        # attach applies to one request
        if resp.status == "needs_clarification":
            self.pending_questions = list(resp.questions)
        else:
            self.pending_questions = []
        if resp.status == "ok":
            self.last_draft = resp.draft_id
            self.last_program = resp.program_ls
            self.last_report = resp.report


# ---------- RAG config (unit-side file; GUI edits as a dev convenience) ----------
RAG_EDITABLE = {                       # path-in-yaml -> (label, cast)
    ("retrieve", "top_k"): ("Top-K closest chunks", int),
    ("retrieve", "score_threshold"): ("Similarity score threshold", float),
    ("retrieve", "max_context_chars"): ("Max context characters", int),
    ("index", "chunk_strategy"): ("Chunk strategy (logical|fixed)", str),
    ("index", "chunk_size_chars"): ("Chunk size (chars, fixed mode)", int),
    ("index", "chunk_overlap_chars"): ("Chunk overlap (chars, fixed mode)", int),
}


def load_rag_config(path: Path = RAG_CONFIG) -> dict:
    return load_yaml(path)


def set_rag_value(cfg: dict, keypath: tuple, raw: str) -> None:
    label, cast = RAG_EDITABLE[keypath]
    node = cfg
    for k in keypath[:-1]:
        node = node[k]
    node[keypath[-1]] = cast(raw)


def save_rag_config(cfg: dict, path: Path = RAG_CONFIG) -> None:
    save_yaml(path, cfg)
