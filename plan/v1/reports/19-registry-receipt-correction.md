# REPORT 19 — registry receipt correction (addendum to `19-registry-corrections.md`)

Status: PARTIAL for Task 19 as a whole, unchanged. This addendum corrects
two receipt defects found by REVIEW 19 (REVISE, receipt only) in
`plan/v1/reports/19-registry-corrections.md`, which is preserved verbatim as
history. Source `b0031f5dae97c68b12140fd46afcae56bd7a54d9` is independently
ACCEPTed; the parent's 172 focused tests plus hooks passed. Nothing in this
addendum changes product, tests, docs or packaging glue, and no command was
re-run for it: every quotation below is taken from the executor's own
private stream record `19-registry-corrections.stream.jsonl` for that
dispatch (tool inputs and captured outputs; no credentials appear in it).

Executor: Claude Code, model `claude-fable-5-1`, effort high, same session
resumed directly at `080a1b6ee909ca0d5d0b9f0d475f093b4b5642ee`; no subagents,
nested executors, model, account or billing substitution; no merge, key
access, live call, push or publication.

## Correction 1: the verdict on `ce38760` was REVISE, not scoped ACCEPT

The commit table in `19-registry-corrections.md` describes
`ce38760db841a02d07c9aad66d80181762c54598` as "reviewed: scoped ACCEPT with
the four corrections below". That is wrong. The independent review of Task 19
at `ce38760` returned **REVISE** with four required corrections (recorded as
amendment V1-039); the scoped ACCEPT came later and applies to the corrected
source `b0031f5`, not to `ce38760`. The earlier report's wording stands as
history; this addendum is the correction of record.

## Correction 2: the commands as actually run, with their real flags and wrappers

The earlier report's heading "raw results (this dispatch, foreground, no tail
pipelines)" and its command table omitted the real flags and wrappers. Each
row below quotes the exact shell line from the stream record and the result
lines it captured. The results themselves are unchanged.

| Exact command | Captured result |
|---|---|
| `UV_OFFLINE=1 uv run --frozen python -c "from actseal.serialization import implementation_fingerprint; print(implementation_fingerprint())"; shasum -a 256 /Users/ajay/.codex/worktrees/actseal-v1-integration/not-yet-named/examples/action_gate/recorded/a5fe090202f7/PRODUCER.json; ls -R /Users/ajay/.codex/worktrees/actseal-v1-integration/not-yet-named/examples/action_gate/recorded/a5fe090202f7` | `8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3`; `63d49ba57cfbfb2ba7762bb483feebb136e772de5d95c2a695a653eadf6b580d  .../PRODUCER.json`; nine files listed |
| `UV_OFFLINE=1 uv run --frozen pytest tests/unit/test_compatibility.py tests/unit/test_cross_release.py tests/examples tests/packaging -q --no-header -p no:cacheprovider; echo "exit=$?"` | `147 passed in 6.82s`, `exit=0` |
| `UV_OFFLINE=1 uv run --frozen pre-commit run --all-files; echo "exit=$?"` | `ruff check ... Passed`, `ruff format --check ... Passed`, `mypy --strict ... Passed`, `exit=0` |
| `git -C ... diff --stat 0b57933710437c6f48f5689a8b73c83db4bca6fd -- src; git -C ... status --short; UV_OFFLINE=1 uv run --frozen python -c "from actseal.serialization import implementation_fingerprint; print(implementation_fingerprint())"` (after the edits) | only `src/actseal/compatibility_registry.json` differs under `src`; `8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3` |
| `UV_OFFLINE=1 uv run --frozen pytest -m "not integration" -q --no-header -p no:cacheprovider -rfE 2>&1 \| grep -v "^\.\+" ; echo "pytest-exit=${pipestatus[1]}"` | `FAILED tests/docs/test_readme.py::test_every_image_resolves_to_a_committed_implemented_asset`; `FAILED tests/visual/test_how_it_works.py::test_committed_assets_match_regeneration_in_this_checkout`; `2 failed, 3929 passed, 11 skipped, 6 deselected in 94.47s (0:01:34)`; `pytest-exit=1` |
| `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 UV_OFFLINE=1 uv run --frozen --extra laya pytest -m integration -q --no-header -p no:cacheprovider; echo "pytest-exit=$?"` | `Installed 30 packages in 436ms`; `6 passed, 1 skipped, 3941 deselected in 16.67s`; `pytest-exit=0` |
| `UV_OFFLINE=1 uv sync --frozen 2>&1 \| tail -1; echo "sync-exit=${pipestatus[1]}"` | `sync-exit=0` (the `tail -1` kept only the last line of uv's package list; the exit status is uv's own, captured through `pipestatus[1]`) |
| `UV_OFFLINE=1 uv run --frozen pytest -m "not integration" tests/visual tests/docs tests/unit/test_serialization.py -q --no-header -p no:cacheprovider -rs 2>&1 \| grep -i "^SKIPPED\|passed\|failed"` | **diagnostic only**: eleven `SKIPPED` lines, all `could not import 'fontTools.fontBuilder': No module named 'fontTools'` (`tests/visual/test_outline.py:11`, `tests/visual/test_hero.py:216/263/270/289[4]/318/337/378`), and `2 failed, 751 passed, 11 skipped, 1 deselected in 3.61s`. The pytest exit status was **not** captured (the grep's status replaced it); this run identifies the skip reasons and is never a done-when result |

Precise statements that replace the earlier wording:

- The three Done-when commands were run in the foreground with the extra
  flags `-q --no-header -p no:cacheprovider` (the full suite also `-rfE`). The
  full-suite line used a `grep -v` filter to drop progress-dot lines and
  captured pytest's own status through zsh `pipestatus[1]`; the saved output
  confirms `2 failed, 3929 passed, 11 skipped, 6 deselected in 94.47s` and
  `pytest-exit=1`. The focused and native runs were not piped; their `$?` is
  pytest's.
- The full-suite exit status is **1**, a failure: the two red checks are the
  separately blocked architecture outputs (Task 13, denied local merge,
  user answer pending). Nothing was skipped, deselected or weakened to hide
  them, and no substitute route was attempted.
- `uv sync --frozen` used `tail -1` and a `sync-exit` capture; it restored the
  exact dev environment after the `--extra laya` run.
- The fontTools skip listing is a diagnostic that explains the eleven skips;
  it carries no exit status and is not claimed as green.

## Unchanged facts

Fingerprint `8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3`
before and after; both V1-037 registry entries; the nine-file original
archive inventory and digests listed in `19-registry-corrections.md`; the
`77b8356` out-of-ownership deviation as reported there; and the remaining
gates (Task 13 outputs, Claude 08's publishing-guide correction, hosted CI at
the exact head, exact-artifact rehearsal, blind README review, publication
and final receipts). Spend: executor-visible receipts none; usage
explicitly unknown.
