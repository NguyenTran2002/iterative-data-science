# Build log

Entries are written in order as the work happens: times come from `date -u`, counts and checksums from scripts. Corrections are added as new entries.

## 2026-10-31T21:20Z: Package the skill

- Already committed: the design spec (`docs/design/2026-10-31-experiment-design.md`), the Apache 2.0 license, and the implementation plan (`docs/design/2026-10-31-implementation-plan.md`).
- Copied the author's `SKILL.md` unchanged into `plugins/iterative-data-science/skills/iterative-data-science/SKILL.md`. SHA-256 of both copies: `b712fec1d97aeea8cea50ea5c5cbbb972730b3d82728ac6e646f8710e8f71c17`.
- Added `plugin.json` and `.claude-plugin/marketplace.json`. `claude plugin validate .` and `claude plugin validate ./plugins/iterative-data-science` both pass. The plugin-directory check asks for a README, which comes with the repository README.
