"""Run directory + phase checkpoints, so work can resume from a saved phase."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .config import ROOT

PHASES = ["brief", "ingest", "analysis", "plan", "produce", "deliver"]

T = TypeVar("T", bound=BaseModel)


class Run:
    def __init__(self, run_id: str | None = None):
        self.id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir = ROOT / "runs" / self.id
        self.dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def latest(cls) -> "Run":
        runs = sorted((ROOT / "runs").glob("*/"))
        if not runs:
            raise SystemExit("Nema prethodnih pokretanja u runs/.")
        return cls(runs[-1].name)

    def path(self, *parts: str) -> Path:
        p = self.dir.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def rel(self, p: Path) -> str:
        return p.relative_to(self.dir).as_posix()

    # --- checkpoints ---
    def save(self, phase: str, model: BaseModel) -> Path:
        p = self.path(f"{PHASES.index(phase)}_{phase}.json")
        p.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        return p

    def load(self, phase: str, cls: type[T]) -> T:
        p = self.path(f"{PHASES.index(phase)}_{phase}.json")
        if not p.exists():
            raise SystemExit(f"Faza '{phase}' nije spremljena u {self.dir}. Pokreni je prvo.")
        return cls.model_validate_json(p.read_text(encoding="utf-8"))

    def has(self, phase: str) -> bool:
        return self.path(f"{PHASES.index(phase)}_{phase}.json").exists()

    def write_text(self, name: str, text: str) -> Path:
        p = self.path(name)
        p.write_text(text, encoding="utf-8")
        return p

    def log(self, msg: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with open(self.path("run.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def append_json(self, name: str, obj: dict) -> None:
        p = self.path(name)
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        data.append(obj)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
