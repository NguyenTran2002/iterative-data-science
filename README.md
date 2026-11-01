# iterative-data-science

`iterative-data-science` is a Claude Code skill for work in Jupyter notebooks. It tells Claude to work in small batches, read every output before moving on, save each figure and open it, and keep text and image output in separate cells.

This repository publishes the skill and an experiment. In each pair, two autonomous Claude Code runs do the same analysis on the same public data, one with the skill and one without. Every log and notebook is kept, so the difference in behavior can be checked. This release has five pairs.

## Install the skill

As a plugin (the skill is then `/iterative-data-science:iterative-data-science`):

```bash
claude plugin marketplace add NguyenTran2002/iterative-data-science
claude plugin install iterative-data-science@iterative-data-science
```

By hand (the skill is then `/iterative-data-science`): copy `plugins/iterative-data-science/skills/iterative-data-science/` into `~/.claude/skills/`, or into a project's `.claude/skills/`.

The skill is one file, [`SKILL.md`](plugins/iterative-data-science/skills/iterative-data-science/SKILL.md), published exactly as the author uses it.

## Findings

Five pairs ran on one brief, with Claude Sonnet 5.5 at effort `high`. All ten runs finished on their own, far inside the caps, and every final notebook re-ran from top to bottom in a fresh container.

In all five pairs, the skill changed how Claude worked. With it, Claude added one to three cells at a time, ran them, read the output, and saved and opened each figure before writing the next section. Without it, Claude wrote the whole notebook first, ran it in one go, and reviewed the result at the end. The skill was written for an older Sonnet. The current model produced sound notebooks either way, so what this experiment shows is a change in how Claude works, not a rescue of a weak result.

### The counts

Ranges across the five pairs. Per-pair values are in each run's `metrics.json` and in [`BUILD_LOG.md`](BUILD_LOG.md).

| | Without the skill | With the skill |
|---|---|---|
| Times the notebook was run | 1–5 | 15–23 |
| Largest batch of new cells before a run¹ | 14–20 | 3 |
| Median batch of new cells before a run¹ | 2–17 | 1–2 |
| Cells mixing text and an image | 1–3 | 0 |
| Figure files saved in the workspace | 0² | 4–5 |
| Distinct figure files opened | 5–6 | 4–5 |
| Cell errors left in the final notebook | 0 | 0 |
| Final notebook re-runs in a fresh container | 5 of 5 | 5 of 5 |
| Turns | 21–32 | 33–43 |
| Wall-clock time | 3.6–5.4 min | 6.2–8.1 min |
| Estimated cost (list price) | $0.53–$0.77 | $0.79–$1.20 |
| Web searches, web fetches, package installs | 0 | 0 |

1. Cells are matched by their code text. This measure was added after the runs, because both sides at times rebuilt the notebook with new cell IDs: the side without the skill in every pair, and the side with it in pairs 4 and 5. The pre-registered count matches cells by ID and is also in `metrics.json`; where IDs were regenerated, it counts whole notebooks as new.
2. Every control run saved its figures under `/tmp`, outside the workspace, and opened them there.

The pre-registered rework count (cells changed after they had produced output) also matches cells by ID. Because of the regenerated IDs it can undercount on both sides, and most on the side without the skill, so it is not compared here; the per-run values are in `metrics.json`.

### How each side worked

- **Without the skill**, Claude profiled the data in standalone scripts. It then generated the whole notebook from one build script, often with placeholder prose, and executed it. It extracted the figures to `/tmp` and looked at them, patched plots and prose by string replacement, and ran everything again. In every pair, the first figure it opened came after the whole notebook already existed.
- **With the skill**, Claude also profiled the data first. Then it added one to three cells at a time through a small helper script, ran them, read the new output, and saved each figure under `figures/` and opened it before writing the next section. In several runs it also added checks of its own: `assert` cells, sensitivity checks, and a final fresh-kernel scan.

### What reading the output changed, on both sides

Both sides changed course after reading their outputs, in every pair. Some examples:

- **Without the skill, pair 1:** after viewing its figures at the end, "The revenue-axis tick labels overlap, and the "Mon–Fri" label is clipped at the top" ([log](runs/2026-10-31T2230Z/control/messages.jsonl#L190)). Both were fixed.
- **Without the skill, pair 3:** "correcting a few sentences in the written takeaways that go beyond what the tables show" ([log](runs/2026-10-31T2253Z/control/messages.jsonl#L170)).
- **With the skill, pair 3:** "My R3 rule is flagging plausible long trips as corrupt based on mileage alone, so I'll switch to a fare-per-minute test" ([log](runs/2026-10-31T2253Z/skill/messages.jsonl#L250)). This was an exclusion rule, changed before later sections were built on it.
- **With the skill, pair 1:** it found prepaid-card tips are "barely recorded … my earlier assumption was wrong", and narrowed the card-only tip comparison ([log](runs/2026-10-31T2230Z/skill/messages.jsonl#L376)).

The difference is when the checking happened. Without the skill, the review came once the notebook was complete. With the skill, the checks happened while the notebook was being built, so some of them changed choices that later cells depended on.

### Defects left in the final notebooks, on both sides

- **Without the skill:**
  - **Prose that contradicts the tables.** Some statements disagree with the notebook's own tables. For example, pair 1, cell 27 says area 33 ranks higher by revenue than by trips; its tables show it 5th by trips and 6th by revenue.
  - **One code bug.** In pair 1, 11 trips with a missing duration are excluded by the speed rule, although the prose says such rows are kept.
  - **Figures never opened.** In four of the five pairs, one or two figures were never opened.
  - **Mixed cells.** One to three cells per run mix text and an image.
- **With the skill:**
  - **Helper-script defects.** In pairs 1 and 2, the helper left `# ` in front of every line of 11 markdown cells, so they render as headings. The helper never displayed markdown, so the agent never saw this. In pair 4 the same bug was caught and fixed ([log](runs/2026-10-31T2302Z/skill/messages.jsonl#L491)).
  - **A correction that silently failed.** In pair 5 the edit did not apply, yet the final message reports it as made ([log](runs/2026-10-31T2310Z/skill/messages.jsonl#L428)). Cell 17 still says area 56 is "7th by trips"; its table shows 6th.
  - **Prose that contradicts the tables.** A few prose figures disagree with the notebook's own tables. For example, in pair 3 the prose says 11.2% where the table shows 11.1%.

### Where the numbers differ

The same six quantities were compared between the two sides of every pair: the analysis set, the share of trips with no pickup area, the busiest weekday hour, the top company's share, the card tip as a percentage of fare, and the top payment type. No headline differs between sides in any pair: 17:00, Flash Cab at about 19% of trips, Credit Card at about 44.5%, and card tips at about 22% of fare.

Every numeric difference traces to a cleaning choice. In pair 1, the side without the skill excluded 629 trips and the side with it 636; of their exclusion rules, they shared only one, for the 324 rows with missing money fields. In pair 4, the side without the skill dropped flagged rows from every analysis, while the side with it kept all rows for counts and filtered only the dollar figures. Apart from the one bug above, each difference is a choice, not an error.

### Where the skill came from

The SKILL.md says Claude cannot see inline notebook renders. That is the observation the skill was written from, with an older model. In these runs, every figure either side looked at came from a saved image file; neither side viewed figures through the notebook (`images_seen_by_source` in `metrics.json`).

## What the experiment shows, and what it does not

- **Behavior, not accuracy.** The experiment counts what each run did: how often it executed the notebook and how many cells at a time, whether it opened its figures, how many errors it hit and left, and how much it reworked. It does not grade which analysis is more correct. There is no answer key for interpretive conclusions, and a reference answer written by anyone here would be one more unchecked analysis. Where the two notebooks report different numbers for the same quantity, the difference is traced through each notebook's code to the step where they part ways.
- **Five pairs, one task.** The first pair was the planned release. Four more were held in reserve in case it hit unforeseen errors, and they ran after it completed. Together they are a worked example repeated five times, not a statistical result. More tasks and models can be added under the same settings.
- **Autonomous, non-interactive Claude Code.** Each run is Claude Code driven by the Claude Agent SDK with Claude Code's own system-prompt preset. The feasibility probe found that preset identical to `claude -p` apart from one billing header line, and slightly different from the interactive terminal ([probe notes](docs/probe-2026-10-31.md)). No human is in the loop during a run.
- **Model.** Sonnet 5.5 (`claude-sonnet-5-5`) at effort `high` on both sides.
- **Full internet.** Both runs can search and fetch from the web, as a person using Claude Code can. Every search, fetch and package install is listed per side; there were none.
- **The agent could see its own log folder.** Each run's container mounts an output folder (`/out`) where the runner writes the message log and notebook snapshots, and the agent's user could read it. The setup is the same on both sides, and no published run touched it (`tool_calls_touching_out` in `metrics.json`, a measure added after the runs).
- **Signed in with a plan token.** The published runs used a Claude plan token. The launcher also accepts an API key; each run records which it used.
- **Designed by the skill's author.** The author wrote the skill and designed this experiment. The next section lists what was done so that the design could not tilt the result.

## How it was kept neutral

- **The only differences between the sides** are the skill file in the workspace and the `/iterative-data-science` prefix on the prompt. Within a pair, both sides run from the same Docker image build, with the same model, settings, caps, data and task, and start within a second of each other. A system-prompt check confirmed that both sides receive the same system prompt, and that the skill text reaches only the skill side.
- **The data week was drawn by code.** One Monday-to-Sunday week of 2023 Chicago taxi trips was chosen by hashing a seed string committed before the draw ([`draw_week.py`](experiment/data/draw_week.py)). The draw is final, and the data is pinned by checksum.
- **The task was written in a clean room.** A separate Claude Opus 5.5 run, with no skill, no web tools and no data, wrote the analyst's brief. It worked from the dataset's public description and a description of the analyst's working environment. Its instructions are published verbatim ([`task_writer.md`](experiment/prompts/task_writer.md), [`environment.md`](experiment/prompts/environment.md)).
  - Under the first instructions, all five drafts failed the length check, because the instructions did not state the limits the drafts were checked against.
  - The author then gave the writer the environment description and stated those limits: three or four questions, under 500 words.
  - The first draft under the amended setup passed and was used. All five rejected drafts are kept in [`experiment/task/rejected/`](experiment/task/rejected/).
  - Both sides of every pair received the same column description the writer saw.
- **The counts were fixed in advance.** Every pre-registered count is defined in the [design spec](docs/design/2026-10-31-experiment-design.md) and computed by [`metrics.py`](experiment/analysis/metrics.py), both committed before any run. Measures added after the runs are kept apart, under `added_after_runs`.
- **Every run is published**, whatever it shows. Caps exist only to stop a runaway run: 1,000 turns, $100 estimated cost and 4 hours per side. A run that hits one is analysed like any other, and a pair is never rerun because of its result. [`BUILD_LOG.md`](BUILD_LOG.md) records each step, decision and correction in order.

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

Run one pair (it builds the image first), then compute the counts for it:

```bash
uv run python run_pair.py
```

```bash
uv run python -m analysis.metrics ../runs/<run-id>
```

The metrics step re-executes both final notebooks in fresh containers; add `--no-reexecute` to skip that. It needs the raw request bodies that a run keeps in its git-ignored `private/` folders, so it works on runs you made yourself, not on the published runs.

Outputs land in `runs/<run-id>/`. For each side that is the full message log, the final workspace, every saved version of the notebook, and the run's cost and duration; each run's estimated cost is in its `result.json`. The image is built for your machine's chip type, and `pair.json` records which one was used. The published runs used `arm64`.

## License

The skill and the code are licensed under [Apache 2.0](LICENSE). The taxi data belongs to the City of Chicago and is used under the [data portal's terms](https://www.chicago.gov/city/en/narr/foia/data_disclaimer.html); it is never stored in this repository.
