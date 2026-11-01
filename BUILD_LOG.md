# Build log

Entries are written in order as the work happens: times come from `date -u`, counts and checksums from scripts. Corrections are added as new entries.

## 2026-10-31T21:20Z: Package the skill

- Already committed: the design spec (`docs/design/2026-10-31-experiment-design.md`), the Apache 2.0 license, and the implementation plan (`docs/design/2026-10-31-implementation-plan.md`).
- Copied the author's `SKILL.md` unchanged into `plugins/iterative-data-science/skills/iterative-data-science/SKILL.md`. SHA-256 of both copies: `b712fec1d97aeea8cea50ea5c5cbbb972730b3d82728ac6e646f8710e8f71c17`.
- Added `plugin.json` and `.claude-plugin/marketplace.json`. `claude plugin validate .` and `claude plugin validate ./plugins/iterative-data-science` both pass. The plugin-directory check asks for a README, which comes with the repository README.

## 2026-10-31T21:53Z: Task writer, draft 1: rejected

- Clean-room run `experiment/task/runs/2026-10-31T2153Z/` (Opus 5.5, effort `high`, no skill, no web tools, workspace holding only `dataset.md`): 3 turns, 35 s, $0.15 estimated, signed in with a plan token, 0 redactions.
- Rejected by the committed checks: "has 7 questions, not three or four; has 875 words, not under 400". The draft is kept in `experiment/task/rejected/2026-10-31T2153Z/`.
- Note on the checks: the draft has four questions, written as `### 1. …?` headings; the counter also counted its three numbered deliverables. The word count fails it on its own, so the rejection stands. The checks are not changed after seeing a draft.
- Before the review fixes, a whole-branch review found two critical and seven important issues; all were fixed test-first. The plan token was checked with one `claude-haiku-5-5` call that replied "OK".

## 2026-10-31T21:54Z to 22:01Z: Task writer, drafts 2 to 5: rejected

| Run | Words | Questions counted | Turns | Est. cost |
|---|---|---|---|---|
| 2026-10-31T2154Z | 746 | 3–4 (passed) | 3 | $0.10 |
| 2026-10-31T2156Z | 912 | 7 | 3 | $0.12 |
| 2026-10-31T2158Z | 682 | 3–4 (passed) | 3 | $0.10 |
| 2026-10-31T2200Z | 764 | 3–4 (passed) | 3 | $0.11 |

All five drafts so far failed the under-400-words check. The writer's instructions do not mention a length, so the drafts run 680 to 910 words. The writer is stopped here and no brief is accepted. Whether to add the limits to the instructions is the author's decision, recorded in a new entry when made. All drafts are kept in `experiment/task/rejected/` with their run records in `experiment/task/runs/`.

## 2026-10-31T22:01Z: System-prompt check in the real image: passed

`run_pair.py --check` (`runs/check-2026-10-31T2201Z/`) sent each side a two-part prompt shaped like the pair's ("Reply with exactly: OK", a blank line, "Do nothing else."); the skill side's prompt had the `/iterative-data-science ` prefix.

- **The two sides received the same system prompt:** 6,499 characters each, SHA-256 `279e494a…6b92eb6` (`system_prompts.json`).
- **The skill side's first request contained the SKILL.md text; the control side's did not.**
- **Loaded:** only Claude Code's three built-in plugins on both sides. The skill side listed `iterative-data-science` as an extra skill; the control side did not have it. Claude Code 2.1.316 on both sides.
- **Starts:** 22:01:21.507Z and 22:01:21.676Z, 0.17 s apart. Both exited 0 after one turn, at an estimated $0.02 and $0.03.
- **Redactions:** 0. No data files were held back.
- **Account context:** the only email addresses in either side's raw requests are `@anthropic.com` addresses; no account email or git identity reached the containers.

## 2026-10-31T22:15Z: Brief setup rewritten before redrafting

The author's decision after the five rejected drafts: the experiment's own setup, not the clean-room writer, had left out the practical facts a real brief carries. The clean-room writer gets no data, but should get the infrastructure the experiment runs on, and the analyst should get the logistics a real brief carries. Spec section 12 records the changes: `environment.md` for the writer, the limits stated in its instructions with the word cap moved to 500, a question counter that skips numbered deliverables, and `dataset.md` in both sides' folders. Before this, the author asked to use draft 1 as is; that was set aside in favor of the rewrite.

## 2026-10-31T22:29Z: Task writer, draft 6: accepted

- The first draft under the rewritten setup (spec section 12) passed every check: four questions, 489 words, only listed columns named, no access to the portal or the dataset. Run `experiment/task/runs/2026-10-31T2229Z/`: 7 turns, an estimated $0.19, 0 redactions.
- Committed as `experiment/task/brief.md`, with the `dataset.md` the writer saw as `experiment/task/dataset.md`; both sides of the pair get that file.
- Caps reviewed against the brief before the pair: 1,000 turns, an estimated $100 and 4 hours per side, unchanged. The brief asks for descriptive work on 135,768 rows, so each cap is expected to sit far above what a side uses.

## 2026-10-31T22:30Z: The first pair

Run `runs/2026-10-31T2230Z/`. Starts: 22:30:30.412Z (control) and 22:30:30.581Z (skill), 0.17 s apart. Both exited 0 with status `success`, far inside every cap. 0 redactions; no files held back from git. The two sides received the same system prompt (6,499 characters, SHA-256 `279e494a…6b92eb6`); the SKILL.md text was in the skill side's first request only.

Counts from `metrics.json`, computed by the committed `metrics.py`:

| | Control | Skill |
|---|---|---|
| Turns | 26 | 34 |
| Duration | 322 s | 372 s |
| Estimated cost | $0.77 | $0.87 |
| Executions of the notebook | 5 | 17 |
| Cells per execution | 16, 16, 16, 16, 16 | 1 to 3 |
| Reworked cells | 0 | 5 |
| Cells mixing text and image output | 3 | 0 |
| Inline images in final notebook | 6 | 4 |
| Image files saved in the workspace | 0 | 4 |
| Distinct image files opened with Read | 5 | 4 |
| Tool errors | 0 | 1 |
| Cell errors in final notebook | 0 | 0 |
| Fresh re-execution | passes | passes |
| Web searches, fetches, package installs | 0 | 0 |

Note for the write-up: the control side saved its figures under `/tmp/nbbuild/`, outside the workspace, and opened five of them there. The "image files saved in the workspace" count is 0 by the spec's definition, not because it made no figures. Both sides read Claude Code's built-in `dataviz` skill before charting.

## 2026-10-31T22:43Z: Decision: four more pairs on the same brief

After reading the first pair's counts, the author decided to run four more pairs with the same brief, data, image, model, settings and caps, to see whether the difference in behavior holds across runs. They run one after another, so the pairs do not compete for the plan's rate limits; within each pair both sides start together. All four are published whatever they show, and none is rerun because of its result.

## 2026-10-31T22:44Z to 23:18Z: Pairs 2 to 5

Runs `runs/2026-10-31T2244Z/`, `…T2253Z/`, `…T2302Z/`, `…T2310Z/`, one after another. In every pair both sides exited 0 with status `success`; the two sides started 0.17 to 0.23 s apart; they received the same system prompt (the same hash as pair 1); the SKILL.md text was in the skill side's first request only; 0 redactions; nothing held back from git. The metrics were computed by the committed `metrics.py`, with fresh re-execution.

| Pair | Side | Turns | Duration | Est. cost | Executions | Rework | Mixed cells | Figures saved / opened | Tool errors | Fresh re-run |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | control | 26 | 322 s | $0.77 | 5 | 0 | 3 | 0 / 5 | 0 | passes |
| 1 | skill | 34 | 372 s | $0.87 | 17 | 5 | 0 | 4 / 4 | 1 | passes |
| 2 | control | 32 | 312 s | $0.77 | 1 | 0 | 3 | 0 / 6 | 2 | passes |
| 2 | skill | 36 | 433 s | $0.94 | 15 | 3 | 0 | 5 / 5 | 0 | passes |
| 3 | control | 24 | 304 s | $0.76 | 3 | 0 | 1 | 0 / 5 | 1 | passes |
| 3 | skill | 43 | 483 s | $1.20 | 23 | 0 | 0 | 5 / 5 | 0 | passes |
| 4 | control | 21 | 218 s | $0.53 | 4 | 0 | 1 | 0 / 5 | 1 | passes |
| 4 | skill | 38 | 428 s | $1.00 | 22 | 4 | 0 | 5 / 5 | 1 | passes |
| 5 | control | 23 | 237 s | $0.59 | 4 | 0 | 2 | 0 / 5 | 1 | passes |
| 5 | skill | 33 | 449 s | $0.79 | 17 | 0 | 0 | 5 / 5 | 1 | passes |

No side made a web search, a web fetch or a package install, and no final notebook had a cell error. Every control side saved its figures outside the workspace (under `/tmp`) and opened them there.

**A limit of the batch-size count, as the spec anticipated for rework.** In pairs 4 and 5 the skill side rebuilt the notebook from a script on each pass, so every cell got a new ID each time. The ID-matched batch sizes in `metrics.json` therefore count whole notebooks as new, and those two sides' medians (8.5 and 9) are inflated. The committed definitions are not changed after the runs. A source-matched recount, added after seeing the runs and labelled as such, appears with the write-up.

## 2026-11-01T02:35Z: Correction: why pairs 2 to 5 were run

The entry for the decision to run four more pairs gave their purpose as checking "whether the difference in behavior holds across runs". The author corrects this: the extra pairs had been held in reserve in case the first run hit unforeseen errors, and were not an effort to correct or strengthen anything. They ran after the first pair had completed.

The author also notes, for the write-up: the skill was written for an older version of Sonnet. That the current Sonnet produces a sound notebook without it is expected and fine. The experiment's question is whether Claude changes how it works, toward the way a data scientist works, not whether the skill rescues a weak result.

## 2026-11-01T02:55Z: Decision: five pairs for the first release

The author decided the first release has the five pairs already run on the one brief; no second task. Nothing is published yet. The deferred minor findings from the whole-branch review are fixed next. Any new measure they add is computed after the runs and is labelled that way in `metrics.json`.

## 2026-11-01T03:01Z: Deferred review findings fixed

Fixed test-first, with the suite at 71 passing. None of these changes any count fixed before the runs; recomputing `metrics.json` for all five pairs left every one of those keys unchanged, including the fresh re-execution.

- **Runner:** `init.json` keeps the first init message. Each published run had exactly one, so nothing changes for them.
- **Data:** `fetch_week` checks a download's checksum before it replaces the local CSV.
- **Brief checks:** questions written as top-level bullets or bold lines count when nothing is numbered. The accepted brief still passes.
- **Image:** `requirements/runner.txt` pins every package of the runner environment at the versions in the image the pairs used. A rebuild gives an identical runner environment.
- **README:** states that the agent could read its own `/out` log folder.
- **New measures, under `added_after_runs` in `metrics.json`:** added after the runs and kept apart from the counts the spec fixed in advance. Packages not in the image's pinned set, install cells in any notebook version, `curl`/`wget` commands, images the model saw by source (image file or notebook), tool calls touching `/out`, and SKILL.md text in tool results. Across all ten sides: no installs, no downloads, no `/out` access, and no SKILL.md text on any control side. Every image the model saw came from a saved image file.

## 2026-11-01T03:16Z: Text-matched batch sizes added, labelled

At the author's go-ahead, `metrics.json` now has `added_after_runs.batch_sizes_by_source`. It counts batch size with cells matched by their code text instead of their ID, because in pairs 4 and 5 the skill side regenerated its notebook with new cell IDs on every pass. The committed ID-matched `batch_sizes` stay as they were. Recomputing changed none of the counts fixed in advance.

| Pair | Control: largest batch, median | Skill: largest batch, median |
|---|---|---|
| 1 | 16, 2 | 3, 1.5 |
| 2 | 17, 17 (one execution) | 3, 1 |
| 3 | 17, 3 | 3, 2 |
| 4 | 20, 2 | 3, 1 |
| 5 | 14, 3.5 | 3, 2 |

Note for the write-up, read from the logs: both sides looked at every figure and changed things after looking. The control first viewed a figure 52–68% of the way through its tool calls, after the whole notebook was built. It then viewed the figures in a row, fixed plot formatting and in several runs numbers in its own prose (pair 1: "800–920 trips an hour" became "790–920"), and re-viewed some. The skill side first viewed a figure 39–45% of the way through, and its later views alternate with edits.

## 2026-11-01T03:19Z: Late entry: the week was drawn and fetched at 2026-10-31T21:22Z

This entry should have been written at 21:22Z, but the command that appended it stopped at an earlier failing step, so the commit that recorded the draw holds only `week.json`. The facts below come from that file and the fetch scripts' output at the time.

- `python -m data.draw_week` drew index 35 of 50: **Monday 2023-09-11 to Sunday 2023-09-17**. The draw is final.
- First fetch, 21:22:29Z to 21:23:09Z: 135,768 rows, 61,133,584 bytes, SHA-256 `ea55bda9551a8908f3d05ff67afbd48013ec57eb02eb243f7cf95538f47ecf8a`, recorded in `experiment/data/week.json`.
- Second fetch, 21:23:56Z to 21:24:37Z: the checksum matched.
