from __future__ import annotations

import argparse
import os
import sys

from .config import load_config
from .costs import CostTracker
from .schemas import BrandAnalysis, Brief, ContentPlan, Sources
from .state import PHASES, Run


def _approve(question: str, yes: bool) -> bool:
    if yes:
        return True
    return input(f"\n{question} [d/N]: ").strip().lower() in {"d", "da", "y", "yes"}


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    ap = argparse.ArgumentParser(prog="recept", description="Od Instagram brenda do tri gotove objave.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="pokreni recept (ili nastavi)")
    r.add_argument("--brief", help="YAML brif (bez njega: interaktivni brifing)")
    r.add_argument("--run", dest="run_id", help="ID postojećeg pokretanja u runs/ (za nastavak)")
    r.add_argument("--latest", action="store_true", help="nastavi zadnje pokretanje")
    r.add_argument("--from", dest="start", choices=PHASES, help="kreni od ove faze (ranije se učitavaju iz runs/)")
    r.add_argument("--to", dest="stop", choices=PHASES, help="stani nakon ove faze")
    r.add_argument("--only-post", type=int, help="izradi samo objavu N")
    r.add_argument("--yes", action="store_true", help="bez ljudskih odobrenja")
    r.add_argument("--config", help="putanja do config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    run = Run.latest() if args.latest else Run(args.run_id)
    run.log(f"pokretanje {run.id}")
    start = PHASES.index(args.start) if args.start else next((i for i, p in enumerate(PHASES) if not _done(run, p)), 0)
    stop = PHASES.index(args.stop) if args.stop else len(PHASES) - 1

    def todo(phase: str) -> bool:
        return start <= PHASES.index(phase) <= stop

    if todo("ingest") or todo("analysis") or todo("plan") or todo("produce"):
        _check_keys(todo)

    from .phases import analysis as ph_analysis
    from .phases import brief as ph_brief
    from .phases import deliver as ph_deliver
    from .phases import ingest as ph_ingest
    from .phases import plan as ph_plan
    from .phases import produce as ph_produce

    costs = CostTracker(run, cfg["pricing"])
    claude = images = None
    if todo("analysis") or todo("plan") or todo("produce"):
        from .llm import Claude

        claude = Claude(costs)
    if todo("produce"):
        from .images import ImageModel

        images = ImageModel(cfg["models"]["image"], cfg["models"]["image_quality"], costs)

    brief = ph_brief.run(run, args.brief) if todo("brief") else run.load("brief", Brief)
    if PHASES.index("brief") == stop:
        return
    sources = ph_ingest.run(run, brief, cfg) if todo("ingest") else run.load("ingest", Sources)
    if PHASES.index("ingest") == stop:
        return
    analysis = ph_analysis.run(run, brief, sources, claude, cfg) if todo("analysis") else run.load("analysis", BrandAnalysis)
    if PHASES.index("analysis") == stop:
        return
    if todo("plan"):
        plan = ph_plan.run(run, brief, sources, analysis, claude, cfg)
        print(f"\nPlan: {run.dir / 'plan.md'}\nUredi {run.dir / '3_plan.json'} ako želiš promjene.")
        if not _approve("Odobravaš plan i kreće izrada slika (trošak)?", args.yes):
            print(f"Zaustavljeno. Nastavak: uv run recept run --run {run.id} --from produce")
            return
    plan = run.load("plan", ContentPlan)
    if PHASES.index("plan") == stop:
        return
    if todo("produce"):
        ph_produce.run(run, brief, sources, analysis, plan, claude, images, cfg, args.only_post)
    if PHASES.index("produce") == stop:
        return
    print(f"\nGotovi kadrovi: {run.dir / 'posts'}")
    if not _approve("Odobravaš objave za isporuku u deliverables/?", args.yes):
        print(f"Zaustavljeno. Nastavak: uv run recept run --run {run.id} --from deliver")
        return
    ph_deliver.run(run, brief, sources, plan)
    _print_costs(run)


def _done(run: Run, phase: str) -> bool:
    if phase == "produce":
        return run.path("4_produce.done").exists()
    if phase == "deliver":
        return False
    return run.has(phase)


def _check_keys(todo) -> None:
    missing = []
    if (todo("analysis") or todo("plan") or todo("produce")) and not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if todo("produce") and not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if missing:
        raise SystemExit(f"Nedostaje {', '.join(missing)} u .env (vidi .env.example).")


def _print_costs(run: Run) -> None:
    import json

    p = run.path("costs.json")
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        print(f"\nTrošak AI poziva: ${d['total_usd']:.2f}  po fazama: {d['by_phase']}")


if __name__ == "__main__":
    main()
