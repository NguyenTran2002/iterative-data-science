# Design: a with-and-without experiment for the `iterative-data-science` skill

Date: 2026-10-31. Status: approved by the author before the build began.

## 1. Purpose and the claim it supports

This repository publishes the `iterative-data-science` Claude Code skill and an experiment that shows how Claude Code behaves on the same data-analysis task with and without it.

The claim is about **behavior**, not accuracy. The skill tells Claude to work in small batches, read every output, save every plot and open it, and keep text and image output in separate cells. The experiment shows whether and how that behavior differs, and what followed from it. It does not grade which analysis is more correct: there is no answer key for interpretive conclusions, and any reference answer we wrote would be one more unchecked analysis.

The experiment is neutral. The skill's author designed it, and the README says so. Everything that could tilt it is either decided by a rule fixed in advance (the data week), produced by a clean-room run that never sees the skill (the task), or measured mechanically from logs (the behavior counts). Every run ever made is published, whatever it shows.

The first release is **one pair**: one run with the skill and one without, launched together. It is a worked example of the difference, not a statistical result. More pairs, tasks and models can be added later under the same frozen settings.

## 2. Decisions

| Topic | Decision |
|---|---|
| Comparison | One run with the skill, one without; the only differences are the skill folder and the `/iterative-data-science` prefix on the prompt |
| Skill activation | Called by name. The slash command inlines the whole SKILL.md into the first request, before the model writes anything (verified, §11) |
| Model | Sonnet 5.5 (`claude-sonnet-5-5`), effort `high`, both sides |
| Mode | Autonomous. No human in the loop during a run |
| Runner | Claude Agent SDK (Python) inside the container, `claude_code` system-prompt preset |
| Isolation | One fresh Docker container per run, from one image shared by both sides |
| Internet | Full access, as a normal user has. Both sides of a pair start within a second of each other |
| Sign-in | A Claude plan token (`CLAUDE_CODE_OAUTH_TOKEN`) for the published runs. The launcher also accepts `ANTHROPIC_API_KEY`. Each run records which it used |
| Data | Chicago Taxi Trips 2013–2023 (portal ID `wrvz-psew`), one Monday-to-Sunday week of 2023 drawn by a committed seed |
| Task | Written by a clean-room Opus 5.5 run (effort `high`) that sees the dataset's public description and columns, never the data or the skill |
| Scoring | Behavior counts from logs and notebooks, consequences quoted from the logs, disagreements traced to their cause in code. No rubric, no judge, no accuracy grading |
| Pairs | One pair first. More only by explicit decision, all published |
| Caps | Runaway guards only (§6). Hitting one is a result, never a reason to rerun |
| License | Apache 2.0 for the skill and the code. The taxi data stays under the City of Chicago portal's terms and is never stored in the repo |

## 3. Data

**Dataset.** Taxi Trips (2013-2023), `wrvz-psew` on the City of Chicago data portal. Its rows were last updated 2024-02-07, so a pinned query returns the same rows over time. A probe week downloaded twice gave identical SHA-256 checksums (§11). 2023 averages about 125,000 trips a week.

**Drawing the week.** `experiment/data/draw_week.py`:

1. Lists the Monday-to-Sunday weeks that lie fully inside 2023. 2023-01-01 is a Sunday and 2023-12-31 is a Sunday, so these are the 52 weeks from Mon 2023-01-02 to Sun 2023-12-31.
2. Drops the first (2023-01-02 to 01-08) and the last (2023-12-25 to 12-31), leaving 50 candidates, indexed 0 to 49 in date order.
3. Picks index `int(sha256(SEED).hexdigest(), 16) % 50` with the seed string fixed here:

   `SEED = "chicago-taxi-2023-week/2026-10-31"`

   SHA-256 is used instead of a random-number generator so the result cannot change across Python versions.
4. Prints the chosen week and writes it to `experiment/data/week.json`.

The script runs once, after this spec is committed. Its output is final: no redraws, no seed changes.

**Fetching.** `experiment/data/fetch_week.py` downloads the drawn week through the portal's SODA API as CSV:

- filter: `trip_start_timestamp between '<Mon>T00:00:00' and '<Sun>T23:59:59'`
- order: `trip_id`, so row order is fixed
- one request with a limit far above the expected row count, then an assertion that the row count is below the limit

It records the row count, byte size and SHA-256 in `week.json`. The CSV itself is not committed (about 55–70 MB); the checksum is, and the script refuses to continue if a later download does not match. Downloads take minutes (100–250 s for the probe week), so the script says so and retries on failure.

**What the runs see.** The CSV is copied into each workspace as `trips.csv`, unchanged.

## 4. The image and the runner

**Image** (`experiment/Dockerfile`), one image for both sides and for the task writer:

- Python base image with `uv`, and two separate environments so an agent's `pip install` can never touch the runner: `/opt/runner/.venv` holds `claude-agent-sdk==0.2.176` (the version the probe verified; it bundles Claude Code 2.1.316 and ships Linux wheels for both chip types); `/opt/venv`, owned by `analyst` and first on the agent's `PATH`, holds pandas, numpy, matplotlib, seaborn, scipy, statsmodels, scikit-learn, jupyter, nbconvert and ipykernel at exact versions compiled into `experiment/requirements/analysis.txt`.
- Claude Code is the build bundled inside the pinned `claude-agent-sdk` wheel, so one pin fixes both. `DISABLE_AUTOUPDATER=1` is set.
- The agent runs as the non-root user `analyst` in `/home/analyst/work`. The runner lives in `/opt/runner` and never names the skill. Outputs go to `/out`, mounted from the host.
- Built for the host's chip type, which `pair.json` and the README record.

**Runner** (`experiment/runner/run.py`), started by the container's entrypoint with a role and a prompt file:

```python
ClaudeAgentOptions(
    model=..., effort="high",
    system_prompt={"type": "preset", "preset": "claude_code"},
    setting_sources=["project"],
    permission_mode="bypassPermissions",   # the container is the confinement
    cwd="/home/analyst/work",
    max_turns=..., max_budget_usd=...,
    env={"CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT": "1", "DISABLE_AUTOUPDATER": "1",
         "CLAUDE_CODE_ENABLE_TELEMETRY": "1", "OTEL_LOGS_EXPORTER": "none",
         "OTEL_METRICS_EXPORTER": "none", "OTEL_LOG_RAW_API_BODIES": "file:/out/private/bodies"},
)
```

- `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT=1` pins the shorter system prompt, which is Sonnet 5.5's default, so a server-side experiment cannot switch it between runs.
- The workspace is not a git repository and has no CLAUDE.md.
- Each message is appended to `/out/messages.jsonl` as it arrives. A cap is caught (the SDK raises `ResultError` on `error_max_turns`) and recorded; the log stays intact.
- The process environment is built from scratch, never inherited from a parent Claude Code session (the probe found inherited variables such as `ANTHROPIC_BASE_URL`).

**The two sides.**

| | Control | Skill |
|---|---|---|
| Workspace | `trips.csv` | `trips.csv`, `.claude/skills/iterative-data-science/SKILL.md` |
| Prompt | wrapper + brief | `/iterative-data-science ` + wrapper + brief |

The SKILL.md copied in is the plugin's copy in this repository (§8). Its SHA-256 is recorded with the run.

**What each run keeps**, under `runs/<run-id>/<side>/`:

- `messages.jsonl`: the full SDK message stream
- `init.json`: Claude Code version, model, skills, plugins and tools that loaded
- `result.json`: status, whether a cap was hit, turns, duration, estimated cost, token usage, sign-in method
- `workspace/`: the final workspace (notebook, figures, any other files), without `trips.csv`
- `packages.txt`: `pip freeze` of `/opt/venv` at the end of the run
- `snapshots/`: every distinct version of `analysis.ipynb`, numbered, with the time it was seen (§7)
- `system_prompt.txt` and its SHA-256, extracted from the first main-thread request

`/out/private/` holds the raw API request bodies. They contain account and device IDs, so they are copied to `runs/<run-id>/<side>/private/`, which `.gitignore` excludes, and are used only to extract `system_prompt.txt` and to check the two sides received the same one.

**Credential scrub.** The sign-in variable is in the container's environment, so an agent that prints its environment could put it in a log or notebook. Before the launcher writes anything into `runs/`, it scans every output file for the sign-in value, redacts any match, and records in `pair.json` how many it redacted. The value itself is never written anywhere.

**Launcher** (`experiment/run_pair.py`), on the host:

1. Checks the data checksum and that a sign-in variable is set (without printing it).
2. Builds the image.
3. Prepares both workspaces in fresh temporary folders with neutral names.
4. Starts both containers back to back with `docker run -d`, recording each start time.
5. Waits for both, then copies outputs into `runs/<run-id>/` and writes `runs/<run-id>/pair.json` (start times, image ID, versions, data checksum, skill checksum).

`<run-id>` is the UTC start time, for example `2026-11-02T1530Z`.

## 5. The clean-room task writer

It runs through the same image and runner with three differences: model `claude-opus-5-5` at effort `high`, no skill, and `disallowed_tools=["WebSearch", "WebFetch"]`.

**What it sees.** Its workspace holds one file, `dataset.md`, generated by `experiment/data/dataset_md.py` from the portal's metadata API (`/api/views/wrvz-psew.json`):

- the dataset's public description, verbatim
- every column's name, type and portal description, verbatim
- the drawn week's dates and row count
- the file name the analyst will receive, `trips.csv`

No rows.

**Its instructions** (`experiment/prompts/task_writer.md`, published verbatim):

> `dataset.md` describes one week of Chicago taxi trip records. Write `brief.md`: the brief a manager would hand to a data analyst for this data. Include three or four routine business questions that can be answered from the listed columns. Scope it so a competent analyst can finish in one sitting of about two to three hours. Use only the files in this folder.

**Acceptance checks**, applied to the first draft and to each redraw:

1. `brief.md` exists and contains three or four questions.
2. It is under 400 words.
3. It names no column that is not in `dataset.md`.
4. Its log shows no access to the data: no fetch of the portal's data endpoints and no download of trip rows.

The first draft that passes is final and is committed as `experiment/task/brief.md`. A failing draft is kept under `experiment/task/rejected/` with the check it failed, and the writer runs again from scratch. Nobody judges whether a passing brief is good.

**The wrapper** both sides receive before the brief (`experiment/prompts/wrapper.md`):

> The data is in `trips.csv` in this folder. Do the analysis in a Jupyter notebook named `analysis.ipynb` in this folder.

It says where the data is and what to produce, nothing about executing or checking.

## 6. Running the experiment

Order, each step committed before the next:

1. This spec.
2. The drawn week (`week.json`, with checksum).
3. The accepted brief, its rejected drafts if any, and the task writer's run record.
4. A system-prompt check with the real image: one trivial prompt per side, confirming both sides get the same system prompt and that the skill side's first request contains the SKILL.md. Cost: cents.
5. The pair.

**Caps**, the same on both sides and set only to stop a runaway run: `max_turns=1000`, `max_budget_usd=100` (the SDK's list-price estimate), and a 4-hour wall clock enforced by the launcher. A run that hits a cap is recorded with its status and analysed like any other.

**Green light.** Every paid step (the task writer, the system-prompt check, the pair) runs only after the author's explicit go-ahead.

**No reruns.** A pair is never rerun because of its result. If the setup itself fails (an image that will not build, a sign-in error before the first model turn), the failure is recorded in the build log and the pair is started again; that is the only exception.

## 7. Analysis

`experiment/analysis/metrics.py` computes the counts below for each side from `messages.jsonl` and the final workspace and writes `runs/<run-id>/metrics.json`. The definitions are fixed here, before any run.

**Behavior counts**

Agents edit notebooks in many ways (the probe's agent rewrote the JSON from a Bash heredoc), so the log alone cannot show the notebook's history. The runner therefore snapshots `analysis.ipynb` every time its content changes, polling once a second from outside the agent's process, into `/out/snapshots/`. Nothing about this reaches the agent's context. The counts below that need history use those snapshots.

- **Executions:** snapshots in which any code cell's outputs or execution count changed from the previous snapshot. For each, the number of code cells added or whose source changed since the previous execution (batch size).
- **Mixed output cells:** code cells in the final notebook whose outputs include both text and an image.
- **Figures:** image files created in the workspace; how many distinct ones the agent opened with the Read tool; and the number of inline image outputs in the final notebook.
- **Errors:** tool calls that returned an error; code cells in the final notebook with an error output.
- **Rework:** code cells (matched by cell ID) whose source changed after they had outputs in an earlier snapshot. A notebook rewritten with new cell IDs undercounts this; the README says so if it happens.
- **Fresh re-execution:** whether the final `analysis.ipynb` runs from top to bottom without error in a fresh container from the same image (run by the analysis step, not by the agent).
- **Cost and effort:** turns, wall-clock duration, estimated cost, input and output tokens.
- **Outside activity:** every web search, web fetch and package install, listed per side. If the control side ever reached this repository or the skill text, that is reported, and the run is kept.

**Consequences** (written by hand, every claim quoted from the log): moments where reading an output changed the next step, and visible defects left in the final notebook (an empty or unreadable figure, a table of NaNs, text that describes a figure wrongly). Both sides get the same treatment.

**Disagreements:** where the two notebooks report different values for the same quantity, the difference is traced through each notebook's own code to the step where they part ways, and stated as a fact about the code ("A dropped zero-mile trips before averaging; B did not"). One side is called wrong only for a bug anyone can see once it is pointed out. Otherwise the README states the difference, its cause, and that we cannot say which choice is right.

**System prompt:** the two sides' `system_prompt.txt` files compared. The README states whether they matched.

## 8. Repository layout

```
README.md                         results first, then install, then how to reproduce
LICENSE
BUILD_LOG.md                      append-only log of the build and every run
.claude-plugin/marketplace.json   this repo as a one-plugin marketplace
plugins/iterative-data-science/
  .claude-plugin/plugin.json
  skills/iterative-data-science/SKILL.md     the skill, single source of truth
experiment/
  Dockerfile  pyproject.toml  uv.lock          host tooling and tests
  requirements/runner.txt  requirements/analysis.in  requirements/analysis.txt   image pins
  runner/                         copied into the image as /opt/runner
  launch/                         host-side helpers for the scripts below
  run_pair.py  run_task_writer.py
  tests/
  data/draw_week.py  data/fetch_week.py  data/dataset_md.py  data/week.json
  prompts/task_writer.md  prompts/wrapper.md
  task/brief.md  task/rejected/
  analysis/metrics.py  analysis/compare_system_prompts.py
runs/<run-id>/
  pair.json  metrics.json
  control/  skill/                as listed in §4
docs/
  design/                         this design and the implementation plan
  probe-2026-10-31.md             what the feasibility probe established (§11)
```

**The skill** is published byte for byte as the author uses it. Installing:

- as a plugin: `claude plugin marketplace add <owner>/iterative-data-science` (the GitHub owner is filled in when the repository is published), then `claude plugin install iterative-data-science@iterative-data-science`. The skill is then `/iterative-data-science:iterative-data-science`.
- by hand: copy `plugins/iterative-data-science/skills/iterative-data-science/` into `~/.claude/skills/` (or a project's `.claude/skills/`). The skill is then `/iterative-data-science`.

`claude plugin validate .` must pass before publishing.

**README**, in this order:

1. What the skill is, in two sentences, and how to install it.
2. The pair's findings: a side-by-side table of the behavior counts, then the consequences and disagreements, each linked to the exact log lines and notebook cells.
3. What the experiment does and does not show: behavior, not accuracy; one pair; autonomous runs using Claude Code's non-interactive setup (identical system prompt to `claude -p`), not the interactive terminal; full internet; signed in with a plan token; the skill's author designed it.
4. How it was kept neutral: the drawn week, the clean-room brief, the counts fixed in advance, every run published.
5. How to reproduce: Docker, a plan token or API key, `fetch_week.py`, `run_pair.py`, the expected cost per run.
6. License: Apache 2.0 for the skill and code; the data is the City of Chicago's, under its portal's terms.

The SKILL.md says Claude cannot see inline notebook renders. The README presents that as the observation the skill was written from, not as current Claude Code behavior, and the experiment's figure counts are the evidence either way.

## 9. Working method

- `BUILD_LOG.md` is append-only and written as the work happens; times come from `date`, counts from scripts.
- The task writer's instructions, the wrapper and every clean-room prompt are published verbatim.
- No paid run without the author's go-ahead. The agent never reads `.env` or any credential file, and never prints a token.
- Public text refers to "the author", never "the user".
- `docs/probe-2026-10-31.md` summarizes the feasibility probe without its raw request bodies.

## 10. Out of scope for the first release

- More pairs, other tasks, other datasets, other models (Opus), and the "left for Claude to load" setup. The layout leaves room for them under `runs/` and `experiment/task/`.
- Accuracy grading, rubrics and judges.
- Enforcing the skill's rules with hooks.

## 11. What the feasibility probe established (2026-10-31)

Run on the author's machine with throwaway scripts; raw API request bodies captured with `OTEL_LOG_RAW_API_BODIES`.

- With the same Claude Code build, the SDK with the `claude_code` preset sends a system prompt identical to `claude -p` (only a billing header line differs). Both identify as "a Claude agent, built on Anthropic's Claude Agent SDK".
- Interactive `claude` differs: it identifies as Claude Code, adds the `AskUserQuestion` tool, a tip about `!` shell commands, an end-conversation note, different Bash and Agent tool descriptions, and a section from a locally installed browser extension. None concerns notebooks or checking work.
- The SDK's bundled Claude Code (2.1.316) differed by one system-prompt line from the installed 2.1.309, and the installed copy auto-updated during the probe. Hence the pinned version and `DISABLE_AUTOUPDATER`.
- Sonnet 5.5 gets the shorter system prompt by default (about 6,900 characters); the full one is about 28,000.
- Without `setting_sources=["project"]`, the SDK loaded the author's user settings, and an installed plugin injected about 24,000 characters of instructions. With it, none did.
- The working folder's path appears in the prompt, so run folders must not contain the skill's name, and must not sit inside this repository.
- An agent that could not find its data file searched the machine's temp folder and the home directory. Hence containers.
- The skill loads from a project's `.claude/skills/` folder and through the SDK's `plugins` option. Called by name, its full text is in the first request; with a trivial prompt and no slash command it was not loaded.
- A small notebook task with the skill: 11 turns, 58 seconds, $0.14 estimated. The agent executed the notebook with `jupyter nbconvert`, opened its saved PNG (the image reached the model), and caught a planted 999 °F value.
- On the author's machine, plan sign-in added account context to the conversation (the account's email address and the global git user name). Inside the container there is no git configuration; the system-prompt check (§6, step 4) records what account context remains. Whatever it is, it is the same on both sides.

## 12. Amendments

**2026-10-31, after five rejected brief drafts (author's decision).** All five drafts from the original setup failed the length check (682 to 912 words), because the writer's instructions never stated the limits it was checked against. Its brief also pointed the analyst to `dataset.md`, which the analyst's folder did not hold. The author judged that the writers of the experiment, not the clean-room writer, had left out the practical facts a real brief carries. Changed before any further draft:

- The writer's folder also holds `environment.md` (`experiment/prompts/environment.md`). It states the facts of the analyst's setup: one folder with `trips.csv` and `dataset.md`, Python 3.13 and the installed packages, internet access, `analysis.ipynb` as the deliverable, and no one available for questions. It says nothing about who the analyst is or how to work, so it cannot overlap the skill.
- The writer's instructions now name `environment.md`, and state the limits the checks enforce: three or four questions, under 500 words. The word check moves from 400 to 500 to leave room for the logistics.
- A question is now counted only where a numbered item or heading contains a question mark, so numbered deliverables no longer count.
- Both sides of the pair get the same `dataset.md` the accepted brief's writer saw (`experiment/task/dataset.md`), next to `trips.csv`.
- The five earlier drafts stay published as rejected under the original setup.
