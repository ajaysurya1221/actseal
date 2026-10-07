# REPORT 09 — Linux recording-renderer probe (amendment V1-040)

Status: DONE for the CI glue and offline regressions. The real hosted probe
has not run: this macOS host is not `linux-x86_64`, and the manifest in this
worktree carries no Linux agg artifact, so no Linux usability is claimed.

Executor: Claude Code, model `claude-fable-5-1`, effort high, directly on
`claude/v1-09-release` from head `c0a183c`. No subagents, nested executors,
model or billing changes, key access, live inference, network, downloads,
pushes, merges, tags or publication. Owned paths only: `.github/workflows/ci.yml`,
`.github/workflows/publish-pypi.yml`, `tools/check_release.py`,
`tests/release/`. The tool manifest, the toolchain package, product source and
other lanes are untouched; no new pin was added.

## Changes

- **Workflows.** Both `assets` jobs now provision the third pin
  (`setup_tools.py --tool agg`) in the single provisioning step, then run a
  separate unconditional step `uv run --frozen python tools/check_release.py
  agg-version` before regeneration. Order: install → (ordinary CI: visual
  tests) → provision → probe → regenerate. No `if`, `continue-on-error`,
  custom `shell` or shell escape.
- **Helper `agg-version`.** Imports the accepted toolchain's `tools` module
  lazily from `docs/assets/src` (the helper stays stdlib-only for every other
  command, including the container `postpublish`). Requires the actual
  platform key to be `linux-x86_64`; loads and validates the manifest (default
  `docs/assets/src/tools.toml`, `--manifest` override for tests); requires the
  `agg` tool to be a binary at the approved version 1.9.0 with a
  `linux-x86_64` artifact; calls `verified_binary` (hash re-verified
  immediately before execution) and then
  `run_tool([binary, "--version"], timeout=10)`; requires the stripped stdout
  to equal exactly `agg 1.9.0`. On success it prints `agg_version`,
  `platform`, `agg_artifact_sha256` and `agg_binary` as `key=value` lines and
  a stderr line naming the approved manifest artifact hash. Missing toolchain,
  wrong platform, invalid or pinless manifest, wrong version pin, missing
  cache, tampered binary, nonzero exit, timeout and wrong output all fail
  explicitly. Nothing executes before the hash check passes.
- **Workflow checker.** `_check_assets_job` now requires the exact install,
  three-command provisioning, probe and regeneration commands once each, in
  that order, with no conditional or ignored-failure escape on the job or
  those steps, setup_tools invoked only in the provisioning step and the probe
  exactly once. It is shared by the publish `workflow` command and, with the
  renderer regeneration command, by the ordinary CI test.
- **Tests.** `tests/release/test_agg_probe.py` (21 tests, offline): positive
  path with a local double pinned by its own hash and the toolchain's
  `platform_key` patched to Linux; CLI output; stdlib-only import guard; every
  failure path above including tamper rejection before execution (the double
  writes a marker when run) and the honest `no linux-x86_64 artifact` result
  for this worktree's manifest. `test_check_release_workflow.py`: the
  provisioning-order test now expects three commands plus the separate probe
  for both workflows and applies the shared checker; ten ordinary-CI
  mutations and eleven publish mutations (agg omitted, provisioning
  reordered, probe omitted/conditional/ignored-failure/`|| true`/duplicated/
  after regeneration, job conditional or ignoring failures, provision `shell`)
  each fail with their specific message. All earlier mutations and
  diagnostics are preserved (`assets-gate-missing` and `assets-no-group`
  fragments follow the new exact-command wording).

## Tests

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/release` | 600 passed in 17.13 s (61 new) | 0 |
| `uv run --frozen python tools/check_release.py workflow` | no output | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict Passed | 0 |
| `uv run --frozen mypy --strict tools/check_release.py` / `src tests` | Success: 1 / 79 source files | 0 |
| `uv run --frozen ruff check .` / `ruff format --check .` | all checks passed / 302 files already formatted | 0 |
| `uv run --frozen pytest tests/visual` | 204 passed (the shared toolchain import disturbs nothing) | 0 |
| `uv run --frozen python tools/check_release.py agg-version` | `agg probe requires an actual linux-x86_64 runner; running on darwin-arm64` | 1 |
| `git diff --check` | clean | 0 |

## Honest status of the Linux probe

- This worktree's `docs/assets/src/tools.toml` has only the `darwin-arm64`
  agg artifact; reviewed main `7820dba` carries the approved `linux-x86_64`
  pin (`agg-x86_64-unknown-linux-gnu`,
  `f111e315cd71056b116302342553dd765b7297579ed511f111d0cedb442aeda6`). I did
  not edit the manifest or merge that branch. On this branch as-is, the hosted
  `assets` jobs would fail at `setup_tools.py --tool agg` with "no pinned
  artifact for platform linux-x86_64", which is the intended fail-closed
  behaviour until independent integration brings the manifest in.
- A matching hash and `agg 1.9.0` output prove consistency with the approved
  pin only. Actual hosted execution has not been recorded; GIF rendering and
  Task 14 are not established by this probe.
- Tests use local doubles and never download or execute the real binary.

## Open issues

- Hosted execution of the probe after integration with the manifest on main;
  the real P1 assets, authorized authoring setup and the non-publishing
  rehearsal remain pending and Codex-owned.
- Independent review of this bounded series is required.

## Spend

No paid inference API calls, no Jev credits, no downloads. Claude subscription
usage is not metered here and is not claimed as free.
