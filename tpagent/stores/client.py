"""Supabase client factory -- the single home of the vendor SDK in stores/.

The SDK import is lazy so offline tests (mock client injected via
use_client) never touch it. Locally, .env is read once; on Vercel the
dashboard supplies the same variables and no .env file exists.
"""
from __future__ import annotations

import os

from tpagent.config import load_dotenv

_client = None
_override = None


def use_client(client) -> None:
    """Inject a client (tests pass the mock). Pass None to clear."""
    global _override
    _override = client


def get_client():
    if _override is not None:
        return _override
    global _client
    if _client is None:
        load_dotenv()
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError(
                "Supabase is not configured: set SUPABASE_URL and "
                "SUPABASE_SERVICE_KEY in .env (locally) or in the Vercel "
                "dashboard (production).")
        from supabase import create_client
        _client = create_client(url, key)
    return _client
