# recept

This repo is an AI recipe: Instagram brand -> three finished posts. When the user asks to run the recipe
(or pastes a path to a `runs/<id>/agent/*.request.md` file), follow `RECEPT.md`: run `uv run recept run ...`,
answer every task listed in `runs/<id>/agent/` by writing the JSON file each request names, rerun the same
command, and stop for the user's approval after the plan and before delivery.

Never paste or answer the files in `prompts/` directly — they are embedded in the request files together with
the data and image paths.
