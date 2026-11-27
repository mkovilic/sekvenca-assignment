"""Track every AI call's tokens and estimated USD cost into runs/<id>/costs.json."""

from __future__ import annotations

import json
from datetime import datetime

from .state import Run


class CostTracker:
    def __init__(self, run: Run, pricing: dict):
        self.run = run
        self.pricing = pricing
        self.path = run.path("costs.json")

    def _add(self, entry: dict) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"calls": []}
        data["calls"].append(entry)
        data["total_usd"] = round(sum(c["usd"] for c in data["calls"]), 4)
        by_phase: dict[str, float] = {}
        for c in data["calls"]:
            by_phase[c["phase"]] = round(by_phase.get(c["phase"], 0) + c["usd"], 4)
        data["by_phase"] = by_phase
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def claude(self, phase: str, model: str, usage) -> float:
        p = self.pricing.get(model) or {"input": 0, "output": 0}
        inp = (usage.input_tokens or 0) + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * 1.25
        cached = getattr(usage, "cache_read_input_tokens", 0) or 0
        usd = (inp * p["input"] + cached * p["input"] * 0.1 + usage.output_tokens * p["output"]) / 1e6
        self._add(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "phase": phase,
                "model": model,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "usd": round(usd, 5),
            }
        )
        return usd

    def openai(self, phase: str, model: str, usage) -> float:
        p = self.pricing.get(model) or {"input": 0, "output": 0}
        cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
        inp = (usage.input_tokens or 0) - cached
        usd = (inp * p["input"] + cached * p.get("cached_input", p["input"] * 0.1) + usage.output_tokens * p["output"]) / 1e6
        self._add(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "phase": phase,
                "model": model,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "usd": round(usd, 5),
            }
        )
        return usd

    def image(self, phase: str, model: str, usage) -> float:
        p = self.pricing.get(model) or {"text_input": 0, "image_input": 0, "image_output": 0}
        if usage is None:
            usd, detail = 0.0, {}
        else:
            ind = getattr(usage, "input_tokens_details", None)
            text_in = getattr(ind, "text_tokens", 0) or 0
            img_in = getattr(ind, "image_tokens", 0) or 0
            out = usage.output_tokens or 0
            usd = (text_in * p["text_input"] + img_in * p["image_input"] + out * p["image_output"]) / 1e6
            detail = {"text_in": text_in, "image_in": img_in, "image_out": out}
        self._add(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "phase": phase,
                "model": model,
                **detail,
                "usd": round(usd, 5),
            }
        )
        return usd
