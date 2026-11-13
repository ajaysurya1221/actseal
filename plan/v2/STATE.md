# Actseal v2 — shared execution state

Claude Code (`claude-fable-5-2`) orchestrates and reviews; Codex (Astra 6)
executes and co-plans (`plan/v2/CHANGE_LOG.md` V2-001a). No independent
third-party review has been performed; nothing here is an ACCEPT.

## Status — 13 November 2026

2.0.0 candidate on branch `claude/v2-foundations`. Not tagged, not published.

| Item | State | Record |
|---|---|---|
| M0 local model spike | Desk check only. No model loaded: free memory stayed under the 10 GB floor while another session used Ollama | `reports/M0.md`, `receipts/spike.json` |
| M2 narrowed fingerprint, audit replay | Done, reviewed by the orchestrator | executor summary in the pull request |
| M3 selector and planner | Done, reviewed | `src/actseal/selection.py` |
| M4 recorded and decision-api providers | Done, reviewed | `reports/M4.md` |
| M5 plan, calibrate, qualify, replay-selection | Done, reviewed, one review fix applied | `reports/M5.md` |
| M6 report and GitHub Action | Done, reviewed | `reports/M6.md` |
| Figures | Regenerated | `reports/assets.md` |
| Version 2.0.0, README, changelog | Done | `reports/release-prep.md` |
| M7, M8 model comparison | Not started. Not part of this candidate (V2-002) | |

## Orchestrator checks on the final tree (local, macOS)

- `uv run --frozen pytest -m "not integration and not packaging" -q`: exit 0.
- `uv run --frozen mypy --strict src tests`: exit 0, 126 files.
- `uv run --frozen ruff check .` and `ruff format --check .`: exit 0.
- `uv run --frozen python tools/check_mutations.py`: 8 killed, 0 survived.
- `actseal replay docs/results/jev-audit-2026-10-08/evidence`: exit 2,
  INCONCLUSIVE, 580/639 accepted, 24 errors, matching the stored verdict.
- Running fingerprint `1c579ef18c4a…` is registered for `actseal-choice-v1`
  (replaces the earlier candidate value: a review finding that `cli.py`'s
  `_load_report_data` held real qualification-linkage integrity logic outside
  the fingerprint was fixed by moving it into
  `actseal.qualification.load_qualification_evidence`).

## Hosted checks (push runs on commit `29f25de`)

- `CI`: success on ubuntu and macOS, Python 3.12 and 3.13, including the
  clean-wheel packaging step. The first run on `0f3687e` failed that step on
  two stale tests; `29f25de` fixed the tests, with no product change.
- `Actseal action self-test`: success for `replay` and `qualify` on hosted
  runners.
- Pull request: ajaysurya1221/actseal#82, opened by the maintainer.

## Not verified

- The Laya integration tests (optional model packages are not installed).
- Any live decision-api server; any local decision model beyond v1's Laya work.
- External model, server, dataset and licence facts in the plan and in M0.
- The selector simulation used a loose risk limit (0.25); a run at a realistic
  limit is still owed.
- New mutants for the selector are not yet in `tools/check_mutations.py`.
