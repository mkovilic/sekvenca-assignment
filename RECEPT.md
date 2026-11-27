# Recipe runbook for Claude Code (agent mode)

Starting prompt — paste into Claude Code opened in this folder:

> Read RECEPT.md and run the recipe for `inputs/brief.yaml` with run id `my-run`. Do every agent task yourself, stop for my approval after the plan and before delivery.

## What the agent does

The program does everything deterministic (scraping, background removal, image generation calls, compositing,
the reel, packaging). Every step that needs judgement is written to `runs/<id>/agent/<key>.request.md` and the
program stops with exit code 3. The agent answers each request and reruns the same command; finished steps are
never redone.

Loop:

1. `uv run recept run --brief inputs/brief.yaml --run <id> --yes`
   (later iterations: `uv run recept run --run <id> --yes`)
2. If it exits with "Waiting for the agent", open each listed `*.request.md`:
   - follow the **Instructions** section (it is the matching file from `prompts/`),
   - look at every image path listed (Instagram screenshots, finished frames, real packshots),
   - write the JSON answer to the path given under **Output**, matching the schema exactly.
3. Repeat until the program prints `delivered to …/deliverables`.

## Rules for the agent

- **Analysis**: every `verified_facts` entry needs a source (URL or screenshot filename). Inferences go to `assumptions`.
- **Plan**: only facts present in the product data; no people; no game titles/logos/fonts. After writing the plan,
  show `runs/<id>/plan.md` to the human and wait for approval before rerunning (the next run generates images = cost).
- **Image QA** (`qa_post*_frame*`): look at the frame *and* the real packshot. Fail it (`score` < 7 or
  `product_accurate: false`) for warped labels, pasted-looking products, stray text, people. Put a concrete scene-prompt
  change in `fix_for_image_model`; the program regenerates the scene with it (max 2 retries, `config.yaml → qa`).
  If a problem can't be fixed by the scene prompt (e.g. product style), edit `runs/<id>/3_plan.json` and say so.
- **Captions**: brand voice from the analysis, only verified facts, 3–6 hashtags incl. `#gymbeamhr`.
- **Caption QA**: list any product claim not in the verified facts; `ok: false` + corrected caption if needed.
- Before delivery, show the human the frames in `runs/<id>/posts/` and wait for approval.

## Switching to fully automatic

Set `models.provider` in `config.yaml` to `openai` (needs only `OPENAI_API_KEY`, already used for images) or
`anthropic` (needs `ANTHROPIC_API_KEY`). The same prompts and schemas are then sent to that API as structured outputs,
and the program runs end to end without stopping. The web UI (`uv run recept ui`) offers the same choice in its header,
plus "Claude Code (automatic)", which runs `claude -p` headless for each task so nothing has to be pasted.
