from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = ROOT / "prompts"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if provider := os.getenv("RECEPT_PROVIDER"):
        cfg["models"]["provider"] = provider
    return cfg


def load_prompt(name: str) -> str:
    """Prompts live as Markdown files so they can be read and reused without the code."""
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")
