"""MODULE NAME REGISTRY (CLAUDE.md course rules).

The ONLY source of module names, everywhere: the architecture diagram,
every steps[] entry, and all descriptions. The consistency requirement
is solved mechanically by importing these constants -- never retype a
name as a string literal.
"""

RUNTIME = "Runtime"
LLM1_INTAKE = "LLM1-Intake"
LLM1_AUDIT = "LLM1-Audit"
RENDERER = "Renderer"
LLM2_CODEGEN = "LLM2-Codegen"
VALIDATOR = "Validator"
RAG_EMBED = "RAG-Embed"
RAG_RETRIEVE = "RAG-Retrieve"
STORES = "Stores"

REGISTRY = (RUNTIME, LLM1_INTAKE, LLM1_AUDIT, RENDERER, LLM2_CODEGEN,
            VALIDATOR, RAG_EMBED, RAG_RETRIEVE, STORES)
