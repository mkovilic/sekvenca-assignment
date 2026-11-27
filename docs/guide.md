# recept — guide and review

**Brand:** GymBeam Croatia, [instagram.com/gymbeamhr](https://www.instagram.com/gymbeamhr/). It was the suggested brand. It sells mostly own-label products, so there are no third-party trademarks on the packaging. Its Instagram has a clear identity (orange, dark backgrounds) and a habit of trend content.
**Repository:** github.com/mkovilic/sekvenca-assignment · **Results:** `deliverables/` · **Intermediate results:** `examples/gymbeam-demo/`

## How to run it

1. Install [uv](https://docs.astral.sh/uv/). Run `cp .env.example .env` and add `OPENAI_API_KEY`, then run `uv sync`.
2. `uv run recept run --brief inputs/brief.yaml --run my-run`. Leave out `--brief` to get the interactive briefing.
3. The judgement steps run either through **Claude Code** (`provider: agent`, the default, no LLM API cost) or through the **Claude API** (`provider: anthropic`). In agent mode, open Claude Code in the folder and paste the starting prompt from `RECEPT.md`. Claude Code answers the tasks the program writes to `runs/<id>/agent/` and reruns the command.
4. **Human steps:** approve the plan before images are generated, and approve the finished frames before delivery. Both gates are skipped with `--yes`.

5. **Web UI** (simplest): `uv run recept ui`. Everything runs from the browser: the UI calls Claude Code headless for the judgement tasks and stops only at the two approvals (plan editing, frames with QA scores, regenerating a single frame, delivery).

Settings are in `config.yaml`: models, image quality, sizes, brand colours and fonts, QA threshold and number of retries. Docker: see the README.

## Phases

| Phase | Input | What it does | Output |
|---|---|---|---|
| brief | YAML or interactive questions | brand, products (URLs), audience, goals, season, constraints | `0_brief.json` |
| ingest | product URLs, screenshot folder | reads schema.org data and FAQ, downloads the packshot, cuts out the product | `1_ingest.json`, cut-out PNGs |
| analysis | brief, facts, 8 screenshots | tone, style, palette, captions, engagement; verified (with source) vs assumed | `2_analysis.json`, `analysis.md` |
| plan | analysis, facts | 3 posts: goal, format, rationale, frames, facts used | `3_plan.json`, `plan.md` |
| produce | plan, cut-outs | scene → composite → visual QA (up to 2 retries), captions + fact check, reel | `posts/post_N/`, `qa.json` |
| deliver | everything | packages media, captions and `meta.md` | `deliverables/` |

Every phase writes its result to disk, and finished steps are skipped on rerun. An interrupted run resumes with `--run <id>`.

## Key decisions

- **The image model never draws the product or any text.** It generates only the scene. The real packshot is cut out with rembg merged with a flood-fill mask: rembg alone loses the reflective foil on the creatine pouch, and flood-fill alone eats into the white Just Whey label. Text is rendered by Pillow. This guarantees exact labels and correct spelling.
- **Facts come only from the shop's structured data.** The webshop has a small inconsistency: Just Whey's description says "at least 22 g" of protein, while the FAQ says "22.5 g per 30 g scoop". The post uses the exact FAQ figure.
- **Brand style is measured, not guessed.** The colours `#FA762B`, `#20201E` and `#FEF6E2` were sampled from the brand's own carousel. The carousel copies their educational template (dark grid, page numbers, one word in orange).
- **Post 3 continues their own trend.** The GTA-style illustration had 2,147 likes, far more than any other visible post, but no product. The reel keeps the aesthetic, adds the product and a seasonal twist, and uses no game names or logos.
- **Two LLM modes, one set of prompts.** Prompts and schemas are shared, so the Claude Code run and the API run are the same recipe.

## Quality checks and limitations

QA scores every frame (product accuracy, stray text and people, legibility, brand fit). Two reel frames failed the first attempt: the packshot stood *in front of* a drawn pedestal and looked pasted. QA wrote the fix ("no pedestal, open ground"), the scene was regenerated, and the product switched to a die-cut "sticker" style like the brand's cut-out collages. Both frames then passed (`examples/.../qa/`). The lesson went back into the plan prompt: no pedestals for composited products.

**What can vary on a rerun:** the scenes and the exact wording. **What should not vary:** the labels (always the real packshot), the facts, the colours, the fonts and the structure.
**Limitations:** Instagram is not scraped (login wall and terms of use), so screenshots are added by hand and no reach or saves data is available. The font is a close free substitute (Anton/Montserrat). The photo-on-illustration mix is a stylistic compromise. In agent mode the judgement steps depend on the agent model's quality.

**Time:** active work 3 h · waiting for generation ~5 min (6 images + 2 retries, ~30 s each) · AI cost **$0.33** (OpenAI images; the judgement steps ran in Claude Code).

**My own refinement of an AI suggestion:** The AI proposed a generic "retro neon Miami" post and avoided the GTA reference over IP concerns. I found that GymBeam had posted exactly that style a week earlier, and that it was their best-performing post. So I changed the concept to a direct follow-up: same aesthetic, the real product added (their post had none), no people, and a holiday twist.

## Proposed next step: learning from feedback

**Data:** for each published post, store its plan JSON (format, concept, hook, colours, product) together with Instagram Insights after 48 h and 7 days (reach, saves, shares, comments), human approvals and edits (diff between `3_plan.json` before and after approval), and QA failures.
**What changes:** (1) The analysis gets a "what worked" section computed from the brand's own history, not from screenshots. (2) The plan prompt receives the top and bottom 5 past posts as few-shot examples. (3) Recurring human edits become explicit rules, for example "never a pedestal" or "always one emoji per bullet". (4) QA thresholds and the scene-prompt suffixes are tuned from frames that humans rejected.
**How to check it is better:** keep a fixed eval set of briefs and score each recipe version blind, by human preference and with an LLM judge against the brand rubric. Track the QA first-pass rate and cost per approved post. In production, A/B test by alternating the old and new plan versions on similar slots and compare saves per reach after 7 days.
