"""OpenAI image model wrapper (generate a scene, or edit with reference packshots)."""

from __future__ import annotations

import base64
from contextlib import ExitStack
from pathlib import Path

from openai import OpenAI

from .costs import CostTracker


class ImageModel:
    def __init__(self, model: str, quality: str, costs: CostTracker):
        self.client = OpenAI()
        self.model = model
        self.quality = quality
        self.costs = costs

    def generate(self, prompt: str, size: str, out: Path, phase: str = "produce") -> Path:
        res = self.client.images.generate(model=self.model, prompt=prompt, size=size, quality=self.quality)
        self.costs.image(phase, self.model, getattr(res, "usage", None))
        out.write_bytes(base64.b64decode(res.data[0].b64_json))
        return out

    def edit(self, prompt: str, refs: list[Path], size: str, out: Path, phase: str = "produce") -> Path:
        with ExitStack() as stack:
            files = [stack.enter_context(open(p, "rb")) for p in refs]
            res = self.client.images.edit(
                model=self.model, image=files, prompt=prompt, size=size, quality=self.quality
            )
        self.costs.image(phase, self.model, getattr(res, "usage", None))
        out.write_bytes(base64.b64decode(res.data[0].b64_json))
        return out
