# REPORT 19 correction (receipt-only REVISE)

Status: PARTIAL, unchanged. This corrects one attribution error in
`plan/v1/reports/19-preparation.md`, which is preserved verbatim as history.
The REVIEW of `1fd9d080996e216b9edc386597487a78067f25b5` recorded a scoped
ACCEPT for the code/docs integration and a receipt-only REVISE for the report.
No product, test, metadata, registry or documentation file is edited here;
the only change is this new report. Full Task 19 acceptance, final provider
inclusion and registry approval remain pending.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same authorized
session resumed directly; no subagents, nested executors, credentials, live
calls, pushes or main merges. Worktree
`/Users/ajay/.codex/worktrees/actseal-v1-integration/not-yet-named`, branch
`claude/v1-19-integration-preparation`, clean at `1fd9d08` before this edit
(confirmed with `git status --short --branch` and `git rev-parse HEAD`).

## The error

REPORT 19's "Integrated commits" table described the Task 09 snapshot as
including "sdist inputs (`tools/check_mutations.py`, `examples/action_gate/`
via `8acbf38` ...)". That attribution is wrong. Verified with
`git show 8acbf38 -- pyproject.toml`: commit
`8acbf38add37235a306060cc81ea19d89ba61eed` ("build(sdist): include the
required mutation harness") adds exactly one line to the sdist
`only-include` inventory, `"tools/check_mutations.py"`, and nothing else.
`examples/action_gate/` does not appear in any commit on this branch
(`git log -S action_gate -- pyproject.toml tests/packaging tests/release
tests/acceptance` returns nothing), is not in the current `pyproject.toml`
inventory (which lists only `examples/support_triage` under `examples/`), and
does not exist in this checkout (`examples/` contains only `support_triage`).

## Correct attribution

| Commit | What it actually adds to the sdist inventory |
|---|---|
| `8acbf38add37235a306060cc81ea19d89ba61eed` | `tools/check_mutations.py` only (reviewed; its supplied-sdist content check lives in `tests/release/test_check_release_distributions.py`). |
| `c0a183c5fe95e1e7e21e193b64f0e31c2584de66` | The v1 documentation inputs required by `tests/docs` (`plan/v1/STATE.md`, `plan/v1/CHANGE_LOG.md`, `plan/v1/PLAN.md`, `plan/v1/tasks/08.md`, `plan/v1/reports`, `plan/v1/reviews`). |

Neither commit packages `examples/action_gate/`.

## What remains

Per `plan/v1/INTEGRATION_CHECKLIST.md` ("Packaged source inputs"), when the
Task 07 archive lands, Task 19 must add exactly `examples/action_gate/` to the
sdist `only-include` inventory and extend the supplied-sdist content checks
(the release-distribution and packaging tests, and the actual installed-sdist
replay outside the checkout) so that every test importing or reading that
path has its input in the source distribution. That example inclusion and its
installed-sdist check are still future Task 07/19 integration work; this
preparation phase did not import, exclude or register the Task 07 archive, so
nothing about it is claimed as done. The original example producer
`a5fe090202f75b07510407937a86ae35a7653a75eab3f4daa2d0ace2e7641642` and lock
`cb009be0039afefd995f6eac3a8bd9767d6bf026a73273b47e87a51fc9fbd715` remain
unregistered and untouched.

## Review receipts (Codex, not commands run by this executor)

- Parent independently ran all 3824 tests, including cached native plus
  assets, in 107.66 seconds at exact `1fd9d08`, followed by a successful
  pre-commit run.
- The independent reviewer ran 359 focused tests in 4.96 s.

The Claude-run results recorded in REPORT 19 (focused 1092 passed; pre-commit
passed; `-m "not integration"` 3812 passed, 1 skipped, 6 deselected) remain
historical receipts of the pre-review working tree and are not restated as
current acceptance.

## Commands run for this correction

| Command | Result |
|---|---|
| `git show 8acbf38 -- pyproject.toml` | one added line: `"tools/check_mutations.py"` |
| `git log -S action_gate -- pyproject.toml tests/packaging tests/release tests/acceptance` | no commits |
| `git diff --check` (working tree) and `git diff --cached --check` (this report staged) | exit 0, no whitespace errors |
| `UV_OFFLINE=1 uv run --frozen pre-commit run --all-files` | `ruff check` Passed, `ruff format --check` Passed, `mypy --strict` Passed |

Only `plan/v1/reports/19-preparation-correction.md` is committed. Spend for
this correction: executor-visible receipts none; usage explicitly unknown.
