from __future__ import annotations

import argparse
import json
import os
import sys

from .config import load_config
from .costs import CostTracker
from .llm import AgentPending
from .schemas import BrandAnalysis, Brief, ContentPlan, Sources
from .state import PHASES, Run


def _approve(question: str, yes: bool) -> bool:
    if yes:
        return True
    return input(f"\n{question} [y/N]: ").strip().lower() in {"y", "yes"}


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    ap = argparse.ArgumentParser(prog="recept", description="From an Instagram brand to three finished posts.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the recipe (or resume it)")
    r.add_argument("--brief", help="YAML brief (omit for the interactive briefing)")
    r.add_argument("--run", dest="run_id", help="existing run id in runs/ to resume")
    r.add_argument("--latest", action="store_true", help="resume the most recent run")
    r.add_argument("--from", dest="start", choices=PHASES, help="start at this phase (earlier ones load from runs/)")
    r.add_argument("--to", dest="stop", choices=PHASES, help="stop after this phase")
    r.add_argument("--only-post", type=int, help="produce only post N")
    r.add_argument("--yes", action="store_true", help="skip the human approval gates")
    r.add_argument("--config", help="path to config.yaml")
    u = sub.add_parser("ui", help="open the local web UI")
    u.add_argument("--port", type=int, default=8765)
    u.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if args.cmd == "ui":
        from .ui.server import serve

        serve(args.port, not args.no_browser)
        return

    cfg = load_config(args.config)
    run = Run.latest() if args.latest else Run(args.run_id)
    run.log(f"run {run.id}")
    start = PHASES.index(args.start) if args.start else next((i for i, p in enumerate(PHASES) if not _done(run, p)), 0)
    stop = PHASES.index(args.stop) if args.stop else len(PHASES) - 1

    def todo(phase: str) -> bool:
        return start <= PHASES.index(phase) <= stop

    provider = cfg["models"].get("provider", "agent")
    _check_keys(todo, provider)

    costs = CostTracker(run, cfg["pricing"])
    llm = images = None
    if todo("analysis") or todo("plan") or todo("produce"):
        from .llm import AgentLLM, Claude, OpenAILLM

        if provider == "anthropic":
            llm = Claude(costs)
        elif provider == "openai":
            llm = OpenAILLM(costs, cfg["models"])
        else:
            llm = AgentLLM(run.dir)
    if todo("produce"):
        from .images import ImageModel

        images = ImageModel(cfg["models"]["image"], cfg["models"]["image_quality"], costs)

    try:
        _pipeline(args, run, cfg, todo, stop, llm, images)
    except AgentPending as e:
        if os.getenv("RECEPT_UI_AGENT"):
            print(f"Handing {len(e.requests)} task(s) to Claude Code: {', '.join(r.name.removesuffix('.request.md') for r in e.requests)}")
            sys.exit(3)
        print(f"\nWaiting for the agent. {len(e.requests)} task(s) in {run.dir / 'agent'}:")
        for req in e.requests:
            print(f"  - {req.name}")
        print(
            "\nOpen Claude Code in this folder (`claude`) and paste:\n\n"
            f"  Read RECEPT.md and continue the recipe run {run.id}. Do every agent task yourself, "
            "stop for my approval after the plan and before delivery.\n\n"
            "Or set models.provider: openai (only OPENAI_API_KEY) or anthropic (ANTHROPIC_API_KEY) in config.yaml "
            "to run without stopping, or use the web UI (uv run recept ui), which drives Claude Code for you."
        )
        sys.exit(3)


def _pipeline(args, run: Run, cfg: dict, todo, stop: int, llm, images) -> None:
    from .phases import analysis, brief, deliver, ingest, plan, produce

    b = brief.run(run, args.brief) if todo("brief") else run.load("brief", Brief)
    if stop == PHASES.index("brief"):
        return
    sources = ingest.run(run, b, cfg) if todo("ingest") else run.load("ingest", Sources)
    if stop == PHASES.index("ingest"):
        return
    a = analysis.run(run, b, sources, llm, cfg) if todo("analysis") else run.load("analysis", BrandAnalysis)
    if stop == PHASES.index("analysis"):
        return
    if todo("plan"):
        plan.run(run, b, sources, a, llm, cfg)
        print(f"\nPlan: {run.dir / 'plan.md'}\nEdit {run.dir / '3_plan.json'} to change it.")
        if not _approve("Approve the plan and start image generation (costs money)?", args.yes):
            print(f"Stopped. Resume with: uv run recept run --run {run.id} --from produce")
            return
    p = run.load("plan", ContentPlan)
    if stop == PHASES.index("plan"):
        return
    if todo("produce"):
        produce.run(run, b, sources, a, p, llm, images, cfg, args.only_post)
    if stop == PHASES.index("produce"):
        return
    print(f"\nFinished frames: {run.dir / 'posts'}")
    if not _approve("Approve the posts for delivery to deliverables/?", args.yes):
        print(f"Stopped. Resume with: uv run recept run --run {run.id} --from deliver")
        return
    deliver.run(run, b, sources, p)
    _print_costs(run)


def _done(run: Run, phase: str) -> bool:
    if phase == "produce":
        return run.path("4_produce.done").exists()
    if phase == "deliver":
        return False
    return run.has(phase)


def _check_keys(todo, provider: str) -> None:
    missing = []
    if provider == "anthropic" and (todo("analysis") or todo("plan") or todo("produce")) and not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if (todo("produce") or (provider == "openai" and (todo("analysis") or todo("plan")))) and not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if missing:
        raise SystemExit(f"Missing {', '.join(missing)} in .env (see .env.example).")


def _print_costs(run: Run) -> None:
    p = run.path("costs.json")
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        print(f"\nAI cost: ${d['total_usd']:.2f}  by phase: {d['by_phase']}")


if __name__ == "__main__":
    main()
