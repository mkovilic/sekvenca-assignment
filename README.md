# recept — from an Instagram brand to three finished posts

A reproducible AI recipe: **brief → ingest → brand analysis → content plan → production + QA → delivery**.
Demo brand: GymBeam Croatia ([@gymbeamhr](https://www.instagram.com/gymbeamhr/)).

Finished posts are in [`deliverables/`](deliverables), and the intermediate results of the demo run are in [`examples/gymbeam-demo/`](examples/gymbeam-demo).
Instructions and the write-up are in [`docs/guide.pdf`](docs/guide.pdf).

| | Format | Goal |
|---|---|---|
| [Post 1](deliverables/post_1) | Carousel, 6 slides | Education → saves |
| [Post 2](deliverables/post_2) | Single image | Product → purchase intent |
| [Post 3](deliverables/post_3) | Reel, 13 s | Trend → comments |

## Quick start

```bash
# needs uv (https://docs.astral.sh/uv/); Python 3.12 is installed by uv
cp .env.example .env          # add OPENAI_API_KEY
uv sync
```

The judgement steps (analysis, plan, captions, QA) need an LLM. There are three backends, all using the same prompts and schemas:

| `models.provider` | Runs on | Needs | LLM cost per run |
|---|---|---|---|
| `agent` (default) | Claude Code | a Claude Code login | none (your subscription) |
| `openai` | OpenAI API (`gpt-5.5`, captions `gpt-5.4-mini`) | only `OPENAI_API_KEY` | roughly $0.5 |
| `anthropic` | Claude API (Opus 5.5, captions Sonnet 5.5) | `ANTHROPIC_API_KEY` | roughly $0.5 |

Images always use the OpenAI API (`gpt-image-2.5-sunburst`, about $0.30 per run; the demo run cost **$0.33**, see `costs.json`).

**Easiest: the web UI.** `uv run recept ui` opens http://127.0.0.1:8765. Write the brief, pick the backend in
"Judgement steps" (Claude Code automatic, OpenAI API or Claude API) and press Start. The UI runs every step on its own;
in Claude Code mode it calls `claude -p` headless with your login. It stops only at the two approvals: edit and approve
the plan, then review every frame with its QA score, regenerate single frames and approve delivery.

**Terminal, fully automatic:** set `models.provider: openai` (or `anthropic`) in `config.yaml`, then

```bash
uv run recept run --brief inputs/brief.yaml --run my-run
```

**Terminal, with Claude Code:** keep `provider: agent`, open Claude Code in this folder (`claude`) and paste:

```
Read RECEPT.md and run the recipe for inputs/brief.yaml with run id my-run. Do every agent task yourself, stop for my approval after the plan and before delivery.
```

The program writes each judgement task to `runs/<id>/agent/*.request.md` and stops; Claude Code answers and reruns it.
Do not paste the files from `prompts/` by hand: they are already included in every request file, together with the data.

Useful flags: `--latest` (resume the last run), `--from <phase>` / `--to <phase>`, `--only-post N`, `--yes` (skip approval gates).
Without `--brief` the program runs an interactive briefing.

Docker: `docker build -t recept . && docker run --env-file .env -v $PWD/runs:/app/runs -v $PWD/deliverables:/app/deliverables recept`

## How it works

```
inputs/brief.yaml ─► brief ─► ingest ─────────► analysis ─► plan ──[human OK]──► produce ───────────► deliver
                              schema.org data   screenshots  3 posts,            scene (OpenAI)        deliverables/
                              FAQ, packshot     + facts      frames, facts       + real packshot       caption.txt
                              cutout (rembg)    → JSON        → JSON              + text (Pillow)       meta.md
                                                                                  → QA (vision) ↺ ×2
                                                                                  → reel (ffmpeg)
```

Each phase saves a Pydantic-validated JSON file in `runs/<id>/`. Any phase can be resumed or hand-edited, for example by editing `3_plan.json`.

**Same recipe on every backend:** `src/recept/llm.py` has one `structured()` contract (text + images in, a Pydantic
object out) implemented by `AgentLLM` (Claude Code), `Claude` (Anthropic API) and `OpenAILLM` (OpenAI Responses API).

**Why the products stay accurate:** the image model never draws the product or any text. It only generates the
background scene. The real packshot from the webshop is cut out (rembg merged with a flood-fill mask, so both
reflective foil and white labels survive) and composited by code. Headlines are rendered in a font close to the brand's,
using colours measured from the brand's own posts. QA compares every frame with the real packshot. A failing frame is
regenerated with a corrected prompt, up to 2 times.

**Why the facts are true:** product claims come only from the shop's structured data and FAQ (`1_ingest.json`). The plan
lists the facts each post uses, and a separate caption QA step checks the caption and on-image text against them.

## Layout

```
config.yaml        models, prices, formats, brand style, QA thresholds
inputs/            brief.yaml + Instagram screenshots
prompts/           the prompt for every judgement step (used in both modes)
src/recept/        cli, phases/, render/ (cutout, compose, reel), ui/ (web UI), llm.py, images.py, costs.py, schemas.py
deliverables/      the three posts
examples/          intermediate results of the demo run
docs/              guide (md + pdf)
tests/             uv run pytest
```
