from __future__ import annotations

import json
import shutil

from ..config import ROOT
from ..schemas import Brief, Caption, ContentPlan, Sources
from ..state import Run


def run(run: Run, brief: Brief, sources: Sources, plan: ContentPlan, out_dir: str = "deliverables") -> None:
    dest = ROOT / out_dir
    dest.mkdir(exist_ok=True)
    for post in plan.posts:
        src = run.dir / "posts" / f"objava_{post.number}"
        d = dest / f"objava_{post.number}"
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()
        if post.format == "reel":
            shutil.copy(src / "reel.mp4", d / "reel.mp4")
            shutil.copy(src / "01.png", d / "cover.png")
        else:
            for i in range(1, len(post.frames) + 1):
                name = f"slajd_{i:02d}.png" if post.format == "carousel" else "objava.png"
                shutil.copy(src / f"{i:02d}.png", d / name)
        cap = Caption.model_validate_json((src / "caption.json").read_text(encoding="utf-8"))
        (d / "caption.txt").write_text(cap.caption.strip() + "\n\n" + " ".join(cap.hashtags) + "\n", encoding="utf-8")

        qa_lines = []
        for i in range(1, len(post.frames) + 1):
            q = json.loads((src / f"{i:02d}_qa.json").read_text(encoding="utf-8"))
            chosen = next(a for a in q["attempts"] if a["file"] == q["chosen"])
            qa_lines.append(f"- kadar {i}: ocjena {chosen['score']}/10, pokušaja {len(q['attempts'])}" + (f" — {'; '.join(chosen['issues'])}" if chosen["issues"] else ""))

        used = sorted({f.product_id for f in post.frames if f.product_id})
        prods = [p for p in sources.products if p.id in used]
        meta = f"""# Objava {post.number}

**Format:** {post.format}
**Cilj:** {post.goal}
**Koncept:** {post.concept}

## Obrazloženje
{post.rationale}

## Korištene činjenice
{chr(10).join('- ' + f for f in post.facts_used) or '- (nema tvrdnji o proizvodu)'}

## Izvori
- Instagram: {brief.instagram}
{chr(10).join(f'- {p.name}: {p.url}' for p in prods)}

## Alt tekst
{cap.alt_text}

## Provjera kvalitete
{chr(10).join(qa_lines)}

_Slike bez osoba. Pozadine generirane AI-em (OpenAI), proizvod je pravi packshot s webshopa ubačen kodom
osim gdje je u planu navedeno `ai_edit`. Tekst na slikama iscrtan je kodom u fontu sličnom brendu._
"""
        (d / "meta.md").write_text(meta, encoding="utf-8")

    for name in ("analiza.md", "plan.md", "costs.json"):
        if (run.dir / name).exists():
            shutil.copy(run.dir / name, dest / name)
    run.log(f"isporuka: {dest}")
