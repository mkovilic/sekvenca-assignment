from __future__ import annotations

from ..config import load_prompt
from ..llm import Claude
from ..schemas import BrandAnalysis, Brief, ContentPlan, Sources
from ..state import Run
from .analysis import facts_text


def run(run: Run, brief: Brief, sources: Sources, analysis: BrandAnalysis, claude: Claude, cfg: dict) -> ContentPlan:
    content = [
        {"type": "text", "text": f"## Brif\n{brief.model_dump_json(indent=2)}"},
        {"type": "text", "text": f"## Analiza brenda\n{analysis.model_dump_json(indent=2)}"},
        {"type": "text", "text": f"## Provjerene činjenice o proizvodima\n{facts_text(sources)}"},
    ]
    plan = claude.structured(
        phase="plan",
        model=cfg["models"]["reasoning"],
        effort=cfg["models"]["reasoning_effort"],
        system=load_prompt("02_plan.md").format(language=brief.language),
        content=content,
        schema=ContentPlan,
        max_tokens=32000,
    )
    valid_ids = {p.id for p in sources.products}
    for post in plan.posts:
        for f in post.frames:
            if f.product_id and f.product_id not in valid_ids:
                run.log(f"upozorenje: nepoznat proizvod '{f.product_id}' u objavi {post.number}, uklanjam")
                f.product_id, f.product_mode = "", "none"
    run.save("plan", plan)
    run.write_text("plan.md", to_markdown(plan))
    run.log("plan: " + ", ".join(f"{p.number}={p.format}" for p in plan.posts))
    return plan


def to_markdown(plan: ContentPlan) -> str:
    out = ["# Plan sadržaja\n"]
    for p in plan.posts:
        out.append(f"## Objava {p.number} — {p.format}\n\n**Cilj:** {p.goal}\n\n**Koncept:** {p.concept}\n\n**Zašto:** {p.rationale}\n")
        for i, f in enumerate(p.frames, 1):
            prod = f" · proizvod: {f.product_id} ({f.product_mode})" if f.product_id else ""
            out.append(f"{i}. **{f.headline}** — {f.subtext}{prod}\n   - scena: {f.scene_prompt}")
        out.append(f"\n**Caption brief:** {p.caption_brief}\n\n**Činjenice:** " + "; ".join(p.facts_used) + "\n")
    return "\n".join(out)
