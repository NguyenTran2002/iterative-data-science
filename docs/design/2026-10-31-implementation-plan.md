# Skill Behavior Experiment Implementation Plan

**Goal:** Publish the `iterative-data-science` skill as a Claude Code plugin and build, then run, a neutral one-pair experiment comparing Claude Code's behavior on the same notebook task with and without the skill.

**Architecture:** One Docker image holds Claude Code (bundled in a pinned Agent SDK), a generic SDK runner, and a separate data-science environment. Host scripts draw and fetch one week of Chicago taxi data, generate a brief through a clean-room Opus run, launch the two sides in parallel containers, scrub credentials, and compute behavior counts from logs and notebook snapshots.

**Tech Stack:** Python 3.13, `claude-agent-sdk==0.2.176`, Docker, uv, pytest, nbformat, Jupyter/nbconvert, Socrata SODA API.

**Spec:** `docs/design/2026-10-31-experiment-design.md` (read it first; this plan argues from it).

**Review:** before Task 10 (the first paid step), the whole branch is reviewed once, in a fresh session.

## Global Constraints

- Models: sides `claude-sonnet-5-5`, task writer `claude-opus-5-5`; effort `"high"` for both.
- `system_prompt={"type": "preset", "preset": "claude_code"}`, `setting_sources=["project"]`, `permission_mode="bypassPermissions"`, `cwd="/home/analyst/work"`.
- Runner env pins: `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT=1`, `DISABLE_AUTOUPDATER=1`, `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_LOGS_EXPORTER=none`, `OTEL_METRICS_EXPORTER=none`, `OTEL_LOG_RAW_API_BODIES=file:/out/private/bodies`.
- Caps, same on both sides: `max_turns=1000`, `max_budget_usd=100`, wall clock 4 hours (14400 s) enforced by the launcher.
- Seed string, verbatim: `chicago-taxi-2023-week/2026-10-31`. Dataset `wrvz-psew`.
- Wrapper text, verbatim: ``The data is in `trips.csv` in this folder. Do the analysis in a Jupyter notebook named `analysis.ipynb` in this folder.``
- Skill side prompt = `"/iterative-data-science "` + wrapper + `"\n\n"` + brief; control prompt = wrapper + `"\n\n"` + brief.
- The SKILL.md in `plugins/iterative-data-science/skills/iterative-data-science/SKILL.md` is byte-identical to `~/.claude/skills/iterative-data-science/SKILL.md`; it is the only copy used anywhere.
- No paid step (any container run that calls a model) without the author's explicit go-ahead in chat. Never read `.env` or credential files; never print, log or commit a token.
- Public text says "the author", never "the user".
- `BUILD_LOG.md` is written in order as the work happens; times come from `date -u`, counts from scripts.
- Host run folders and workspaces must not contain the substring `iterative` and must sit outside the repository.

## Review Focus

1. **A token printed by an agent** (e.g. it runs `env`) must never reach `runs/`. Test: `scrub_tree` redacts the secret inside `messages.jsonl` and inside a notebook output (Task 6).
2. **A run that hits a cap or the SDK raising mid-stream** must still leave `messages.jsonl` and a `result.json` whose `status` names the cap. Test: fake query raising after two messages (Task 4).
3. **The agent never creates `analysis.ipynb`, or names it differently** must not crash analysis. Test: `compute` on a side with no notebook returns `notebook_present: False` and zero notebook counts (Task 8).
4. **A truncated or changed download** must stop the pipeline. Tests: row count equal to the limit raises; checksum mismatch raises (Task 3).
5. **A half-written notebook caught mid-save** must not produce a bogus snapshot. Test: the watcher skips content that is not valid JSON and keeps polling (Task 4).

---

### Task 1: Publish the skill as a one-plugin marketplace, start the build log

**Files:**
- Create: `plugins/iterative-data-science/skills/iterative-data-science/SKILL.md` (copied, not edited)
- Create: `plugins/iterative-data-science/.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `BUILD_LOG.md`

**Interfaces:**
- Produces: the skill path above, used by Tasks 6 and 10 as `SKILL_MD`.

- [ ] **Step 1:** `cp ~/.claude/skills/iterative-data-science/SKILL.md plugins/iterative-data-science/skills/iterative-data-science/SKILL.md`, then confirm `shasum -a 256` of both files match.
- [ ] **Step 2:** Write `plugin.json` with `"name": "iterative-data-science"`, `"version": "1.0.0"`, a one-line description ("Makes Claude Code work in small, verified batches in Jupyter notebooks"), `"license": "Apache-2.0"`. Write `marketplace.json` with `"name": "iterative-data-science"`, `"owner": {"name": "Nguyen Tran"}`, and one plugin entry `{"name": "iterative-data-science", "source": "./plugins/iterative-data-science", "description": <same line>}`.
- [ ] **Step 3:** Run `claude plugin validate .` and `claude plugin validate ./plugins/iterative-data-science`. Expected: both end with `✔ Validation passed`.
- [ ] **Step 4:** Start `BUILD_LOG.md`: a title, one paragraph saying it is append-only, and a first entry (timestamp from `date -u`) recording the spec and license commits and this task.
- [ ] **Step 5:** Commit: `git add plugins .claude-plugin BUILD_LOG.md && git commit -m "Package the skill as a one-plugin marketplace"`.

### Task 2: Host Python project and the week draw

**Files:**
- Create: `experiment/pyproject.toml` (uv project; deps `nbformat`, `claude-agent-sdk==0.2.176`; dev dep `pytest`), `experiment/uv.lock`
- Create: `experiment/data/__init__.py`, `experiment/data/draw_week.py`
- Test: `experiment/tests/test_draw_week.py`

**Interfaces:**
- Produces: `candidate_weeks(year: int = 2023) -> list[tuple[date, date]]`; `pick_index(seed: str, n: int) -> int`; `draw(seed: str = SEED) -> dict` returning `{"seed", "index", "monday", "sunday"}` (ISO date strings); CLI `python -m data.draw_week` writes `experiment/data/week.json` and refuses to overwrite an existing one.

- [ ] **Step 1: Write the failing tests**

```python
def test_candidates_exclude_first_and_last_full_week():
    weeks = candidate_weeks(2023)
    assert len(weeks) == 50
    assert weeks[0] == (date(2023, 1, 9), date(2023, 1, 15))
    assert weeks[-1] == (date(2023, 12, 18), date(2023, 12, 24))
    assert all(m.weekday() == 0 and (s - m).days == 6 for m, s in weeks)

def test_pick_index_is_sha256_mod_n():
    assert pick_index("abc", 50) == int(hashlib.sha256(b"abc").hexdigest(), 16) % 50
    assert pick_index("abc", 50) == pick_index("abc", 50)

def test_seed_is_the_committed_string():
    assert SEED == "chicago-taxi-2023-week/2026-10-31"

def test_cli_refuses_to_overwrite(tmp_path): ...  # existing week.json -> SystemExit, file unchanged
```

- [ ] **Step 2:** `cd experiment && uv run pytest tests/test_draw_week.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement `draw_week.py`. `candidate_weeks` takes every Monday whose Sunday is still in the year, starting from the first Monday, and drops the first and last.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `experiment/pyproject.toml experiment/uv.lock experiment/data experiment/tests` with message "Add the week draw".

### Task 3: Fetch the week and describe the dataset

**Files:**
- Create: `experiment/data/fetch_week.py`, `experiment/data/dataset_md.py`
- Test: `experiment/tests/test_fetch_week.py`, `experiment/tests/test_dataset_md.py`, fixture `experiment/tests/fixtures/views_wrvz-psew.json` (a trimmed copy of the real metadata: description plus three columns)

**Interfaces:**
- Consumes: `week.json` from Task 2.
- Produces: `soql_url(monday: date, sunday: date, limit: int = 2_000_000) -> str`; `check_rows(n_rows: int, limit: int) -> None` (raises `ValueError` when `n_rows >= limit`); `verify(csv: Path, expected_sha256: str) -> None` (raises `ValueError` on mismatch); CLI `python -m data.fetch_week` writes `experiment/data/trips.csv` (gitignored) and adds `rows`, `bytes`, `sha256` to `week.json` on first fetch, verifies on later fetches. `render(metadata: dict, week: dict) -> str` and CLI `python -m data.dataset_md OUT_PATH`.

- [ ] **Step 1: Write the failing tests**

```python
def test_url_filters_the_week_and_orders_by_trip_id():
    u = urllib.parse.unquote(soql_url(date(2023, 6, 5), date(2023, 6, 11)))
    assert "resource/wrvz-psew.csv" in u
    assert "trip_start_timestamp between '2023-06-05T00:00:00' and '2023-06-11T23:59:59'" in u
    assert "$order=trip_id" in u and "$limit=2000000" in u

def test_row_count_at_limit_is_rejected():
    with pytest.raises(ValueError): check_rows(2_000_000, 2_000_000)

def test_checksum_mismatch_is_rejected(tmp_path):
    p = tmp_path / "t.csv"; p.write_text("a\n")
    with pytest.raises(ValueError): verify(p, "0" * 64)

def test_render_is_verbatim_and_has_no_rows():
    md = render(METADATA_FIXTURE, {"monday": "2023-06-05", "sunday": "2023-06-11", "rows": 150573})
    assert METADATA_FIXTURE["description"] in md
    for c in METADATA_FIXTURE["columns"]:
        assert c["fieldName"] in md and c["dataTypeName"] in md and c.get("description", "") in md
    assert "2023-06-05" in md and "150,573" in md and "trips.csv" in md
```

- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement. `fetch_week` streams the download with `urllib`, retries up to 3 times with a printed notice that it takes minutes, then runs `check_rows` and either records or `verify`s the checksum. `render` lists columns as a Markdown table (field name, type, portal description) under the verbatim dataset description, then the week's dates, row count and the file name `trips.csv`.
- [ ] **Step 4:** Run the tests. Expected: PASS. Commit "Add the data fetch and dataset description".
- [ ] **Step 5 (free, no model calls):** Run `uv run python -m data.draw_week`, then `uv run python -m data.fetch_week`, then run `fetch_week` a second time to confirm the checksum verifies. Record the drawn week, row count and checksum in `BUILD_LOG.md`. Commit `experiment/data/week.json BUILD_LOG.md` with message "Draw and fetch the week".

### Task 4: The runner

**Files:**
- Create: `experiment/runner/__init__.py`, `experiment/runner/options.py`, `experiment/runner/watcher.py`, `experiment/runner/run.py`
- Test: `experiment/tests/test_runner.py`

**Interfaces:**
- Produces:
  - `@dataclass RunConfig(model: str, effort: str, prompt: str, max_turns: int, max_budget_usd: float, disallow_web: bool, workspace: Path = Path("/home/analyst/work"), out_dir: Path = Path("/out"))`
  - `build_options(cfg: RunConfig) -> ClaudeAgentOptions`
  - `class NotebookWatcher(path: Path, snapshot_dir: Path, interval: float = 1.0)` with `start()`, `stop()`, `poll_once() -> bool`; writes `snap-0001.ipynb` … plus `snapshots.jsonl` lines `{"seq", "seen_at"}`
  - `serialize(message) -> dict` (dataclass to dict, plus `"_type"`)
  - `async run(cfg: RunConfig, query_fn=query) -> dict` writes `messages.jsonl` (appended per message), `init.json` (the init `SystemMessage` data), `result.json` with `status` ∈ {`"success"`, `"error_max_turns"`, `"error_max_budget_usd"`, `"error"`} plus `num_turns`, `duration_ms`, `total_cost_usd`, `usage`, `signin_method`; returns that dict
  - CLI: `python -m runner.run --model M --effort E --prompt-file F --max-turns N --max-budget-usd X [--disallow-web]`; after `run`, writes `packages.txt` from `/opt/venv/bin/pip freeze`

- [ ] **Step 1: Write the failing tests**

```python
def test_options_match_the_spec():
    o = build_options(RunConfig("claude-sonnet-5-5", "high", "p", 1000, 100.0, False))
    assert o.system_prompt == {"type": "preset", "preset": "claude_code"}
    assert o.setting_sources == ["project"] and o.permission_mode == "bypassPermissions"
    assert o.max_turns == 1000 and o.max_budget_usd == 100.0 and o.effort == "high"
    assert o.env["CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT"] == "1" and o.env["DISABLE_AUTOUPDATER"] == "1"
    assert o.env["OTEL_LOG_RAW_API_BODIES"] == "file:/out/private/bodies"
    assert o.env["PATH"].startswith("/opt/venv/bin:")
    assert o.disallowed_tools == []

def test_task_writer_has_no_web_tools():
    o = build_options(RunConfig("claude-opus-5-5", "high", "p", 1000, 100.0, True))
    assert set(o.disallowed_tools) == {"WebSearch", "WebFetch"}

def test_cap_mid_stream_keeps_log_and_status(tmp_path):
    # fake query yields an init SystemMessage and one AssistantMessage, then raises the SDK's
    # ResultError for "Reached maximum number of turns"
    result = asyncio.run(run(cfg_with_out(tmp_path), query_fn=fake_query_hitting_cap))
    assert result["status"] == "error_max_turns"
    assert len((tmp_path / "messages.jsonl").read_text().splitlines()) == 2
    assert json.loads((tmp_path / "result.json").read_text())["status"] == "error_max_turns"

def test_watcher_snapshots_only_valid_changed_json(tmp_path):
    nb = tmp_path / "analysis.ipynb"; w = NotebookWatcher(nb, tmp_path / "snaps")
    assert w.poll_once() is False                      # no file yet
    nb.write_text('{"cells": [], "nbformat": 4'); assert w.poll_once() is False   # half-written
    nb.write_text('{"cells": [], "nbformat": 4, "nbformat_minor": 5, "metadata": {}}'); assert w.poll_once() is True
    assert w.poll_once() is False                      # unchanged
    assert sorted(p.name for p in (tmp_path / "snaps").glob("*.ipynb")) == ["snap-0001.ipynb"]
```

- [ ] **Step 2:** `uv run pytest tests/test_runner.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement. `build_options` builds `env` from scratch: the pinned variables above, `PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin`, `HOME=/home/analyst`, and the one sign-in variable present in `os.environ` (`CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`). `signin_method` records which name, never the value. The watcher runs in a daemon thread; `run` starts it before the query and stops it, with one final `poll_once`, in a `finally`. Map the SDK's `ResultError`/`ResultMessage.subtype` to `status`.
- [ ] **Step 4:** Run the tests. Expected: PASS. Commit "Add the runner".

### Task 5: The Docker image

**Files:**
- Create: `experiment/Dockerfile`, `experiment/requirements/runner.txt` (`claude-agent-sdk==0.2.176`), `experiment/requirements/analysis.in` (pandas, numpy, matplotlib, seaborn, scipy, statsmodels, scikit-learn, jupyter, nbconvert, ipykernel), `experiment/requirements/analysis.txt` (from `uv pip compile requirements/analysis.in --python-version 3.13 -o requirements/analysis.txt`)

**Interfaces:**
- Consumes: `experiment/runner/` from Task 4.
- Produces: image tag `ids-experiment:latest`; entrypoint `python -m runner.run` run from `/opt/runner` as user `analyst`; mounts expected at `/home/analyst/work` and `/out`.

- [ ] **Step 1:** Write the Dockerfile: `python:3.13-slim` base; copy `uv` from `ghcr.io/astral-sh/uv`; `useradd -m analyst`; create `/opt/runner/.venv` from `runner.txt` and `/opt/venv` from `analysis.txt` (chown `/opt/venv` to `analyst`); copy `runner/` to `/opt/runner/runner/`; `ENV DISABLE_AUTOUPDATER=1`; `USER analyst`; `WORKDIR /opt/runner`; `ENTRYPOINT ["/opt/runner/.venv/bin/python", "-m", "runner.run"]`.
- [ ] **Step 2:** `docker build -t ids-experiment experiment`. Expected: succeeds.
- [ ] **Step 3:** Verify, with no sign-in variable and no model call:
  - `docker run --rm --entrypoint whoami ids-experiment` → `analyst`
  - `docker run --rm --entrypoint sh ids-experiment -c '/opt/runner/.venv/lib/python3.13/site-packages/claude_agent_sdk/_bundled/claude --version'` → `2.1.316 (Claude Code)`
  - `docker run --rm --entrypoint /opt/venv/bin/jupyter ids-experiment nbconvert --version` → a version string
  - `docker run --rm --entrypoint sh ids-experiment -c 'grep -ri iterative /opt/runner/runner || echo clean'` → `clean`
- [ ] **Step 4:** Commit "Add the experiment image".

### Task 6: Launcher helpers and `run_pair.py`

**Files:**
- Create: `experiment/launch/__init__.py`, `experiment/launch/signin.py`, `experiment/launch/workspace.py`, `experiment/launch/scrub.py`, `experiment/launch/docker.py`, `experiment/run_pair.py`, `experiment/prompts/wrapper.md` (the wrapper text, verbatim, no trailing newline)
- Test: `experiment/tests/test_launch.py`

**Interfaces:**
- Consumes: image from Task 5, `SKILL_MD` from Task 1, `trips.csv`/`week.json` from Task 3.
- Produces:
  - `signin_env(environ: Mapping[str, str]) -> tuple[str, str]` (name, value); prefers `CLAUDE_CODE_OAUTH_TOKEN`, else `ANTHROPIC_API_KEY`, else `SystemExit` with a message naming both
  - `prepare_workspace(side: Literal["control", "skill"], csv: Path | None, skill_md: Path, files: dict[str, str] | None = None) -> Path` — fresh `tempfile.mkdtemp(prefix="run-")`; copies `csv` as `trips.csv` when given; skill side also gets `.claude/skills/iterative-data-science/SKILL.md`; `files` writes extra named text files (used by Task 7)
  - `build_prompt(side, wrapper: str, brief: str) -> str`
  - `scrub_tree(root: Path, secret: str) -> int` (replaces every occurrence with `[REDACTED]` in every file under `root`, returns the count)
  - `start(image: str, workspace: Path, out_dir: Path, prompt: str, run_args: list[str], signin: tuple[str, str]) -> str` (container ID). Writes `prompt` to `out_dir/prompt.md` (so the exact prompt is kept with the run) and passes `--prompt-file /out/prompt.md` plus `run_args`. Mounts `workspace` at `/home/analyst/work` and `out_dir` at `/out`. Passes the sign-in value with `-e NAME` from the launcher's environment so it never appears on a command line
  - `wait_all(ids: list[str], timeout_s: int) -> dict[str, str]` (`"exit:<code>"` or `"timeout"`; `docker stop` on timeout)
  - `run_pair.py [--check]`: real pair, or with `--check` the trivial system-prompt check (prompt `Reply with exactly: OK`, `--max-turns 2`) into `runs/check-<UTC>/`; writes `pair.json` (start times, image ID, Claude Code version from `init.json`, data and skill SHA-256, chip type, redaction count) and copies each side's `/out` to `runs/<run-id>/<side>/` (workspace minus `trips.csv`, `private/` kept but gitignored) only after `scrub_tree`

- [ ] **Step 1: Write the failing tests**

```python
def test_signin_prefers_plan_token():
    assert signin_env({"CLAUDE_CODE_OAUTH_TOKEN": "a", "ANTHROPIC_API_KEY": "b"}) == ("CLAUDE_CODE_OAUTH_TOKEN", "a")
    with pytest.raises(SystemExit): signin_env({})

def test_workspaces_differ_only_by_skill(tmp_path):
    c = prepare_workspace("control", CSV, SKILL_MD); s = prepare_workspace("skill", CSV, SKILL_MD)
    assert "iterative" not in str(c) and "iterative" not in str(s)
    assert not (c / ".claude").exists()
    assert (s / ".claude/skills/iterative-data-science/SKILL.md").read_bytes() == SKILL_MD.read_bytes()
    assert (c / "trips.csv").read_bytes() == (s / "trips.csv").read_bytes()

def test_prompts_differ_only_by_prefix():
    assert build_prompt("control", "W", "B") == "W\n\nB"
    assert build_prompt("skill", "W", "B") == "/iterative-data-science W\n\nB"

def test_scrub_redacts_token_in_logs_and_notebooks(tmp_path):
    (tmp_path / "messages.jsonl").write_text('{"x": "TOKEN=sk-secret"}\n')
    (tmp_path / "ws").mkdir(); (tmp_path / "ws/analysis.ipynb").write_text('{"o": "sk-secret sk-secret"}')
    assert scrub_tree(tmp_path, "sk-secret") == 3
    assert "sk-secret" not in "".join(p.read_text() for p in tmp_path.rglob("*") if p.is_file())
```

- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement the helpers and `run_pair.py`. Starts are back to back; record both start times with millisecond precision. Wall-clock timeout `14400`.
- [ ] **Step 4:** Run the tests. Expected: PASS. Commit "Add the launcher".

### Task 7: The clean-room task writer

**Files:**
- Create: `experiment/prompts/task_writer.md` (spec §5 instructions, verbatim), `experiment/launch/brief_checks.py`, `experiment/run_task_writer.py`
- Test: `experiment/tests/test_brief_checks.py`

**Interfaces:**
- Consumes: `prepare_workspace(..., files={"dataset.md": ...})`, `start`, `wait_all`, `scrub_tree` from Task 6; `render` from Task 3.
- Produces: `check_brief(text: str, columns: set[str]) -> list[str]` (failure reasons; empty means pass); `check_no_data_access(messages_jsonl: Path) -> list[str]`; `run_task_writer.py` runs Opus with `--disallow-web`, no CSV, `dataset.md` only, into `experiment/task/runs/<UTC>/`; on pass copies `brief.md` to `experiment/task/brief.md`; on fail moves the draft and its reasons to `experiment/task/rejected/<UTC>/` and exits non-zero.

- [ ] **Step 1: Write the failing tests**

```python
COLS = {"trip_id", "fare", "tips", "trip_start_timestamp"}
GOOD = "# Brief\n\n1. How do fares vary?\n2. When do trips start?\n3. How do tips relate to fare?\n"

def test_accepts_three_or_four_questions():
    assert check_brief(GOOD, COLS) == []

def test_rejects_two_or_five_questions_and_long_briefs():
    assert check_brief("1. a?\n2. b?\n", COLS)
    assert check_brief("".join(f"{i}. q?\n" for i in range(1, 6)), COLS)
    assert check_brief(GOOD + "word " * 400, COLS)

def test_rejects_unknown_backticked_column():
    assert check_brief(GOOD + "Use `driver_rating`.", COLS)

def test_flags_data_endpoint_access(tmp_path):
    log = tmp_path / "m.jsonl"
    log.write_text(json.dumps({"_type": "AssistantMessage", "content": [{"name": "Bash",
        "input": {"command": "curl https://data.cityofchicago.org/resource/wrvz-psew.csv"}}]}) + "\n")
    assert check_no_data_access(log)
```

Question counting: top-level numbered items (`^\d+\.`) or headed questions (`^#+ .*\?$`); words counted with `str.split`. Column check: backticked identifiers and snake_case tokens that look like column names but are not in `columns`. Data access: any tool input mentioning `data.cityofchicago.org/resource/` or `/api/views/wrvz-psew/rows`.

- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. Max turns for the writer: 200; budget cap 100.
- [ ] **Step 4:** Run the tests. Expected: PASS. Commit "Add the clean-room task writer".

### Task 8: Analysis

**Files:**
- Create: `experiment/analysis/__init__.py`, `experiment/analysis/system_prompt.py`, `experiment/analysis/metrics.py`
- Test: `experiment/tests/test_analysis.py`, fixtures under `experiment/tests/fixtures/side/` (a tiny `messages.jsonl`, `result.json`, three snapshots, a final notebook with one mixed-output cell and one error cell, one PNG)

**Interfaces:**
- Consumes: the per-side folder layout from Tasks 4 and 6.
- Produces:
  - `extract_system_prompt(bodies: Path) -> str` (first `query_source == "sdk"` request in `index.jsonl`; drops the `x-anthropic-billing-header` line); `first_request_has(bodies: Path, marker: str) -> bool`
  - `compute(side_dir: Path) -> dict` with keys `notebook_present, executions, batch_sizes, mixed_output_cells, figures_created, figures_opened, inline_images, tool_errors, cell_errors, rework_cells, turns, duration_s, cost_usd, input_tokens, output_tokens, web_searches, web_fetches, package_installs`
  - `reexecute(notebook: Path, image: str) -> bool` (runs `jupyter nbconvert --to notebook --execute` in a fresh container from the image, with `trips.csv` mounted alongside)
  - CLI `python -m analysis.metrics runs/<run-id> [--no-reexecute]` writes `runs/<run-id>/metrics.json` (each side's `compute` result plus `fresh_reexecution` from `reexecute`; `--no-reexecute` for the trivial check run) and `system_prompts.json` (both hashes and whether they match)

- [ ] **Step 1: Write the failing tests** — on the fixture side: `executions == 2`, `batch_sizes == [2, 1]`, `mixed_output_cells == 1`, `cell_errors == 1`, `figures_created == 1`, `figures_opened == 1`, `rework_cells == 1`, `package_installs == 1` (a `pip install` Bash call), `tool_errors == 1`. A side folder with no notebook: `notebook_present is False`, `executions == 0`, `mixed_output_cells == 0`. `extract_system_prompt` on a two-request fixture returns the main-thread prompt without the billing line, identical for two fixtures that differ only in that line.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement per spec §7 definitions; snapshots read with `nbformat`, cells matched by `id`, falling back to position when IDs are missing.
- [ ] **Step 4:** Run the full suite `uv run pytest -v`. Expected: all PASS. Commit "Add the analysis".

### Task 9: Probe notes and the README before results

**Files:**
- Create: `docs/probe-2026-10-31.md` (spec §11 expanded slightly, no raw bodies, no account details), `README.md`

- [ ] **Step 1:** Write the probe notes from spec §11.
- [ ] **Step 2:** Write `README.md` in the spec §8 order, with section 2 ("Findings") holding only "Results will appear here after the first pair runs." and every other section complete: install (both ways), what the experiment does and does not show, how it was kept neutral, how to reproduce, license. "The author", not "the user".
- [ ] **Step 3:** Commit "Add the README and probe notes".

### Task 10: Run the clean-room task writer — PAID, needs the author's go-ahead

- [ ] **Step 1:** Ask the author for the go-ahead and confirm the plan token is set in their shell (do not read it).
- [ ] **Step 2:** `cd experiment && uv run python run_task_writer.py`. Expected: exits 0 with `experiment/task/brief.md` written. If it exits non-zero, the rejected draft is already kept; run it again (no other changes) and log both.
- [ ] **Step 3:** Log the run in `BUILD_LOG.md` (time, cost from `result.json`, pass or the failed checks). Commit `experiment/task BUILD_LOG.md` with message "Accept the brief".

### Task 11: System-prompt check with the real image — PAID (cents), needs go-ahead

- [ ] **Step 1:** Ask for the go-ahead.
- [ ] **Step 2:** `uv run python run_pair.py --check`, then `uv run python -m analysis.metrics runs/check-<UTC> --no-reexecute`.
- [ ] **Step 3:** Verify: `system_prompts.json` says the two sides match; `first_request_has(skill bodies, "# Iterative Data Science Workflow")` is true and false for control; `init.json` of each side lists no user plugins and only the skill side lists `iterative-data-science`; the redaction count is recorded. If any check fails, stop and report; do not run the pair.
- [ ] **Step 4:** Log and commit "Check the system prompt in the real image".

### Task 12: Run the pair — PAID, needs go-ahead

- [ ] **Step 1:** Ask for the go-ahead, stating the caps (1000 turns, $100 estimated, 4 hours per side).
- [ ] **Step 2:** `uv run python run_pair.py`, run in the background; do not poll.
- [ ] **Step 3:** When it finishes, `uv run python -m analysis.metrics runs/<run-id>`. Verify both sides have `result.json`, `messages.jsonl`, `snapshots/`, and that `git status` shows no file under any `private/` folder.
- [ ] **Step 4:** Log and commit `runs/<run-id> BUILD_LOG.md` with message "Run the first pair".

### Task 13: Write up the findings

- [ ] **Step 1:** Read both final notebooks, both logs and `metrics.json` in full. Write the consequences (each quoted from the log, both sides treated the same) and trace every disagreement on a checkable number to its cause in the code, per spec §7.
- [ ] **Step 2:** Fill README section 2: the counts table, the consequences, the disagreements, each linked to the exact files and cells. Present the SKILL.md's inline-render line as the observation the skill was written from, alongside the figure counts.
- [ ] **Step 3:** Commit "Write up the first pair". Ask the author to read the README before anything is pushed.

## Where the build differed from this plan

The tasks above are the plan as written before the build. `BUILD_LOG.md` records what happened, and spec §§12–13 record the amendments.

- **Five pairs.** Task 12 ran one pair. Four more ran after it on the same brief, data, model, settings and caps, and the first release has all five.
- **Task 10.** The writer was stopped after five drafts, all rejected on length, instead of being rerun unchanged. It resumed under the amended setup (spec §12): `environment.md` in the writer's folder, the limits stated in its instructions, a 500-word cap, a question counter that skips numbered deliverables, and `dataset.md` in both sides' folders. Draft 6 was accepted.
- **Task 11 ran before the brief was accepted.** The system-prompt check does not use the brief.
- **WorkspaceWatcher.** The runner snapshots every notebook in the workspace, not only `analysis.ipynb`.
- **Wall clock.** The runner enforces the 4-hour limit and records `error_wall_clock`. The launcher keeps a backstop 15 minutes later.
- **`--init`.** Containers start with `docker run --init`, so a `docker stop` reaches the runner, which records `error_terminated`.
- **Check prompt.** The system-prompt check sends a two-part prompt ("Reply with exactly: OK", a blank line, "Do nothing else."), shaped like the pair's wrapper and brief, with 2 turns and an estimated $1 cap.
- **Hold-back.** Data files and files over 25 MB in a run folder are kept out of git by a per-run `.gitignore` and listed in `pair.json`.
- **Raw JSON.** `metrics.py` reads notebooks as raw JSON, not through `nbformat`.
- **`added_after_runs`.** Measures added after the runs sit under their own key in `metrics.json`, apart from the counts the spec fixed.
- **Runner pin.** `requirements/runner.txt` pins every package of the runner environment, not only `claude-agent-sdk`.
- **Base images.** The Dockerfile pins `python:3.13-slim` and the `uv` image by digest.
