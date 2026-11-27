"""Answers pending agent tasks by running Claude Code headless (`claude -p`), one process per task."""

from __future__ import annotations

import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from .config import ROOT
from .schemas import BrandAnalysis, Caption, CaptionQA, ContentPlan, QAResult

SCHEMAS: list[tuple[str, type[BaseModel]]] = [
    ("analysis", BrandAnalysis),
    ("plan", ContentPlan),
    ("qa_post", QAResult),
    ("caption_qa_post", CaptionQA),
    ("caption_post", Caption),
]

PROMPT = """You are one step of the `recept` pipeline, running unattended.
Read the task file `{req}`. Follow its Instructions section, open every image path it lists with the Read tool
(screenshots, finished frames, real packshots) and look at them, then write ONLY the JSON answer to
`{out}`, matching the schema in the task exactly. Do not create or change any other file. Do not ask questions.

Rules:
{rules}"""


def claude_path() -> str | None:
    return shutil.which("claude")


def _rules() -> str:
    text = (ROOT / "RECEPT.md").read_text(encoding="utf-8")
    start = text.find("## Rules for the agent")
    end = text.find("## ", start + 5)
    return text[start:end].split("\n", 1)[1].strip() if start >= 0 else ""


def _env() -> dict:
    """Use the Claude Code login, not an API key from .env (which may have no credit)."""
    return {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}


def schema_for(key: str) -> type[BaseModel]:
    for prefix, schema in SCHEMAS:
        if key.startswith(prefix):
            return schema
    raise ValueError(f"Unknown task {key}")


def pending(agent_dir: Path) -> list[Path]:
    return [r for r in sorted(agent_dir.glob("*.request.md")) if not _answer(r).exists()]


def _answer(req: Path) -> Path:
    return req.with_name(req.name.removesuffix(".request.md") + ".json")


def answer_one(req: Path, log: Callable[[str], None], model: str | None = None, attempts: int = 2) -> bool:
    key = req.name.removesuffix(".request.md")
    out = _answer(req)
    cmd = [claude_path() or "claude", "-p", PROMPT.format(req=req, out=out, rules=_rules()),
           "--tools", "Read,Write", "--permission-mode", "acceptEdits", "--no-session-persistence",
           "--output-format", "text"]
    if model:
        cmd += ["--model", model]
    for attempt in range(1, attempts + 1):
        log(f"[claude] {key}: working (attempt {attempt})")
        try:
            r = subprocess.run(cmd, cwd=ROOT, env=_env(), stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=900)
        except subprocess.TimeoutExpired:
            log(f"[claude] {key}: timed out")
            continue
        if not out.exists():
            log(f"[claude] {key}: no answer written (exit {r.returncode}) {r.stdout.strip()[-300:]} {r.stderr.strip()[-300:]}")
            continue
        try:
            schema_for(key).model_validate_json(out.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"[claude] {key}: answer does not match the schema, retrying ({str(e)[:200]})")
            out.unlink()
            continue
        log(f"[claude] {key}: done")
        return True
    return False


def answer_all(agent_dir: Path, log: Callable[[str], None], keys: list[str] | None = None,
               model: str | None = None, workers: int = 4) -> bool:
    reqs = [r for r in pending(agent_dir) if keys is None or r.name.removesuffix(".request.md") in keys]
    if not reqs:
        return True
    log(f"[claude] answering {len(reqs)} task(s) with Claude Code")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda r: answer_one(r, log, model), reqs))
    return all(results)
