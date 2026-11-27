from __future__ import annotations

from pathlib import Path

import yaml

from ..schemas import Brief, ProductRef
from ..state import Run

QUESTIONS = [
    ("brand", "Brand name"),
    ("instagram", "Instagram profile URL"),
    ("website", "Website / webshop"),
    ("why_this_brand", "Why this brand (short)"),
    ("audience", "Target audience"),
    ("inspiration", "Role models and inspiration (text or image paths)"),
    ("season", "Season / context"),
    ("references_dir", "Folder with Instagram post screenshots"),
]


def _ask(label: str, default: str = "") -> str:
    v = input(f"{label}{f' [{default}]' if default else ''}: ").strip()
    return v or default


def interactive() -> Brief:
    print("\n— Briefing — (Enter = skip)\n")
    data: dict = {k: _ask(label) for k, label in QUESTIONS}
    data["references_dir"] = data["references_dir"] or "inputs/instagram"
    products = []
    print("\nProduct page URLs to promote (empty line to finish):")
    while url := input("  Product URL: ").strip():
        products.append(ProductRef(url=url, note=input("  Note: ").strip()))
    data["products"] = products
    goals = []
    print("\nGoals for the 3 posts (empty line to finish):")
    while g := input("  Goal: ").strip():
        goals.append(g)
    data["goals"] = goals or ["education", "purchase intent", "reactions and comments"]
    data["constraints"] = [c.strip() for c in _ask("Constraints (separated by ;)").split(";") if c.strip()]
    data["language"] = _ask("Post language", "en")
    return Brief.model_validate(data)


def run(run: Run, brief_path: str | None) -> Brief:
    if brief_path:
        brief = Brief.model_validate(yaml.safe_load(Path(brief_path).read_text(encoding="utf-8")))
    else:
        brief = interactive()
    run.save("brief", brief)
    run.log(f"brief: {brief.brand}, {len(brief.products)} products")
    return brief
