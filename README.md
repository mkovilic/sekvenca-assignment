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

Needs [uv](https://docs.astral.sh/uv/) (it installs Python 3.12) and an OpenAI API key.

```bash
cp .env.example .env          # add OPENAI_API_KEY
uv sync
uv run recept ui              # opens http://127.0.0.1:8765
```

In the browser:

1. **New run**: the brief is prefilled with the GymBeam demo, edit it or keep it.
2. **Judgement steps** (top right): pick who does analysis, plan, captions and QA (see the table below), then press **Start**.
3. **Approve the plan**: read it, edit it if you want, then approve. Image generation starts only now.
4. **Review the posts**: every frame shows its QA score; regenerate any frame you don't like.
5. **Approve delivery**: posts, captions and `meta.md` go to `deliverables/`.

Everything between the two approvals runs on its own.

| Judgement steps | Runs on | Needs | LLM cost per run |
|---|---|---|---|
| Claude Code (automatic) | Claude Code, headless (`claude -p`) | Claude Code installed and logged in | none (your subscription) |
| OpenAI API | `gpt-5.5`, captions `gpt-5.4-mini` | only `OPENAI_API_KEY` | roughly $0.5 |
| Claude API | Opus 5.5, captions Sonnet 5.5 | `ANTHROPIC_API_KEY` | roughly $0.5 |

Images always use the OpenAI API (`gpt-image-2.5-sunburst`, about $0.30 per run; the demo run cost **$0.33**, see `costs.json`).

### Optional: terminal

The UI runs the same CLI underneath. Set the backend in `config.yaml` (`models.provider`: `agent` = Claude Code,
`openai`, `anthropic`) and run:

```bash
uv run recept run --brief inputs/brief.yaml --run my-run
```

With `openai` or `anthropic` it runs to the end, asking only at the two approvals. With `agent` (the default) it stops at
every judgement task; open Claude Code in this folder (`claude`) and paste:

```
Read RECEPT.md and run the recipe for inputs/brief.yaml with run id my-run. Do every agent task yourself, stop for my approval after the plan and before delivery.
```

Do not paste the files from `prompts/` by hand: they are already included in every request file, together with the data.

Flags: `--latest` (resume the last run), `--from <phase>` / `--to <phase>`, `--only-post N`, `--yes` (skip approvals).
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
