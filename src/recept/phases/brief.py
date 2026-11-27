from __future__ import annotations

from pathlib import Path

import yaml

from ..schemas import Brief, ProductRef
from ..state import Run

QUESTIONS = [
    ("brand", "Naziv brenda"),
    ("instagram", "Instagram profil (URL)"),
    ("website", "Web-stranica / webshop"),
    ("why_this_brand", "Zašto ovaj brend (kratko)"),
    ("audience", "Ciljana publika"),
    ("inspiration", "Uzori i inspiracija (opis ili putanje do slika)"),
    ("season", "Sezona / kontekst objave"),
    ("references_dir", "Mapa sa screenshotovima Instagram objava"),
]


def _ask(label: str, default: str = "") -> str:
    v = input(f"{label}{f' [{default}]' if default else ''}: ").strip()
    return v or default


def interactive() -> Brief:
    print("\n— Brifing — (Enter = preskoči)\n")
    data: dict = {k: _ask(label) for k, label in QUESTIONS}
    data["references_dir"] = data["references_dir"] or "inputs/instagram"
    products = []
    print("\nPoveznice proizvoda za promociju (prazan red za kraj):")
    while url := input("  URL proizvoda: ").strip():
        products.append(ProductRef(url=url, note=input("  Napomena: ").strip()))
    data["products"] = products
    goals = []
    print("\nCiljevi za 3 objave (prazan red za kraj):")
    while g := input("  Cilj: ").strip():
        goals.append(g)
    data["goals"] = goals or ["edukacija", "interes za kupnju", "reakcije i komentari"]
    data["constraints"] = [c.strip() for c in _ask("Ograničenja (odvojena s ;)").split(";") if c.strip()]
    return Brief.model_validate(data)


def run(run: Run, brief_path: str | None) -> Brief:
    if brief_path:
        brief = Brief.model_validate(yaml.safe_load(Path(brief_path).read_text(encoding="utf-8")))
    else:
        brief = interactive()
    run.save("brief", brief)
    run.log(f"brif: {brief.brand}, {len(brief.products)} proizvoda")
    return brief
