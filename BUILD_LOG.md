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
