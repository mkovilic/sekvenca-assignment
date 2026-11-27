from __future__ import annotations

import json
from pathlib import Path

from ..config import load_prompt
from ..images import ImageModel
from ..llm import AgentPending, image_ref
from ..render.compose import Style, compose_frame
from ..render.reel import render_reel
from ..schemas import BrandAnalysis, Brief, Caption, CaptionQA, ContentPlan, Frame, PostPlan, QAResult, Sources
from ..state import Run
from .analysis import facts_text

SCENE_SUFFIX = (
    " Absolutely no text, letters, numbers, logos, labels, brand names, packaging or people anywhere in the image."
)
COMPOSITE_HINT = (
    " Leave a clean, empty surface in the lower-middle of the frame where a product will be placed later;"
    " lighting soft and frontal like a studio packshot."
)
ZONE_HINT = {
    "top": " Keep the upper third calm and uncluttered (darker, simple background) for a headline.",
    "bottom": " Keep the lower third calm and uncluttered for a headline.",
    "center": " Keep the centre calm and uncluttered for a headline.",
}
AI_EDIT_HINT = (
    " Place the product from the reference image into this scene as the hero, standing in the lower-middle."
    " Reproduce the packaging exactly as in the reference: same shape, colours, logo and label text, undistorted"
    " and fully legible. Do not add any other text or products."
)


class Producer:
    def __init__(self, run: Run, brief: Brief, sources: Sources, analysis: BrandAnalysis, claude, images: ImageModel, cfg: dict):
        self.run, self.brief, self.sources, self.analysis = run, brief, sources, analysis
        self.claude, self.images, self.cfg = claude, images, cfg
        self.style = Style(cfg)
        self.logo = run.dir / sources.logo if sources.logo else None
        self.products = {p.id: p for p in sources.products}

    def _scene(self, frame: Frame, fmt: dict, out: Path, fix: str) -> Path | None:
        if frame.layout == "dark_card":
            return None
        prompt = frame.scene_prompt + ZONE_HINT[frame.text_zone]
        if fix:
            prompt += " " + fix
        if out.exists():
            return out
        prod = self.products.get(frame.product_id)
        if frame.product_mode == "ai_edit" and prod and prod.local_images:
            return self.images.edit(prompt + AI_EDIT_HINT, [self.run.dir / prod.local_images[0]], fmt["gen_size"], out)
        if frame.product_mode == "composite":
            prompt += COMPOSITE_HINT
        return self.images.generate(prompt + SCENE_SUFFIX, fmt["gen_size"], out)

    def _qa(self, img_path: Path, frame: Frame, key: str) -> QAResult:
        prod = self.products.get(frame.product_id)
        content: list[dict] = [
            {"type": "text", "text": f"Brand palette: {', '.join(self.analysis.palette_hex)}\nVisual style: {'; '.join(self.analysis.visual_style)}"},
            {"type": "text", "text": f"Expected on-image text (rendered by code): {frame.headline} / {frame.subtext}"},
            {"type": "text", "text": f"Product expected: {'yes, ' + prod.name if prod and frame.product_mode != 'none' else 'no'}"},
            image_ref(img_path, "finished frame"),
        ]
        if prod and frame.product_mode != "none" and prod.local_images:
            content.append(image_ref(self.run.dir / prod.local_images[0], "real product packshot"))
        return self.claude.structured(
            phase="qa",
            key=key,
            model=self.cfg["models"]["reasoning"],
            effort="medium",
            system=load_prompt("04_qa_image.md"),
            content=content,
            schema=QAResult,
        )

    @staticmethod
    def _passes(q: QAResult, min_score: int) -> bool:
        return q.score >= min_score and q.product_accurate and q.text_legible and not q.has_unwanted_text_or_people

    def frame(self, post: PostPlan, idx: int, total: int) -> tuple[Path, Path | None]:
        """Returns (final composed frame, background-only frame for the reel)."""
        is_reel = post.format == "reel"
        fmt = self.cfg["formats"]["reel" if is_reel else "feed"]
        size = (fmt["width"], fmt["height"])
        d = self.run.path("posts", f"post_{post.number}")
        d.mkdir(exist_ok=True)
        final = d / f"{idx:02d}.png"
        bg_path = d / f"{idx:02d}_bg.png"
        qa_path = d / f"{idx:02d}_qa.json"
        if final.exists() and qa_path.exists():
            return final, bg_path if bg_path.exists() else None

        frame = post.frames[idx - 1]
        prod = self.products.get(frame.product_id)
        cutout = self.run.dir / prod.cutout if prod and prod.cutout else None
        page = (idx, total) if post.format == "carousel" else None
        history, fix, best = [], "", None
        for attempt in range(self.cfg["qa"]["max_retries"] + 1):
            scene = self._scene(frame, fmt, d / f"{idx:02d}_scene_a{attempt}.png", fix)
            img = compose_frame(frame=frame, scene=scene, cutout=cutout, logo=self.logo, size=size, style=self.style, page=page)
            cand = d / f"{idx:02d}_a{attempt}.png"
            img.convert("RGB").save(cand)
            q = self._qa(cand, frame, f"qa_post{post.number}_frame{idx:02d}_a{attempt}")
            history.append({"attempt": attempt, "file": cand.name, **q.model_dump()})
            self.run.log(f"post {post.number} frame {idx} attempt {attempt}: score {q.score} {'PASS' if self._passes(q, self.cfg['qa']['min_score']) else 'FAIL: ' + '; '.join(q.issues)[:160]}")
            if best is None or q.score > best[0]:
                best = (q.score, cand, scene, q)
            if self._passes(q, self.cfg["qa"]["min_score"]) or frame.layout == "dark_card":
                break
            fix = q.fix_for_image_model
        assert best
        final.write_bytes(best[1].read_bytes())
        if is_reel:
            bg = compose_frame(frame=frame, scene=best[2], cutout=cutout, logo=None, size=size, style=self.style, with_text=False)
            bg.convert("RGB").save(bg_path)
        qa_path.write_text(json.dumps({"chosen": best[1].name, "attempts": history}, indent=2, ensure_ascii=False), encoding="utf-8")
        if not self._passes(best[3], self.cfg["qa"]["min_score"]):
            self.run.log(f"  ! post {post.number} frame {idx}: no attempt passed, flagged for human review")
        return final, bg_path if is_reel else None

    def caption(self, post: PostPlan) -> Caption:
        d = self.run.path("posts", f"post_{post.number}")
        d.mkdir(exist_ok=True)
        cap_path = d / "caption.json"
        if cap_path.exists():
            return Caption.model_validate_json(cap_path.read_text(encoding="utf-8"))
        ctx = [
            {"type": "text", "text": f"## Post\n{post.model_dump_json(indent=2)}"},
            {"type": "text", "text": f"## Brand analysis (captions, hashtags, tone)\nTone: {self.analysis.tone_of_voice}\nCaptions: {self.analysis.caption_patterns}\nHashtags: {self.analysis.hashtags}"},
            {"type": "text", "text": f"## Verified facts\n{facts_text(self.sources)}"},
        ]
        cap = self.claude.structured(
            phase="caption",
            key=f"caption_post{post.number}",
            model=self.cfg["models"]["copy"],
            effort=self.cfg["models"]["copy_effort"],
            system=load_prompt("03_caption.md").format(language=self.brief.language),
            content=ctx,
            schema=Caption,
        )
        texts = "\n".join(f"- {f.headline} / {f.subtext}" for f in post.frames)
        check = self.claude.structured(
            phase="qa",
            key=f"caption_qa_post{post.number}",
            model=self.cfg["models"]["reasoning"],
            effort="medium",
            system=load_prompt("05_qa_caption.md"),
            content=f"## Caption\n{cap.caption}\n\n## On-image texts\n{texts}\n\n## Verified facts\n{facts_text(self.sources)}",
            schema=CaptionQA,
        )
        (d / "caption_qa.json").write_text(check.model_dump_json(indent=2), encoding="utf-8")
        if not check.ok:
            self.run.log(f"post {post.number}: caption corrected ({'; '.join(check.unsupported_claims)[:160]})")
            cap.caption = check.suggested_fix or cap.caption
        cap_path.write_text(cap.model_dump_json(indent=2), encoding="utf-8")
        return cap

    def post(self, post: PostPlan) -> list[Path]:
        total = len(post.frames)
        pending: list[Path] = []
        results = []
        for i in range(1, total + 1):
            try:
                results.append(self.frame(post, i, total))
            except AgentPending as e:
                pending += e.requests
        try:
            self.caption(post)
        except AgentPending as e:
            pending += e.requests
        if pending:
            return pending
        if post.format == "reel":
            out = self.run.path("posts", f"post_{post.number}", "reel.mp4")
            if not out.exists():
                from PIL import Image

                shots = [(Image.open(bg).convert("RGBA"), post.frames[i]) for i, (_, bg) in enumerate(results) if bg]
                render_reel(shots, out, self.style, self.logo, self.cfg["formats"]["reel_seconds_per_frame"], self.cfg["formats"]["reel_fps"])
                self.run.log(f"post {post.number}: reel.mp4 rendered ({len(shots)} shots)")
        return []


def run(run: Run, brief: Brief, sources: Sources, analysis: BrandAnalysis, plan: ContentPlan, claude, images: ImageModel, cfg: dict, only: int | None = None) -> None:
    p = Producer(run, brief, sources, analysis, claude, images, cfg)
    pending: list[Path] = []
    for post in plan.posts:
        if only and post.number != only:
            continue
        run.log(f"— producing post {post.number} ({post.format}, {len(post.frames)} frames)")
        pending += p.post(post)
    if pending:
        raise AgentPending(pending)
    if not only:
        run.write_text("4_produce.done", "ok")
