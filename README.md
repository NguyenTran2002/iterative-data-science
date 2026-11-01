# iterative-data-science

`iterative-data-science` is a Claude Code skill for work in Jupyter notebooks. It tells Claude to work in small batches, read every output before moving on, save each figure and open it, and keep text and image output in separate cells.

This repository publishes the skill and an experiment: two autonomous Claude Code runs do the same analysis on the same public data, one with the skill and one without, and every log and notebook is kept so the difference in behavior can be checked.

## Install the skill

As a plugin (the skill is then `/iterative-data-science:iterative-data-science`):

```bash
claude plugin marketplace add <owner>/iterative-data-science
claude plugin install iterative-data-science@iterative-data-science
```

By hand (the skill is then `/iterative-data-science`): copy `plugins/iterative-data-science/skills/iterative-data-science/` into `~/.claude/skills/`, or into a project's `.claude/skills/`.

The skill is one file, [`SKILL.md`](plugins/iterative-data-science/skills/iterative-data-science/SKILL.md), published exactly as the author uses it.

## Findings

Results will appear here after the first pair runs.

## What the experiment shows, and what it does not

- **Behavior, not accuracy.** The experiment counts what each run did: how often it executed the notebook and how many cells at a time, whether it opened its figures, how many errors it hit and left, how much it reworked. It does not grade which analysis is more correct. There is no answer key for interpretive conclusions, and a reference answer written by anyone here would be one more unchecked analysis. Where the two notebooks report different numbers for the same quantity, the difference is traced through each notebook's code to the step where they part ways.
- **One pair.** The first release is one run with the skill and one without. It is a worked example of the difference, not a statistical result. More pairs, tasks and models can be added under the same settings.
- **Autonomous, non-interactive Claude Code.** Each run is Claude Code driven by the Claude Agent SDK with Claude Code's own system prompt preset, which the feasibility probe found identical to `claude -p` and slightly different from the interactive terminal ([probe notes](docs/probe-2026-10-31.md)). No human is in the loop during a run.
- **Model.** Sonnet 5.5 (`claude-sonnet-5-5`) at effort `high` on both sides.
- **Full internet.** Both runs can search and fetch from the web, as a person using Claude Code can. Every search, fetch and package install is listed per side.
- **The agent could see its own log folder.** Each run's container mounts an output folder (`/out`) where the runner writes the message log and notebook snapshots, and the agent's user could read it. The setup is the same on both sides, and no published run touched it (`tool_calls_touching_out` in `metrics.json`).
- **Signed in with a plan token.** The published runs used a Claude plan token. The launcher also accepts an API key; each run records which it used.
- **Designed by the skill's author.** The author wrote the skill and designed this experiment. The next section lists what was done so that the design could not tilt the result.

## How it was kept neutral

- **The only differences between the sides** are the skill file in the workspace and the `/iterative-data-science` prefix on the prompt. Both sides run from the same Docker image, with the same model, settings, caps, data and task, and start within a second of each other.
- **The data week was drawn by code.** One Monday-to-Sunday week of 2023 Chicago taxi trips was chosen by hashing a seed string committed before the draw ([`draw_week.py`](experiment/data/draw_week.py)). The draw is final, and the data is pinned by checksum.
- **The task was written in a clean room.** A separate Claude Opus 5.5 run, with no skill, no web access and no data, wrote the analyst's brief from the dataset's public description alone. Its instructions are published verbatim ([`task_writer.md`](experiment/prompts/task_writer.md)). The first draft that passed fixed form checks (three or four questions, under 400 words, no invented columns, no data access) was used; any rejected draft is kept in `experiment/task/rejected/`.
- **The counts were fixed in advance.** Every behavior count is defined in the [design spec](docs/design/2026-10-31-experiment-design.md) and computed by [`metrics.py`](experiment/analysis/metrics.py), both committed before any run.
- **Every run is published**, whatever it shows. Caps exist only to stop a runaway run (1,000 turns, $100 estimated cost, 4 hours); a run that hits one is analysed like any other. A pair is never rerun because of its result. [`BUILD_LOG.md`](BUILD_LOG.md) records every step as it happened.

## Reproduce it

You need Docker, [uv](https://docs.astral.sh/uv/), and either a Claude plan token (from `claude setup-token`) or an Anthropic API key, exported in your shell as `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`. The launcher passes it to the containers by name and redacts it from every output file.

```bash
cd experiment
uv sync
uv run pytest
```

Fetch the data week (about 61 MB; the script stops if the checksum does not match):

```bash
uv run python -m data.fetch_week
```

Run one pair, then compute the counts:

```bash
uv run python run_pair.py
```

```bash
uv run python -m analysis.metrics ../runs/<run-id>
```

Outputs land in `runs/<run-id>/`: for each side the full message log, the final workspace, every saved version of the notebook, and the run's cost and duration. Each run's estimated cost is in its `result.json`. The image is built for your machine's chip type; `pair.json` records which one was used.

## License

The skill and the code are licensed under [Apache 2.0](LICENSE). The taxi data belongs to the City of Chicago and is used under the [data portal's terms](https://www.chicago.gov/city/en/narr/foia/data_disclaimer.html); it is never stored in this repository.
