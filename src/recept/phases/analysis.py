from __future__ import annotations

from ..config import ROOT, load_prompt
from ..llm import image_ref
from ..schemas import BrandAnalysis, Brief, Sources
from ..state import Run


def facts_text(sources: Sources) -> str:
    out = []
    for p in sources.products:
        out.append(f"### {p.name}\nid: {p.id}\nurl: {p.url}\ncategory: {p.category}\ndescription: {p.description}")
        if p.price_low_eur:
            out.append(f"price range (EUR, depends on pack size): {p.price_low_eur} – {p.price_high_eur}")
        for f in p.faq:
            out.append(f"- Q: {f.question}\n  A: {f.answer}")
    return "\n".join(out)


def run(run: Run, brief: Brief, sources: Sources, claude, cfg: dict) -> BrandAnalysis:
    content: list[dict] = [
        {"type": "text", "text": f"## Brief\n{brief.model_dump_json(indent=2)}"},
        {"type": "text", "text": f"## Verified product facts (webshop)\n{facts_text(sources)}"},
        {"type": "text", "text": "## Unavailable sources\n" + "\n".join(sources.unavailable)},
        {"type": "text", "text": "## Instagram screenshots"},
    ]
    for shot in sources.instagram_screenshots:
        content.append(image_ref(ROOT / shot))

    analysis = claude.structured(
        phase="analysis",
        key="analysis",
        model=cfg["models"]["reasoning"],
        effort=cfg["models"]["reasoning_effort"],
        system=load_prompt("01_analysis.md").format(language=brief.language),
        content=content,
        schema=BrandAnalysis,
        max_tokens=32000,
    )
    run.save("analysis", analysis)
    run.write_text("analysis.md", to_markdown(analysis))
    run.log(f"analysis: {len(analysis.verified_facts)} verified facts, {len(analysis.assumptions)} assumptions")
    return analysis


def to_markdown(a: BrandAnalysis) -> str:
    def ul(items):
        return "\n".join(f"- {i}" for i in items)

    return f"""# Brand analysis

{a.summary}

## Tone of voice
{ul(a.tone_of_voice)}

## Audience
{a.audience}

## Recurring themes
{ul(a.recurring_themes)}

## Visual style
{ul(a.visual_style)}

**Palette:** {", ".join(a.palette_hex)}
**Typography:** {a.typography}

## Product presentation
{a.product_presentation}

## People
{a.people_presentation}

## Captions
{ul(a.caption_patterns)}

**Hashtags:** {" ".join(a.hashtags)}

## Engagement
{ul(a.engagement_observations)}

## Verified (with source)
{ul(f"{e.claim} — _{e.source}_" for e in a.verified_facts)}

## Assumptions (not verified)
{ul(a.assumptions)}

## Unavailable sources
{ul(a.unavailable_sources)}

## Opportunities
{ul(a.opportunities)}
"""
