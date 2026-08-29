"""Architecture diagram generator (course Phase 7).

Draws docs/architecture.png - the Design Doc Figure-1 hub topology with
EXACTLY the registry module names - and writes docs/architecture.json,
a manifest listing the drawn boxes. Both come from tpagent.modules
REGISTRY, so the diagram, the steps traces and the descriptions cannot
disagree (the consistency test pins it).

    python -m tpagent.architecture      # regenerate both files

Dev-only tool (Pillow); the API just serves the committed PNG.
"""
from __future__ import annotations

import json

from PIL import Image, ImageDraw, ImageFont

from tpagent import modules
from tpagent.config import ROOT

PNG = ROOT / "docs" / "architecture.png"
MANIFEST = ROOT / "docs" / "architecture.json"

W, H = 1480, 900
BG = (247, 248, 250)
BOX = (255, 255, 255)
EDGE = (55, 65, 81)
HUB = (16, 20, 24)
HUB_TEXT = (255, 255, 255)
ACCENT = (47, 111, 235)
TEXT = (28, 33, 40)
SUB = (106, 115, 125)


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
    x1, y1 = 2 * x1 - bx + (bx - x1) * 2, 2 * y1 - by + (by - y1) * 2
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


def generate() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((40, 28), "TP Creator - module architecture",
           font=F_TITLE, fill=TEXT)
    d.text((40, 68), "hub topology: the Runtime calls every module; "
                     "numbers show one /api/execute flow",
           font=F_SMALL, fill=SUB)

    runtime = _box(d, 740, 450, 240, 96, modules.RUNTIME,
                   "session loop - budgets", fill=HUB, text=HUB_TEXT)

    intake = _box(d, 320, 210, 250, 84, modules.LLM1_INTAKE,
                  "task -> params / questions")
    audit = _box(d, 1160, 210, 250, 84, modules.LLM1_AUDIT,
                 "semantic advisories")
    retrieve = _box(d, 250, 450, 250, 84, modules.RAG_RETRIEVE,
                    "query -> doc chunks")
    renderer = _box(d, 530, 720, 250, 84, modules.RENDERER,
                    "deterministic prompt")
    codegen = _box(d, 850, 780, 250, 84, modules.LLM2_CODEGEN,
                   "prompt -> TP draft")
    validator = _box(d, 1210, 640, 250, 84, modules.VALIDATOR,
                     "grammar/existence/limits")
    stores = _box(d, 1230, 430, 240, 84, modules.STORES,
                  "Supabase persistence")
    embed = _box(d, 250, 640, 250, 84, modules.RAG_EMBED,
                 "offline corpus indexing")

    _arrow(d, runtime, intake, "1 intake")
    _arrow(d, runtime, retrieve, "2 retrieve docs")
    _arrow(d, runtime, renderer, "3 render prompt")
    _arrow(d, runtime, codegen, "4 generate draft")
    _arrow(d, runtime, validator, "5 validate (every draft)")
    _arrow(d, runtime, audit, "6 audit (every pass)")
    _arrow(d, runtime, stores, "7 store + report")
    _arrow(d, embed, retrieve, "shared index", dashed=True)

    d.text((40, H - 40),
           "RAG-Embed runs offline to build the Pinecone index the "
           "RAG-Retrieve module queries at request time.",
           font=F_SMALL, fill=SUB)

    PNG.parent.mkdir(exist_ok=True)
    img.save(PNG)
    MANIFEST.write_text(json.dumps(
        {"boxes": list(modules.REGISTRY)}, indent=2), encoding="utf-8")
    print(f"wrote {PNG.name} + {MANIFEST.name} "
          f"({len(modules.REGISTRY)} registry boxes)")


if __name__ == "__main__":
    generate()
