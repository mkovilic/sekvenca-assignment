from __future__ import annotations

from ..config import ROOT, load_prompt
from ..llm import Claude, image_blocks
from ..schemas import BrandAnalysis, Brief, Sources
from ..state import Run


def facts_text(sources: Sources) -> str:
    out = []
    for p in sources.products:
        out.append(f"### {p.name}\nid: {p.id}\nurl: {p.url}\nkategorija: {p.category}\nopis: {p.description}")
        if p.price_low_eur:
            out.append(f"raspon cijena (EUR, ovisno o pakiranju): {p.price_low_eur} – {p.price_high_eur}")
        for f in p.faq:
            out.append(f"- P: {f.question}\n  O: {f.answer}")
    return "\n".join(out)


def run(run: Run, brief: Brief, sources: Sources, claude: Claude, cfg: dict) -> BrandAnalysis:
    content: list[dict] = [
        {"type": "text", "text": f"## Brif\n{brief.model_dump_json(indent=2)}"},
        {"type": "text", "text": f"## Provjerene činjenice o proizvodima (webshop)\n{facts_text(sources)}"},
        {"type": "text", "text": "## Nedostupni izvori\n" + "\n".join(sources.unavailable)},
        {"type": "text", "text": "## Instagram screenshotovi"},
    ]
    for shot in sources.instagram_screenshots:
        content += image_blocks(ROOT / shot)

    analysis = claude.structured(
        phase="analysis",
        model=cfg["models"]["reasoning"],
        effort=cfg["models"]["reasoning_effort"],
        system=load_prompt("01_analiza.md").format(language=brief.language),
        content=content,
        schema=BrandAnalysis,
        max_tokens=32000,
    )
    run.save("analysis", analysis)
    run.write_text("analiza.md", to_markdown(analysis))
    run.log(f"analiza: {len(analysis.verified_facts)} provjerenih činjenica, {len(analysis.assumptions)} pretpostavki")
    return analysis


def to_markdown(a: BrandAnalysis) -> str:
    def ul(items):
        return "\n".join(f"- {i}" for i in items)

    return f"""# Analiza brenda

{a.summary}

## Ton
{ul(a.tone_of_voice)}

## Publika
{a.audience}

## Teme
{ul(a.recurring_themes)}

## Vizualni stil
{ul(a.visual_style)}

**Paleta:** {", ".join(a.palette_hex)}
**Tipografija:** {a.typography}

## Prikaz proizvoda
{a.product_presentation}

## Prikaz osoba
{a.people_presentation}

## Captioni
{ul(a.caption_patterns)}

**Hashtagovi:** {" ".join(a.hashtags)}

## Angažman
{ul(a.engagement_observations)}

## Provjereno (s izvorom)
{ul(f"{e.claim} — _{e.source}_" for e in a.verified_facts)}

## Pretpostavke (nije provjereno)
{ul(a.assumptions)}

## Nedostupni izvori
{ul(a.unavailable_sources)}

## Prilike
{ul(a.opportunities)}
"""
