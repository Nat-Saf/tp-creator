"""Architecture diagram generator (course Phase 7, agent view).

Draws docs/architecture.png - the AGENT architecture in the Design
Document's Figure-1 language (block diagram + numbered 1-10 flow),
labelled with EXACTLY the registry module names - and writes
docs/architecture.json, the manifest carrying the same registry boxes
plus the intro and the numbered flow that GET /api/agent_info serves.
Diagram, manifest and endpoint text all come from this one module plus
tpagent.modules, so they cannot disagree (the consistency test pins it).

    python -m tpagent.architecture      # regenerate both files

Dev-only tool (Pillow); the API just serves the committed PNG/JSON.
"""
from __future__ import annotations

import json
import math

from PIL import Image, ImageDraw, ImageFont

from tpagent import modules
from tpagent.config import ROOT

PNG = ROOT / "docs" / "architecture.png"
MANIFEST = ROOT / "docs" / "architecture.json"

W, H = 1360, 1700
BG = (247, 248, 250)
BOX = (255, 255, 255)
EDGE = (55, 65, 81)
HUB = (16, 20, 24)
HUB_TEXT = (255, 255, 255)
ACCENT = (47, 111, 235)
TEXT = (28, 33, 40)
SUB = (106, 115, 125)
PURPLE = (229, 224, 248)
TEAL = (222, 242, 234)
CORAL = (250, 233, 226)
AMBER = (250, 238, 216)
GREEN = (232, 242, 219)
BLUE = (226, 239, 251)


def _font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


F_TITLE = _font(30, bold=True)
F_BOX = _font(22, bold=True)
F_SMALL = _font(16)
F_STEP = _font(15, bold=True)

# ---------------------------------------------------------------- the story
# GET /api/agent_info serves these verbatim (via the JSON manifest); the
# badge numbers drawn below match FLOW's step numbers one to one.

INTRO = [
    "TP Creator turns one plain sentence into a validated FANUC TP (.LS) "
    "program. The design splits the work between two narrow AI roles and "
    "one deterministic machine, so everything creative is reviewable and "
    "everything mechanical is guaranteed.",

    "LLM #1 (the LLM1-Intake and LLM1-Audit roles) exists because human "
    "words are ambiguous - it is the only component allowed to interpret "
    "them. It maps 'the conveyor' to the cell's real registers through "
    "their pendant notes, decides per gap whether to use a default, infer "
    "with a note, or ask the user, diagnoses validation failures, and "
    "reviews the finished program. It decides strategy - never mechanics.",

    "The Runtime is deterministic and owns the mechanics precisely because "
    "models cannot be trusted with them: the retry budget, the "
    "unconditional edges (every draft goes to the Validator, every passing "
    "program to LLM1-Audit), mandatory documentation retrieval, and the "
    "stop rules. LLM2-Codegen writes the actual TP code in a fresh context "
    "from a deterministically rendered prompt, so nothing can slip past "
    "the Validator - the machine, not a model, decides when a program is "
    "good enough to deliver.",
]

FLOW = [
    {"step": 1, "title": "Request in", "modules": [modules.RUNTIME],
     "text": "The browser GUI sends the whole conversation transcript as "
             "the prompt (plus the optional registers/IO table CSV). The "
             "adapter builds the contract Request and the Runtime performs "
             "the mechanical level-A checks before any model is involved."},
    {"step": 2, "title": "Table materialized",
     "modules": [modules.RUNTIME, modules.STORES],
     "text": "The Stores layer resolves the cell's table: an uploaded CSV "
             "wins (bare files get the reg_io_v1 metadata synthesized), "
             "else the bundled default table, else the robot is treated as "
             "empty and any index is usable. A session row opens in "
             "Supabase."},
    {"step": 3, "title": "Intake", "modules": [modules.LLM1_INTAKE],
     "text": "LLM1-Intake is the only place human words are interpreted: "
             "it maps them to real registers and IO through the pendant "
             "notes and applies the gap policy - use a default, infer with "
             "a note, or ask. An ambiguous or missing pick/place position "
             "always comes back as a question."},
    {"step": 4, "title": "Retrieval",
     "modules": [modules.RUNTIME, modules.RAG_RETRIEVE, modules.RAG_EMBED],
     "text": "The Runtime always calls RAG-Retrieve for TP-syntax "
             "documentation before the first draft; LLM1-Intake may add up "
             "to two targeted queries. RAG-Embed built the Pinecone index "
             "offline from our own-words notes. Chunks go to the Renderer "
             "only - never through LLM1-Intake's context."},
    {"step": 5, "title": "Params out", "modules": [modules.LLM1_INTAKE],
     "text": "LLM1-Intake invokes the generate_program tool: parameters, "
             "program name and notes, plus fix guidance on retries. The "
             "task and notes are pinned to the first attempt, so a retry "
             "differs only in what is being fixed."},
    {"step": 6, "title": "Prompt and draft",
     "modules": [modules.RENDERER, modules.LLM2_CODEGEN],
     "text": "The Renderer deterministically assembles the LLM2-Codegen "
             "prompt from fixed sections (canonical program skeleton, "
             "cell, docs, task, notes, previous draft + fix on retries). "
             "It takes the table and config from the stores, never from "
             "LLM1-Intake's output - the tool call has no field that could "
             "carry them (no-leakage). LLM2-Codegen writes the TP draft in "
             "a fresh context."},
    {"step": 7, "title": "Validation", "modules": [modules.VALIDATOR],
     "text": "Every draft goes through the deterministic three-layer "
             "Validator: grammar token walks, existence against the table "
             "(skipped for an empty robot; an existing-but-untaught "
             "register is a warning, not an error), and safety limits with "
             "every speed unit converted or refused."},
    {"step": 8, "title": "Errors back",
     "modules": [modules.RUNTIME, modules.LLM1_INTAKE],
     "text": "A failing verdict returns to LLM1-Intake for diagnosis and a "
             "bounded retry: the Runtime allows at most three drafts and "
             "stops mechanically on a third consecutive failure of the "
             "same layer and offender."},
    {"step": 9, "title": "Audit - always", "modules": [modules.LLM1_AUDIT],
     "text": "Every passing program is reviewed by LLM1-Audit for mapping "
             "and intent correctness, with the effective defaults in hand. "
             "Advisory only - findings never block delivery."},
    {"step": 10, "title": "Store and respond",
     "modules": [modules.RUNTIME, modules.STORES],
     "text": "Outputs and the full report persist via Stores (Supabase); "
             "the adapter maps the result to the exact course shape "
             "{status, error, response, steps}. The steps recorder wraps "
             "the model client, so every chat and embedding call appears "
             "in steps, in order."},
]

# ---------------------------------------------------------------- drawing


def _box(d: ImageDraw.ImageDraw, cx, cy, w, h, name, subtitle,
         fill=BOX, text=TEXT):
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    d.rounded_rectangle((x0, y0, x1, y1), radius=12, fill=fill,
                        outline=EDGE, width=2)
    tw = d.textlength(name, font=F_BOX)
    d.text((cx - tw / 2, cy - (22 if subtitle else 12)), name,
           font=F_BOX, fill=text)
    if subtitle:
        sw = d.textlength(subtitle, font=F_SMALL)
        d.text((cx - sw / 2, cy + 6), subtitle, font=F_SMALL,
               fill=SUB if fill == BOX else (170, 180, 190))
    return (cx, cy, w, h)


def _arrow(d, a, b, label=None, color=EDGE, dashed=False):
    (ax, ay, aw, ah), (bx, by, bw, bh) = a, b
    dx, dy = bx - ax, by - ay
    dist = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / dist, dy / dist
    # trim the line at each box's border (approximate by half-extents)
    def trim(cx, cy, w, h, sx, sy):
        tx = (w / 2 + 8) / abs(sx) if sx else 1e9
        ty = (h / 2 + 8) / abs(sy) if sy else 1e9
        t = min(tx, ty)
        return cx + sx * t, cy + sy * t
    x0, y0 = trim(ax, ay, aw, ah, ux, uy)
    x1, y1 = trim(bx, by, bw, bh, -ux, -uy)
    if dashed:
        steps = int(dist // 14)
        for i in range(0, steps, 2):
            t0, t1 = i / steps, min((i + 1) / steps, 1)
            d.line((x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0,
                    x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1),
                   fill=color, width=3)
    else:
        d.line((x0, y0, x1, y1), fill=color, width=3)
    # arrow head
    hx, hy = x1 - ux * 14, y1 - uy * 14
    px, py = -uy, ux
    d.polygon((x1, y1, hx + px * 7, hy + py * 7, hx - px * 7, hy - py * 7),
              fill=color)
    if label:
        lw = d.textlength(label, font=F_STEP)
        lx = (x0 + x1) / 2 - lw / 2
        ly = (y0 + y1) / 2 - 22
        d.rounded_rectangle((lx - 6, ly - 3, lx + lw + 6, ly + 20),
                            radius=8, fill=(232, 238, 250))
        d.text((lx, ly), label, font=F_STEP, fill=ACCENT)


def _pt(x, y):
    return (x, y, 0, 0)


def _dashed_rect(d, x0, y0, x1, y1, dash=12, gap=8):
    def dline(a, b):
        dist = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(int(dist // (dash + gap)), 1)
        ux, uy = (b[0] - a[0]) / dist, (b[1] - a[1]) / dist
        for i in range(n + 1):
            s = i * (dash + gap)
            e = min(s + dash, dist)
            if s >= dist:
                break
            d.line((a[0] + ux * s, a[1] + uy * s,
                    a[0] + ux * e, a[1] + uy * e), fill=SUB, width=2)
    dline((x0, y0), (x1, y0))
    dline((x1, y0), (x1, y1))
    dline((x1, y1), (x0, y1))
    dline((x0, y1), (x0, y0))


def _badge(d, cx, cy, n):
    r = 17
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLUE, outline=ACCENT,
              width=2)
    t = str(n)
    w = d.textlength(t, font=F_STEP)
    d.text((cx - w / 2, cy - 9), t, font=F_STEP, fill=ACCENT)


def generate() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((60, 28), "TP Creator - agent architecture",
           font=F_TITLE, fill=TEXT)
    d.text((60, 68), "badges 1-10 = the flow in GET /api/agent_info",
           font=F_SMALL, fill=SUB)

    # outside the unit: the caller and the external services
    ext = _box(d, 276, 152, 360, 92, "LLMod + Pinecone",
               "models + vector index", fill=TEAL)
    embed = _box(d, 320, 290, 220, 80, modules.RAG_EMBED,
                 "offline indexing", fill=TEAL)
    _arrow(d, embed, ext, dashed=True)
    user = _box(d, 680, 118, 320, 88, "User", "prompt / answers", fill=BLUE)
    gui = _box(d, 680, 250, 460, 92, "Web GUI + adapter",
               "transcript, table upload", fill=BOX)
    _arrow(d, user, gui)

    _dashed_rect(d, 80, 360, 1280, 1650)
    d.text((104, 380), "TP creator unit", font=F_BOX, fill=TEXT)

    runtime = _box(d, 700, 480, 400, 96, modules.RUNTIME,
                   "no AI - checks, budgets, edges", fill=HUB, text=HUB_TEXT)
    _arrow(d, gui, runtime)
    _badge(d, 636, 386, 1)

    # respond / clarify loop back to the caller
    d.line((880, 448, 1130, 448), fill=EDGE, width=3)
    d.line((1130, 448, 1130, 250), fill=EDGE, width=3)
    _arrow(d, _pt(1130, 250), _pt(916, 250))
    _badge(d, 1164, 330, 10)

    _dashed_rect(d, 936, 430, 1250, 726)
    d.text((952, 700), "runtime-owned", font=F_SMALL, fill=SUB)
    _box(d, 1092, 516, 276, 92, "Reg/IO table", "upload or bundled default",
         fill=TEAL)
    _box(d, 1092, 646, 276, 92, modules.STORES, "Supabase sessions/outputs",
         fill=CORAL)
    _arrow(d, runtime, _pt(954, 516))
    _badge(d, 944, 486, 2)

    llm1 = _box(d, 700, 660, 400, 96, modules.LLM1_INTAKE,
                "words -> params / ask / reject", fill=PURPLE)
    _arrow(d, _pt(660, 520), _pt(660, 620))     # runtime -> intake
    _arrow(d, _pt(740, 620), _pt(740, 520))     # intake -> runtime
    _badge(d, 620, 574, 3)

    rag = _box(d, 270, 660, 300, 92, modules.RAG_RETRIEVE,
               "auto + on-demand chunks", fill=TEAL)
    d.line((500, 500, 270, 500), fill=EDGE, width=3)
    _arrow(d, _pt(270, 500), _pt(270, 610))
    _badge(d, 310, 552, 4)
    _arrow(d, _pt(150, 622), _pt(150, 202))    # RAG-Retrieve -> the index
    _arrow(d, llm1, rag, dashed=True)

    cfg = _box(d, 270, 800, 300, 88, "Static config", "defaults + limits",
               fill=BOX)
    _arrow(d, cfg, llm1, dashed=True)

    _dashed_rect(d, 300, 880, 1070, 1120)
    d.text((320, 1084), "generate_program tool", font=F_SMALL, fill=SUB)
    ren = _box(d, 510, 980, 330, 100, modules.RENDERER,
               "deterministic fixed sections", fill=BOX)
    llm2 = _box(d, 890, 980, 280, 100, modules.LLM2_CODEGEN,
                "fresh context -> TP draft", fill=PURPLE)
    _arrow(d, llm1, _pt(700, 884))
    _badge(d, 650, 820, 5)
    _arrow(d, ren, llm2)
    _badge(d, 712, 944, 6)

    val = _box(d, 700, 1230, 460, 100, modules.VALIDATOR,
               "no AI - grammar, existence, limits", fill=AMBER)
    _arrow(d, _pt(700, 1120), val)
    _badge(d, 660, 1160, 7)

    # errors, retry -> back to LLM1-Intake
    d.line((930, 1230, 1240, 1230), fill=EDGE, width=3)
    d.line((1240, 1230, 1240, 760), fill=EDGE, width=3)
    d.line((1240, 760, 848, 760), fill=EDGE, width=3)
    _arrow(d, _pt(848, 760), _pt(848, 712))
    _badge(d, 1206, 980, 8)

    aud = _box(d, 700, 1400, 460, 100, modules.LLM1_AUDIT,
               "advisory - sees the defaults", fill=PURPLE)
    _arrow(d, val, aud)
    _badge(d, 660, 1330, 9)

    _box(d, 274, 1400, 320, 100, "Steps recorder",
         "every model call, in order", fill=CORAL)

    out = _box(d, 700, 1570, 500, 100, "Validated .ls + report",
               "exact course shape out", fill=GREEN)
    _arrow(d, aud, out)

    PNG.parent.mkdir(exist_ok=True)
    img.save(PNG)
    MANIFEST.write_text(json.dumps(
        {"boxes": list(modules.REGISTRY), "intro": INTRO, "flow": FLOW},
        indent=2), encoding="utf-8")
    print(f"wrote {PNG.name} + {MANIFEST.name} "
          f"({len(modules.REGISTRY)} registry boxes, {len(FLOW)} flow steps)")


if __name__ == "__main__":
    generate()
