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
        src = run.dir / "posts" / f"post_{post.number}"
        d = dest / f"post_{post.number}"
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()
        if post.format == "reel":
            shutil.copy(src / "reel.mp4", d / "reel.mp4")
            shutil.copy(src / "01.png", d / "cover.png")
        else:
            for i in range(1, len(post.frames) + 1):
                name = f"slide_{i:02d}.png" if post.format == "carousel" else "post.png"
                shutil.copy(src / f"{i:02d}.png", d / name)
        cap = Caption.model_validate_json((src / "caption.json").read_text(encoding="utf-8"))
        (d / "caption.txt").write_text(cap.caption.strip() + "\n\n" + " ".join(cap.hashtags) + "\n", encoding="utf-8")

        qa_lines = []
        for i in range(1, len(post.frames) + 1):
            q = json.loads((src / f"{i:02d}_qa.json").read_text(encoding="utf-8"))
            chosen = next(a for a in q["attempts"] if a["file"] == q["chosen"])
            issues = f" — {'; '.join(chosen['issues'])}" if chosen["issues"] else ""
            qa_lines.append(f"- frame {i}: score {chosen['score']}/10, attempts {len(q['attempts'])}{issues}")

        used = sorted({f.product_id for f in post.frames if f.product_id})
        prods = [p for p in sources.products if p.id in used]
        facts = "\n".join("- " + f for f in post.facts_used) or "- (no product claims)"
        links = "\n".join(f"- {p.name}: {p.url}" for p in prods)
        meta = f"""# Post {post.number}

**Format:** {post.format}
**Goal:** {post.goal}
**Concept:** {post.concept}

## Rationale
{post.rationale}

## Facts used
{facts}

## Sources
- Instagram: {brief.instagram}
{links}

## Alt text
{cap.alt_text}

## Quality check
{chr(10).join(qa_lines)}

_No people. Backgrounds generated with OpenAI; the product is the real webshop packshot composited by code
(except frames marked `ai_edit` in the plan). On-image text is rendered by code in a font close to the brand's._
"""
        (d / "meta.md").write_text(meta, encoding="utf-8")

    for name in ("analysis.md", "plan.md", "costs.json"):
        if (run.dir / name).exists():
            shutil.copy(run.dir / name, dest / name)
    run.log(f"delivered to {dest}")
