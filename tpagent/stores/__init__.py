"""tpagent/stores -- table, session, output on Supabase (SOFTWARE.md 6.9).

Course delivery: Vercel has no persistent disk, so every store row lives in
Supabase (guide Part 1.2 tables). The runtime is the sole caller; the
Supabase SDK is imported in client.py only.
"""
