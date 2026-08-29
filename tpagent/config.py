"""Shared config access: .env loading + cached static_config.yaml.

Locally .env supplies the environment (values already present win); on
Vercel the dashboard supplies the same variables and no .env exists.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path | None = None) -> None:
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]                 # unquote like python-dotenv does
        os.environ.setdefault(k.strip(), v)


@lru_cache(maxsize=1)
def static_config() -> dict:
    path = ROOT / "config" / "static_config.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
