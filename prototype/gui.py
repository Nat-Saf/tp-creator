"""gui.py -- TP Creator console GUI v0 (OUTSIDE the unit; speaks contract only).

Tabs: Chat | Program | Report | Settings.
Run:  python gui.py          (requires: pip install pyyaml; tkinter ships with Python)

All Request fields are auto-filled from app_config.yaml + conversation state;
the user only ever types the prompt (and answers questions in the same box).
"""
from __future__ import annotations
import difflib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from app_state import (AppState, RAG_EDITABLE, load_rag_config,
                       set_rag_value, save_rag_config)
from contract import Response
import mock_unit


def post_to_unit(state: AppState, req) -> Response:
    if state.cfg.get("unit", {}).get("transport") == "http":
        import urllib.request, json
        url = state.cfg["unit"]["base_url"].rstrip("/") + "/request"
        data = req.to_json().encode()
        with urllib.request.urlopen(urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"})) as r:
            return Response.from_json(r.read().decode())
    return mock_unit.handle(req)          # v0: in-process mock


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TP Creator - console v0 (outside the unit)")
        self.geometry("920x640")
        self.state_ = AppState.load()

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.chat_tab = ttk.Frame(nb); nb.add(self.chat_tab, text="Chat")
        self.prog_tab = ttk.Frame(nb); nb.add(self.prog_tab, text="Program")
        self.rep_tab = ttk.Frame(nb); nb.add(self.rep_tab, text="Report")
        self.set_tab = ttk.Frame(nb); nb.add(self.set_tab, text="Settings")
        self._build_chat(); self._build_program(); self._build_report(); self._build_settings()
        self._say("system", f"cell {self.state_.cfg.get('cell_id')} - "
                  f"map {'loaded' if self.state_.scan_csv else 'NOT loaded'} - "
                  f"backend {self.state_.cfg.get('rag_backend')}")

    # ---------------- Chat ----------------
    def _build_chat(self):
        bar = ttk.Frame(self.chat_tab); bar.pack(fill="x", padx=6, pady=4)
        ttk.Button(bar, text="New program", command=self._new).pack(side="left")
        ttk.Button(bar, text="Load reg/IO map...", command=self._load_scan).pack(side="left", padx=4)
        ttk.Button(bar, text="Attach example .ls...", command=self._attach).pack(side="left")
        self.status = ttk.Label(bar, text=""); self.status.pack(side="right")

        self.transcript = scrolledtext.ScrolledText(self.chat_tab, wrap="word",
                                                    state="disabled", height=24)
        self.transcript.pack(fill="both", expand=True, padx=6, pady=4)
        for tag, col in (("user", "#26215C"), ("unit", "#04342C"),
                         ("system", "#5F5E5A"), ("err", "#A32D2D")):
            self.transcript.tag_config(tag, foreground=col)

        entry_row = ttk.Frame(self.chat_tab); entry_row.pack(fill="x", padx=6, pady=6)
        self.entry = ttk.Entry(entry_row); self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self._send())
        ttk.Button(entry_row, text="Send", command=self._send).pack(side="left", padx=4)

    def _say(self, tag, text):
        self.transcript.config(state="normal")
        prefix = {"user": "you:  ", "unit": "unit: ", "system": "--    ", "err": "!!    "}[tag]
        self.transcript.insert("end", prefix + text + "\n\n", tag)
        self.transcript.config(state="disabled"); self.transcript.see("end")

    def _send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._say("user", text)
        st = self.state_
        req = st.build_request(text)
        try:
            resp = post_to_unit(st, req)
        except Exception as e:
            self._say("err", f"transport error: {e}"); return
        prev = st.last_program
        st.apply_response(req, resp)

        if resp.status == "needs_clarification":
            for q in resp.questions: self._say("unit", q)
        elif resp.status == "ok":
            self._say("unit", f"Done - draft {resp.draft_id}  ({resp.file_ref})")
            if prev:
                diff = [d for d in difflib.unified_diff(
                    prev.splitlines(), resp.program_ls.splitlines(), lineterm="", n=0)
                    if d.startswith(("+", "-")) and not d.startswith(("+++", "---"))]
                if diff: self._say("unit", "changes:\n" + "\n".join(diff))
            for a in (resp.report.advisories if resp.report else []):
                self._say("unit", "advisory: " + a)
            self._render_program(resp.program_ls); self._render_report(resp.report)
        else:
            self._say("err", f"({resp.status}) {resp.reason}")
        self.status.config(text=f"draft: {st.last_draft or '-'}   "
                                f"pending question: {'yes' if st.pending_questions else 'no'}")

    def _new(self):
        self.state_.new_program(); self._say("system", "new program - previous draft forgotten")

    def _load_scan(self):
        p = filedialog.askopenfilename(filetypes=[("reg_io_v1 CSV", "*.csv")])
        if p:
            try:
                meta = self.state_.load_scan(p)
                self._say("system", f"map loaded: {meta}")
            except Exception as e:
                messagebox.showerror("Map load failed", str(e))

    def _attach(self):
        p = filedialog.askopenfilename(filetypes=[("TP program", "*.ls")])
        if p:
            self.state_.attach_example(p)
            self._say("system", f"example attached for the next request: {p}")

    # ---------------- Program / Report ----------------
    def _build_program(self):
        self.prog_text = scrolledtext.ScrolledText(self.prog_tab, wrap="none",
                                                   font=("Consolas", 10))
        self.prog_text.pack(fill="both", expand=True, padx=6, pady=6)

    def _render_program(self, text):
        self.prog_text.delete("1.0", "end"); self.prog_text.insert("1.0", text or "")

    def _build_report(self):
        self.rep_text = scrolledtext.ScrolledText(self.rep_tab, wrap="word")
        self.rep_text.pack(fill="both", expand=True, padx=6, pady=6)

    def _render_report(self, r):
        self.rep_text.delete("1.0", "end")
        if not r: return
        lines = [f"scan used:    {r.scan_used}   (source: {r.table_source}, {r.mapping_confidence})",
                 "defaults:     " + ", ".join(f"{k}={v}" for k, v in r.effective_defaults.items()),
                 "positions:"] + [f"   {k}  {v}" for k, v in r.positions.items()] + \
                [f"retries:      {r.retries}"] + \
                [f"inferred:     '{i['text']}' -> {i['decision']}" for i in r.inferred] + \
                [f"advisory:     {a}" for a in r.advisories]
        self.rep_text.insert("1.0", "\n".join(lines))

    # ---------------- Settings ----------------
    def _build_settings(self):
        st = self.state_
        f = ttk.LabelFrame(self.set_tab, text="Caller (app_config.yaml)")
        f.pack(fill="x", padx=8, pady=6)
        self.cell_var = tk.StringVar(value=st.cfg.get("cell_id", ""))
        self.backend_var = tk.StringVar(value=st.cfg.get("rag_backend", "online"))
        ttk.Label(f, text="cell_id").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(f, textvariable=self.cell_var, width=24).grid(row=0, column=1, sticky="w")
        ttk.Label(f, text="rag_backend").grid(row=1, column=0, sticky="w", padx=4)
        ttk.Combobox(f, textvariable=self.backend_var, values=["online", "local"],
                     width=10, state="readonly").grid(row=1, column=1, sticky="w")

        d = ttk.LabelFrame(self.set_tab,
                           text="Defaults (sent as config_overrides only when changed; limits are not overridable)")
        d.pack(fill="x", padx=8, pady=6)
        self.def_vars = {}
        for i, (k, v) in enumerate(st.baseline_defaults.items()):
            ttk.Label(d, text=k).grid(row=i, column=0, sticky="w", padx=4, pady=1)
            var = tk.StringVar(value=str(v)); self.def_vars[k] = var
            ttk.Entry(d, textvariable=var, width=16).grid(row=i, column=1, sticky="w")

        g = ttk.LabelFrame(self.set_tab, text="RAG (rag_config.yaml - unit-side file, edited here as a dev convenience)")
        g.pack(fill="x", padx=8, pady=6)
        self.rag_cfg = load_rag_config(); self.rag_vars = {}
        for i, (keypath, (label, _cast)) in enumerate(RAG_EDITABLE.items()):
            node = self.rag_cfg
            for k in keypath[:-1]: node = node[k]
            ttk.Label(g, text=label).grid(row=i, column=0, sticky="w", padx=4, pady=1)
            var = tk.StringVar(value=str(node[keypath[-1]])); self.rag_vars[keypath] = var
            ttk.Entry(g, textvariable=var, width=16).grid(row=i, column=1, sticky="w")
        ttk.Label(g, foreground="#854F0B",
                  text="Changing embedding/index values requires re-running the indexer for that profile."
                  ).grid(row=len(RAG_EDITABLE), column=0, columnspan=2, sticky="w", padx=4, pady=4)

        ttk.Button(self.set_tab, text="Apply + Save", command=self._save_settings)\
            .pack(anchor="e", padx=10, pady=8)

    def _save_settings(self):
        st = self.state_
        st.set_cell(self.cell_var.get()); st.set_backend(self.backend_var.get())
        try:
            for k, var in self.def_vars.items():
                val = var.get()
                st.set_default(k, int(val) if val.isdigit() else
                               (float(val) if _isfloat(val) else val))
            for keypath, var in self.rag_vars.items():
                set_rag_value(self.rag_cfg, keypath, var.get())
        except ValueError as e:
            messagebox.showerror("Invalid value", str(e)); return
        st.save_app_config(); save_rag_config(self.rag_cfg)
        self._say("system", f"settings saved - overrides now sent: {st.overrides or '{}'}")


def _isfloat(s):
    try: float(s); return True
    except ValueError: return False


if __name__ == "__main__":
    App().mainloop()
