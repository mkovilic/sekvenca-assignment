"""Local web UI: brief, step-by-step run with the two approval gates, plan editing, frame review and regeneration.

Each step runs the CLI in a subprocess, so the UI and the terminal use exactly the same recipe."""

from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import markdown
from pydantic import ValidationError

from ..agent_runner import answer_all, claude_path
from ..config import ROOT, load_config
from ..schemas import ContentPlan

RUNS = ROOT / "runs"
HERE = Path(__file__).parent
ID_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")


class Job:
    """One UI step. In mode "claude" it loops: run the CLI, answer agent tasks with Claude Code, rerun."""

    def __init__(self, run_id: str, action: str, cmd: list[str], mode: str):
        self.run_id, self.action, self.cmd, self.mode = run_id, action, cmd, mode
        self.lines: list[str] = []
        self.code: int | None = None
        self.phase = "running"
        self.started = time.time()
        threading.Thread(target=self._loop, daemon=True).start()

    def log(self, line: str) -> None:
        self.lines.append(line)

    def _cli(self) -> int:
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1",
               "RECEPT_PROVIDER": "anthropic" if self.mode == "api" else "agent"}
        if self.mode == "claude":
            env["RECEPT_UI_AGENT"] = "1"
        proc = subprocess.Popen(
            self.cmd, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        assert proc.stdout
        for line in proc.stdout:
            self.log(line.rstrip())
        return proc.wait()

    def _loop(self) -> None:
        try:
            for _ in range(12):
                self.phase = "running"
                code = self._cli()
                if code != 3 or self.mode != "claude":
                    self.code = code
                    return
                self.phase = "agent"
                keys = self._handed_keys()
                if not keys or not answer_all(RUNS / self.run_id / "agent", self.log, keys):
                    self.log("[claude] some tasks could not be answered; see above. Retry or answer them manually.")
                    self.code = 3
                    return
                self.log("[claude] all tasks answered, continuing")
            self.code = 1
        except Exception as e:
            self.log(f"error: {e}")
            self.code = 1

    def _handed_keys(self) -> list[str]:
        prefix = "Handing "
        for line in reversed(self.lines):
            if line.startswith(prefix) and ": " in line:
                return [k.strip() for k in line.split(": ", 1)[1].split(",")]
        return []

    def state(self) -> dict:
        return {"id": self.started, "action": self.action, "mode": self.mode, "phase": self.phase,
                "running": self.code is None, "code": self.code, "lines": self.lines[-300:]}


JOBS: dict[str, Job] = {}


def _cli(*args: str) -> list[str]:
    return [sys.executable, "-m", "recept.cli", "run", *args]


def _run_dir(run_id: str) -> Path:
    if not run_id or not set(run_id) <= ID_OK:
        raise ValueError("Run id may contain only letters, digits, - and _.")
    return RUNS / run_id


def _url(p: Path) -> str:
    return f"/files/{p.relative_to(ROOT).as_posix()}?v={int(p.stat().st_mtime)}"


def _md(p: Path) -> str:
    return markdown.markdown(p.read_text(encoding="utf-8"), extensions=["tables"]) if p.exists() else ""


def _read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _phases(d: Path) -> dict:
    log = d / "run.log"
    return {
        "brief": (d / "0_brief.json").exists(),
        "ingest": (d / "1_ingest.json").exists(),
        "analysis": (d / "2_analysis.json").exists(),
        "plan": (d / "3_plan.json").exists(),
        "produce": (d / "4_produce.done").exists(),
        "deliver": log.exists() and "delivered to" in log.read_text(encoding="utf-8", errors="replace"),
    }


def _pending(d: Path) -> list[dict]:
    a = d / "agent"
    if not a.exists():
        return []
    out = []
    for req in sorted(a.glob("*.request.md")):
        key = req.name.removesuffix(".request.md")
        if not (a / f"{key}.json").exists():
            out.append({"key": key, "path": str(req)})
    return out


def _posts(d: Path, cfg: dict) -> list[dict]:
    plan = _read_json(d / "3_plan.json")
    if not plan:
        return []
    min_score = cfg["qa"]["min_score"]
    posts = []
    for p in plan["posts"]:
        pd = d / "posts" / f"post_{p['number']}"
        frames = []
        for i, fr in enumerate(p["frames"], 1):
            img, qa = pd / f"{i:02d}.png", _read_json(pd / f"{i:02d}_qa.json")
            chosen = next((a for a in (qa or {}).get("attempts", []) if a["file"] == qa.get("chosen")), None)
            frames.append({
                "idx": i,
                "headline": fr["headline"],
                "img": _url(img) if img.exists() else None,
                "attempts": len(qa["attempts"]) if qa else 0,
                "score": chosen["score"] if chosen else None,
                "passed": bool(chosen and chosen["score"] >= min_score and chosen["product_accurate"]
                               and chosen["text_legible"] and not chosen["has_unwanted_text_or_people"]),
                "issues": chosen["issues"] if chosen else [],
            })
        cap = _read_json(pd / "caption.json")
        reel = pd / "reel.mp4"
        posts.append({
            "number": p["number"], "format": p["format"], "goal": p["goal"], "concept": p["concept"],
            "frames": frames, "caption": cap, "reel": _url(reel) if reel.exists() else None,
        })
    return posts


def run_list() -> list[dict]:
    if not RUNS.exists():
        return []
    out = []
    for d in sorted(RUNS.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if d.is_dir():
            b = _read_json(d / "0_brief.json") or {}
            out.append({"id": d.name, "brand": b.get("brand", ""), "phases": _phases(d), "running": _running(d.name)})
    return out


def _running(run_id: str) -> bool:
    j = JOBS.get(run_id)
    return bool(j and j.code is None)


def run_detail(run_id: str) -> dict:
    d = _run_dir(run_id)
    if not d.exists():
        raise FileNotFoundError(run_id)
    cfg = load_config()
    costs = _read_json(d / "costs.json") or {}
    brief_yaml = d / "brief.input.yaml"
    plan = d / "3_plan.json"
    job = JOBS.get(run_id)
    return {
        "id": run_id,
        "provider": cfg["models"].get("provider", "agent"),
        "modes": _modes(),
        "phases": _phases(d),
        "pending": _pending(d),
        "job": job.state() if job else None,
        "brief": (d / "0_brief.json").read_text(encoding="utf-8") if (d / "0_brief.json").exists() else
                 (brief_yaml.read_text(encoding="utf-8") if brief_yaml.exists() else ""),
        "analysis_html": _md(d / "analysis.md"),
        "plan_html": _md(d / "plan.md"),
        "plan_json": plan.read_text(encoding="utf-8") if plan.exists() else "",
        "posts": _posts(d, cfg),
        "cost": costs.get("total_usd", 0),
        "agent_prompt": f"Read RECEPT.md and continue the recipe run {run_id}. Do every agent task yourself, "
                        "stop for my approval after the plan and before delivery.",
    }


def _modes() -> dict:
    return {"claude": bool(claude_path()), "manual": True, "api": bool(os.getenv("ANTHROPIC_API_KEY"))}


def start(run_id: str, action: str, body: dict) -> None:
    d = _run_dir(run_id)
    if _running(run_id):
        raise ValueError("A step is already running for this run.")
    if action == "create":
        if d.exists() and any(d.iterdir()):
            raise ValueError(f"Run '{run_id}' already exists.")
        d.mkdir(parents=True, exist_ok=True)
        p = d / "brief.input.yaml"
        p.write_text(body.get("brief_yaml", ""), encoding="utf-8")
        cmd = _cli("--brief", str(p), "--run", run_id, "--to", "plan", "--yes")
    elif action == "plan":
        brief = d / "brief.input.yaml"
        extra = ["--brief", str(brief)] if not (d / "0_brief.json").exists() and brief.exists() else []
        cmd = _cli(*extra, "--run", run_id, "--to", "plan", "--yes")
    elif action == "produce":
        cmd = _cli("--run", run_id, "--to", "produce", "--yes")
    elif action == "deliver":
        cmd = _cli("--run", run_id, "--from", "deliver", "--yes")
    elif action == "regen":
        post, frame = int(body["post"]), int(body["frame"])
        _forget_frame(d, post, frame)
        cmd = _cli("--run", run_id, "--from", "produce", "--to", "produce", "--yes")
    else:
        raise ValueError(f"Unknown action {action}")
    mode = body.get("mode") or ("claude" if claude_path() else "manual")
    if not _modes().get(mode):
        raise ValueError(f"Mode '{mode}' is not available on this machine.")
    JOBS[run_id] = Job(run_id, action, cmd, mode)


def _forget_frame(d: Path, post: int, frame: int) -> None:
    pd = d / "posts" / f"post_{post}"
    for pat in (f"{frame:02d}.png", f"{frame:02d}_qa.json", f"{frame:02d}_bg.png", f"{frame:02d}_a*.png",
                f"{frame:02d}_scene_a*.png", "reel.mp4"):
        for f in pd.glob(pat):
            f.unlink()
    for f in (d / "agent").glob(f"qa_post{post}_frame{frame:02d}_a*"):
        f.unlink()
    (d / "4_produce.done").unlink(missing_ok=True)


def save_plan(run_id: str, text: str) -> None:
    d = _run_dir(run_id)
    if (d / "4_produce.done").exists():
        raise ValueError("Images are already produced for this plan.")
    plan = ContentPlan.model_validate_json(text)
    (d / "3_plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if ctype.startswith("application/json") else "max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        try:
            if path == "/":
                self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/runs":
                self._json({"runs": run_list()})
            elif path.startswith("/api/runs/"):
                self._json(run_detail(path.split("/")[3]))
            elif path == "/api/modes":
                self._json(_modes())
            elif path == "/api/brief-template":
                self._send(200, (ROOT / "inputs" / "brief.yaml").read_bytes(), "text/plain; charset=utf-8")
            elif path.startswith("/files/"):
                self._file(path.removeprefix("/files/"))
            else:
                self._json({"error": "not found"}, 404)
        except FileNotFoundError:
            self._json({"error": "not found"}, 404)
        except ValueError as e:
            self._json({"error": str(e)}, 400)

    def _file(self, rel: str) -> None:
        p = (ROOT / rel).resolve()
        allowed = [(ROOT / "runs").resolve(), (ROOT / "deliverables").resolve(), (ROOT / "inputs").resolve()]
        if not any(p.is_relative_to(a) for a in allowed) or not p.is_file():
            raise FileNotFoundError(rel)
        self._send(200, p.read_bytes(), mimetypes.guess_type(p.name)[0] or "application/octet-stream")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        parts = path.strip("/").split("/")
        try:
            if len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "save-plan":
                save_plan(parts[2], body["plan_json"])
            elif len(parts) == 4 and parts[:2] == ["api", "runs"]:
                start(parts[2], parts[3], body)
            else:
                return self._json({"error": "not found"}, 404)
            self._json({"ok": True})
        except ValidationError as e:
            self._json({"error": "Plan does not match the schema:\n" + str(e)}, 400)
        except (ValueError, KeyError) as e:
            self._json({"error": str(e)}, 400)


def serve(port: int = 8765, open_browser: bool = True) -> None:
    load_config()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"recept UI on {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
