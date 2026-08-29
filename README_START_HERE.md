# tp-creator starter bundle

Everything needed to begin the Claude Code guide, in the layout it expects.

## Contents

| Path | What it is | Where the guide uses it |
|---|---|---|
| docs/Learn_ClaudeCode_TPAgent_Guide_v2.0.docx | THE GUIDE - open this first and follow it top to bottom | everywhere |
| docs/TP_Creator_Agent_Design_v1.3.docx | Design Document (what & why) | reference |
| docs/TP_Creator_Software_Architecture_v2.1.docx | SW Architecture (modules, classes, interfaces) | reference |
| CLAUDE.md | ready-made rules file - copy to the repo ROOT (guide Part 2 paste-box, already applied + context pointer) | Part 2 |
| docs/PROJECT_CONTEXT.md | the full session history & decision record - Claude Code's ONLY window into the design conversations; copy into repo docs/ | Part 1.4, every session |
| docs/DESIGN.md, docs/SOFTWARE.md | markdown exports of the two docs above - copy into the repo's docs/ (guide Part 1.4; Claude Code reads these) | Part 1.4, CLAUDE.md |
| prototype/ | the working tier-2 caller + mock unit (GUI, console, contract, reg_io parser, configs, CSV template) | Part 1.4 sanity run; Phase 1 migrates it verbatim |
| ir/ir.py | Pydantic v2 IR schema, 48 instruction types + options/helpers (79 models), tested | lands as tpagent/ir.py; feeds RAG instruction cards; future structured-generation path |
| ir/program.schema.json | exported JSON Schema (85 definitions) | GBNF / guided decoding when LLM #2 goes local |

## Quick start (10 minutes, before the guide)

1. Sanity-run the prototype:
       cd prototype
       py -m pip install pyyaml
       py gui.py
   Type: "pick a part from the conveyor and put it on the fixture, gently"
   -> expect the fixture A/B question -> answer "fixture A" -> program + report.
2. Open docs/Learn_ClaudeCode_TPAgent_Guide_v2.0.docx and start at Part 1
   (accounts & API keys). The bundle covers guide step 1.4 already: when you
   reach it, copy CLAUDE.md to the repo root, docs/DESIGN.md + docs/SOFTWARE.md +
   docs/PROJECT_CONTEXT.md into the repo's docs/, and prototype/ as-is.

## Also included (day-one convenience)

- .gitignore - ready; note corpus/raw/*.pdf is ignored (LFS or local-only)
- .env.template - copy to .env, fill keys (Part 1.5)
- corpus/prepared/FORMAT.md - the extraction spec for the controller PDFs;
  corpus/raw/README.md - where the 3 FANUC PDFs go
- tests/fixtures/v1.ls - the CANONICAL seeded-errors fixture from DESIGN.md
  section 8 (Phase 2 asserts its exact verdict; Phase 7 builds v2 from it)

## Not in this bundle (you create per the guide)

- .env with your keys (Part 1.5) - never share or commit
- corpus/ content: your 3 FANUC controller PDFs into corpus/raw/, extracted
  markdown into corpus/prepared/ (guide Phase 4 + the corpus layout note)
- the Pinecone index fanuc-tp-online (dimension 1536, cosine) - Part 1.1
