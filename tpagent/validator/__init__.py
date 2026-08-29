"""tpagent/validator -- the deterministic three-layer sieve (DESIGN.md 4.9).

grammar (token walks) -> existence (table membership) -> limits (numbers
vs static config). No LLM, no network, no randomness: membership testing
against closed sets. Entry point: verdict.run(text, table, limits, mode).

Owner policy (2026-08-29): table=None means "empty robot" - the
existence layer is skipped entirely; grammar and limits always run.
"""
from tpagent.validator.verdict import Err, Verdict, run

__all__ = ["Err", "Verdict", "run"]
