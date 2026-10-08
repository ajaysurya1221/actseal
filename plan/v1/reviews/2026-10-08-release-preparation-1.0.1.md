# Release preparation record — Actseal 1.0.1 (8 October 2026)

This record identifies the trees that were tested before the `v1.0.1` tag, the exact commands,
their results and who produced each result. Lanes follow `plan/VERIFICATION.md`:
**EXECUTOR REPORT** (the implementing executor reported the command and result; the
orchestrator did not repeat it unless a re-run is listed), **ORCHESTRATOR RE-RUN** (the
orchestrator ran the command), **HOSTED RUN** (a GitHub Actions run, identified by id).
Reviewer verdicts are in the acceptance ledger
(`2026-10-08-refinement-acceptance.md`) once recorded. Dates and times are IST.

## Trees

| Tree | Description |
|---|---|
| T0 | `main` at `39c75a2` (base of branch `claude/release-1.0.1-docs`) |
| T1 | T0 plus the orchestrator's documentation edits: dated `v1.0.1` changelog heading with the Unreleased entries moved under it, `CITATION.cff` 1.0.1 / 2026-10-08, the README recording-provenance sentence, ADR 0019 receipt scoping, V1-059 heading |
| T2 | T1 plus the executor's package: `tools/check_release.py` version-aware receipt paths and tests, `plan/v1/releases/1.0.1/RELEASE_NOTES.md` and `FINAL_REPORT.md`, `pyproject.toml` sdist inclusion, `docs/publishing.md`, V1-059 body, one README guard line |
| T3 | T2 plus the orchestrator's follow-up edits after the second review: `docs/versioning.md` registry wording, `docs/assets/src/recording.md` historical checkpoint, this record, the native-receipt references in ADR 0019, the 1.0.1 notes, the 1.0.1 report and V1-059 |

No file under `src/` differs between T0 and T3 (`git diff --quiet HEAD -- src` on T3), so every
tree carries the 1.0.1 source, implementation fingerprint
`dced01d79e64799a19a75c0957f3684a48249c58ebb27d346336e7420195bcb4` (approved by V1-055; unchanged
since `d1f3215`).

## Cached-native receipts for the changed Laya path (ADR 0019)

The 1.0.1 patch changes native worker reply validation in `src/actseal/adapters/laya.py`.
ADR 0019 requires a cached-native receipt for a changed native path before release; green
hosted deterministic jobs do not satisfy it.

| Lane | Platform | Command | Result |
|---|---|---|---|
| ORCHESTRATOR RE-RUN | macOS 26.6.2 arm64, Python 3.12.13, tree T2 (the `.venv` of the worktree, `laya` extra installed from the frozen lock) | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya pytest -m integration tests/integration/test_laya.py` | 5 passed in 32.63 s; no skips |
| HOSTED RUN | `ubuntu-latest`, Python 3.12.3, `laya==0.3.28` from the frozen lock, tree T0 (`39c75a2`, identical `src/`), workflow `native.yml` run [37719743745](https://github.com/ajaysurya1221/actseal/actions/runs/37719743745) dispatched 02:49 UTC | the workflow's `uv run --frozen --extra laya pytest -m integration tests/integration/test_laya.py` step | 5 passed in 33.12 s; job `native-linux` success |

Both runs exercise the real pinned checkpoint from the local cache with the library offline
flags set, so a missing prerequisite would have failed, not skipped. They establish that the
changed reply-validation path loads, answers and closes the pinned model on the two documented
CPU platforms; they do not broaden native support beyond the tested configurations.

## Executor-reported results (tree T2) — EXECUTOR REPORT

| Command | Result |
|---|---|
| `uv run --frozen python tools/check_release.py docs` | exit 0 |
| `uv run --frozen python tools/check_release.py workflow` | exit 0 |
| `uv run --frozen python tools/check_release.py receipts` | exit 1, expected before publication: three unmet requirements, all naming the missing `plan/v1/releases/1.0.1/` receipt files |
| `uv run --frozen python tools/check_release.py candidate` | exit 1, expected on an uncommitted tree: `git working tree must be clean` only |
| `uv run --frozen ruff check . && uv run --frozen ruff format --check .` | all checks passed; 480 files already formatted |
| `uv run --frozen mypy --strict src tests` | no issues in 106 source files |
| `uv run --frozen pytest -m "not integration and not packaging" -q` | 4216 passed, 1 skipped, 31 deselected |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict passed |
| `uv build --no-sources` then `tar tzf` of the sdist | `plan/v1/releases/1.0.1/FINAL_REPORT.md` and `RELEASE_NOTES.md` present |
| packaging tests against that build (`ACTSEAL_TEST_DIST`, `ACTSEAL_TEST_WHEEL`) | 25 passed, 4223 deselected |
| `uv lock --check --offline` | exit 0 |
| secret scan of the tree | clean |

The executor also reported that the diff over `src/`, `docs/assets/`, `plan/v1/PLAN.md`, the
1.0.0 receipts and documents, `.github` and the statistical contract is empty, that the audit
archive is in the sdist (21 of 21 files) and that the wheel holds only `actseal/` and its
dist-info.

## Orchestrator re-runs

| Tree | Command | Result |
|---|---|---|
| T1 | `check_release.py docs`, `workflow` | exit 0, exit 0 |
| T1 | ruff check and format, `mypy --strict src tests` | passed; no issues in 106 files |
| T1 | `pytest -m "not integration and not packaging" -q` | 4202 passed, 2 skipped, 31 deselected |
| T1 | `pre-commit run --all-files` | passed |
| T2 + `docs/versioning.md` edit | `check_release.py docs`; `pytest tests/docs tests/unit/test_stability.py tests/release` | exit 0; 850 passed, 1 skipped |
| T3 | see "Final verification" below | |

## Reviews

- First review (R-REL1, on T1): REJECT as tag-ready. Blocker: receipt-path selection and the
  1.0.1 scope notes belong before the tag. Should-fixes: README recording sentence, ADR 0019
  fingerprint clause, merged hero bullets, V1-059 heading level. All applied (T1 → T2).
- Second review (R-REL1b, on T2 plus the `docs/versioning.md` edit): REJECT as the complete
  tag-ready tree. Blocker: the changed native path needs its own cached-native receipt before
  release. Should-fixes: attribute the report's verification claim to a committed record;
  mark the stale "Pending" checkpoint in `docs/assets/src/recording.md` historical. All
  applied (→ T3): the receipts above, this record, and the checkpoint note.
- The third review's verdict and the hosted CI run ids for the pull-request head and the
  merged commit are recorded in the acceptance ledger.

## Final verification (tree T3) — ORCHESTRATOR RE-RUN

Appended after the commands ran; the tree they ran on differs from the committed tree only by
this section's results.

| Command | Result |
|---|---|
| `uv run --frozen python tools/check_release.py workflow` | exit 0 |
| `uv run --frozen python tools/check_release.py docs` | exit 0 |
| `uv run --frozen ruff check .` | all checks passed |
| `uv run --frozen ruff format --check .` | 481 files already formatted |
| `uv run --frozen mypy --strict src tests` | no issues in 106 source files |
| `uv run --frozen pytest -m "not integration and not packaging" -q` | 4216 passed, 1 skipped, 31 deselected in 95.80 s |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict passed |
| `uv build --no-sources` and `tar tzf` of the sdist | wheel and sdist built; the sdist contains `plan/v1/releases/1.0.1/FINAL_REPORT.md`, `plan/v1/releases/1.0.1/RELEASE_NOTES.md` and this record |
| packaging tests against that build (`ACTSEAL_TEST_DIST`, `ACTSEAL_TEST_WHEEL`) | 25 passed, 4223 deselected in 23.83 s |
| `uv lock --check --offline` | exit 0 |
| `uv run --frozen python tools/check_release.py receipts` | exit 1, expected before publication: the three missing `plan/v1/releases/1.0.1/` receipt files only |
| `git diff --quiet HEAD -- src` | `src/` unchanged against `39c75a2` |
| secret scan of the tree | clean |

The candidate gate's clean-tree check is run on the merged release commit before the tag is
created; its result and the hosted CI run ids belong to the acceptance ledger.
