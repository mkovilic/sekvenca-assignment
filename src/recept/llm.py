"""Thin wrapper around the Anthropic SDK: structured (Pydantic) outputs + images + cost tracking."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import TypeVar

import anthropic
from PIL import Image
from pydantic import BaseModel

from .costs import CostTracker

T = TypeVar("T", bound=BaseModel)

MAX_EDGE = 1568  # Claude's recommended max long edge for vision input


def image_blocks(path: str | Path, label: str | None = None) -> list[dict]:
    """Encode an image for Claude. Very tall screenshots (e.g. a profile grid) are split into
    readable tiles instead of being shrunk into an illegible strip."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    tiles: list[Image.Image] = []
    if h > 1.6 * w:
        step = int(w * 1.3)
        for top in range(0, h, step):
            tiles.append(img.crop((0, top, w, min(h, top + step))))
    else:
        tiles.append(img)

    blocks: list[dict] = []
    name = label or Path(path).name
    for i, tile in enumerate(tiles):
        tile.thumbnail((MAX_EDGE, MAX_EDGE))
        buf = io.BytesIO()
        tile.save(buf, format="JPEG", quality=88)
        suffix = f" (dio {i + 1}/{len(tiles)})" if len(tiles) > 1 else ""
        blocks.append({"type": "text", "text": f"[Slika: {name}{suffix}]"})
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(buf.getvalue()).decode(),
                },
            }
        )
    return blocks


class Claude:
    def __init__(self, costs: CostTracker):
        self.client = anthropic.Anthropic()
        self.costs = costs

    def structured(
        self,
        *,
        phase: str,
        model: str,
        effort: str,
        system: str,
        content: list[dict] | str,
        schema: type[T],
        max_tokens: int = 16000,
    ) -> T:
        """One call, validated against `schema`. Server-side fallback re-runs a refused request on
        another model inside the same call (beta), so a false-positive refusal doesn't stop the run."""
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        with self.client.beta.messages.stream(
            model=model,
            max_tokens=max_tokens,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system,
            output_config={"effort": effort},
            output_format=schema,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            resp = stream.get_final_message()
        self.costs.claude(phase, resp.model or model, resp.usage)
        if resp.stop_reason == "refusal":
            details = getattr(resp, "stop_details", None)
            raise RuntimeError(f"Claude je odbio zahtjev u fazi {phase}: {details}")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError(f"Odgovor u fazi {phase} je odrezan (max_tokens). Povećaj max_tokens.")
        if resp.parsed_output is None:
            raise RuntimeError(f"Faza {phase}: odgovor nije prošao validaciju sheme.")
        return resp.parsed_output
