"""Thin wrapper around the Anthropic SDK: structured (Pydantic) outputs + images + cost tracking."""

from __future__ import annotations

import base64
import io
import json
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
        suffix = f" (part {i + 1}/{len(tiles)})" if len(tiles) > 1 else ""
        blocks.append({"type": "text", "text": f"[Image: {name}{suffix}]"})
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


def image_ref(path: str | Path, label: str | None = None) -> dict:
    return {"type": "image_ref", "path": str(path), "label": label or Path(path).name}


def _expand(content: list[dict]) -> list[dict]:
    out: list[dict] = []
    for b in content:
        out += image_blocks(b["path"], b["label"]) if b["type"] == "image_ref" else [b]
    return out


class AgentPending(Exception):
    def __init__(self, requests: list[Path]):
        self.requests = requests
        super().__init__(f"{len(requests)} tasks waiting for the agent")


class AgentLLM:
    """No API: writes each request to runs/<id>/agent/<key>.request.md and reads the answer from
    <key>.json, written by an agent such as Claude Code (see RECEPT.md)."""

    def __init__(self, run_dir: Path):
        self.dir = run_dir / "agent"
        self.dir.mkdir(exist_ok=True)

    def structured(self, *, key: str, system: str, content: list[dict] | str, schema: type[T], **_) -> T:
        answer = self.dir / f"{key}.json"
        if answer.exists():
            return schema.model_validate_json(answer.read_text(encoding="utf-8"))
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        parts = [f"# Task: {key}\n\n## Instructions\n{system}\n"]
        for b in content:
            if b["type"] == "image_ref":
                parts.append(f"[Image: {b['label']}] -> view file `{Path(b['path']).resolve()}`")
            else:
                parts.append(b["text"])
        parts.append(
            f"\n## Output\nWrite JSON matching this schema to `{answer.resolve()}`:\n```json\n"
            + json.dumps(schema.model_json_schema(), indent=1, ensure_ascii=False)
            + "\n```"
        )
        req = self.dir / f"{key}.request.md"
        req.write_text("\n\n".join(parts), encoding="utf-8")
        raise AgentPending([req])


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
        key: str = "",
    ) -> T:
        """One call, validated against `schema`. Server-side fallback re-runs a refused request on
        another model inside the same call (beta), so a false-positive refusal doesn't stop the run."""
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        content = _expand(content)
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
            raise RuntimeError(f"Claude refused the request in phase {phase}: {details}")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError(f"Response in phase {phase} was truncated (max_tokens). Increase max_tokens.")
        if resp.parsed_output is None:
            raise RuntimeError(f"Phase {phase}: response failed schema validation.")
        return resp.parsed_output
