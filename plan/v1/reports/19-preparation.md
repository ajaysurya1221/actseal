# REPORT 19 (early integration preparation)

Status: PARTIAL. This is the Task 19 preparation candidate authorized by the
recorded amendment (V1-032 at Codex commit `6a54650`): the three reviewed
snapshots are merged locally with history and authorship preserved, the
experimental Jev provider is registered behind the explicit opt-in, and the
stale tests/docs are updated atomically. Final source/version freeze, exact
producer registry approval, the unchanged Task 07 archive replay, any Task 06
producer approval, final provider inclusion, native checks, exact-head hosted
CI and full Task 19 ACCEPT remain outstanding. DONE is not ACCEPT; no main
merge, push, tag, registry entry, version/classifier/lock edit, shipped-Jev
or live-capability claim follows from this report.

Executor: Claude Code, model `claude-fable-5-1`, effort high, run directly;
no subagents or nested executors, no model, account or billing substitution.
Isolated worktree `/Users/ajay/.codex/worktrees/actseal-v1-integration/not-yet-named`,
branch `claude/v1-19-integration-preparation`, started at reviewed main
`20b996917c25111bc9b043f22db000be0ff8fcdc` (confirmed with `git rev-parse`
before the first merge). Python 3.12, uv frozen, macOS arm64, `UV_OFFLINE=1`
on every command. No `.env`, `.env.example`, key or credential access; no live
request; no socket opened by any test (`JEV_API_KEY` is unset and the
adapter's environment read and connection factory are forbidden in every new
CLI test). No read or copy of the active Task 06/15 worktrees. No Task 07
archive imported, excluded or registered. No shared STATE/REVIEW file edited.

## Integrated commits (local merges, in order)

| Merge commit on this branch | Snapshot merged | Content |
|---|---|---|
| `aab0674147c929478032233516e0d0bf83c8ddab` | Task 05 `c2e27d2235eb98be0f97c9ec6d38b0c8ff235dfa` | Experimental stdlib Jev transport, `records.PROVIDERS` admission, pure Jev normalization profile, Jev-native fault envelopes, schema enum updates, Task 05 reports. Ten commits (`f7439f5`..`c2e27d2`), authorship preserved. |
| `8487160fcc635e6c2f7d86beb93cf55c69efddc0` | Task 08 `eb21e8738d1f529d0e06223203e4266f1c495218` | Concepts/CLI/Python/FAQ reference pages, ADRs 0017-0020, SECURITY/CONTRIBUTING/AGENTS updates, `tests/docs`, Task 08 reports. Thirteen commits. |
| `e81f6782c79b28f46376d84ca2d6b413c8b1d8ef` | Task 09 `c0a183c5fe95e1e7e21e193b64f0e31c2584de66` | Release pipeline, `tools/check_release.py`, three release-receipt schemas, `tests/release`, sdist inputs (`tools/check_mutations.py`, `examples/action_gate/` via `8acbf38`, v1 documentation inputs via `c0a183c`), ADR 0016, Task 09 reports. Sixteen commits, including reviewed `8acbf38`. |

All three merges completed with `git merge --no-ff --no-edit` and **no
textual conflict**. The expected `docs/schemas/README.md` overlap auto-merged
because Task 05 (provider enum / Jev body profile) and Task 09 (release
receipts section and table) touched different regions; after the merge the
file contains the Jev body profile paragraph and all three release-receipt
rows (`build-receipt`, `postpublish-receipt`, `release-receipt`), verified by
`grep` and by `tests/unit/test_schemas.py::test_schema_readme_lists_every_file`.
No ours/theirs resolution was used anywhere. Task 09's packaging and release
machinery (`pyproject.toml` sdist inventory, workflows, helper, byte tests)
is unchanged by this task; the only `pyproject.toml` delta on the branch is
Task 09's own.

Post-merge baseline before any Task 19 edit: the focused suite had exactly one
failure, the known stale
`tests/docs/test_policy_and_metadata.py::test_providers_doc_describes_jev_as_unshipped_and_experimental`
(`PROVIDERS` now admits `jev` and the experimental module exists).

## Task 19 commits

| Commit | Subject | Files |
|---|---|---|
| `2596204fb8908561c16e90e2b4ebcf5c9400663a` | feat(cli): register the experimental Jev provider behind --experimental-provider | `src/actseal/cli.py`, `src/actseal/runner.py`, `tests/unit/test_cli.py`, `tests/unit/test_runner.py`, `tests/unit/test_stability.py`, `tests/docs/test_cli_reference.py`, `docs/cli.md`, `docs/stability.md` |
| `0d85fc76b31960b3233d3da270ac06a9103d558a` | docs(providers): classify Jev as a PROVISIONAL explicit opt-in, mocked only | `docs/providers.md`, `docs/python-api.md`, `docs/faq.md`, `docs/schemas/README.md`, `tests/docs/test_policy_and_metadata.py` |

Implementation fingerprint at `0d85fc7`:
`1fd27c3c83e79c26ba10629fc006d4ea17b225fceea1fdb1edf5b4f8518f0f2b`. The
packaged registry (`src/actseal/compatibility_registry.json`) is still empty;
no registration or approval is requested. The version remains `0.1.0`; Codex
retains version/classifier/lock edits.

## Runner and CLI behaviour (frozen for this phase)

- `runner.open_model(provider, *, responses, offline)` signature unchanged.
  Branches are now explicit per provider: `fixture` (requires `responses`),
  `laya` (rejects `responses`), `jev` (rejects `responses`; lazy
  `from actseal.experimental.providers.jev import JevModel` inside the branch;
  `JevModel(offline=offline)`), and a final unreachable `SchemaError` so a
  registered name without a branch can never build Laya. The V1-011 guard
  (`PROVIDERS` admission vs `_REGISTERED_PROVIDERS` registration) is kept;
  `_REGISTERED_PROVIDERS` is now `{fixture, laya} | _EXPERIMENTAL_PROVIDERS`
  with `_EXPERIMENTAL_PROVIDERS = {jev}`. The explicit Python string `"jev"`
  is the opt-in. `verify_run` still requires the requested provider to equal
  the locked provider before the factory; `IntegrityError` for a Jev lock with
  a stable provider and vice versa.
- `cli`: `--provider` choices are `{fixture,laya,jev}`; `_PROVIDERS` (stable)
  stays `("fixture", "laya")`, `_EXPERIMENTAL_PROVIDERS = ("jev",)`. New
  `--experimental-provider` (store_true) on `lock` and `verify` only.
  `_check_provider_options` runs before any input read or provider build:
  `jev` without the flag -> `usage: --experimental-provider is required with
  --provider jev`; the flag with `fixture`/`laya` -> `usage:
  --experimental-provider is not accepted with --provider <provider>`;
  `--responses` with `jev` -> `usage: --responses is not accepted with
  --provider jev`. All are versioned ERROR 3 receipts (`schema_version` 1,
  `command`, `status: ERROR`). `replay`/`demo` reject the flag as
  `unrecognized arguments` (ERROR 3). `jev --offline` reaches the adapter and
  is `ProviderSetupError: offline: the experimental Jev adapter has no offline
  mode; no request was made` (ERROR 3) before any environment read. No receipt
  field was added; receipt shapes, exit codes and the stable signatures are
  unchanged (`tests/unit/test_stability.py` oracles pass with only the
  `--experimental-provider` inventory addition).
- Import discipline: `import actseal.cli` loads nothing under
  `actseal.adapters`, `actseal.experimental`, `http` or `ssl`; replay of a Jev
  bundle succeeds with `actseal.adapters`, `actseal.experimental`, `http`,
  `ssl`, `subprocess`, the native stack and sockets denied.
- The `--provider` invalid-choice diagnostic now lists `fixture, laya, jev`;
  the raw argv sentinel tests still prove no value is echoed. The
  `_check_provider_options` messages interpolate only the validated argparse
  choice, never a raw token.

## Tests replaced or added

- `tests/unit/test_runner.py`: removed the two stale tests that required every
  Jev construction to fail (`..._rejects_admitted_but_unregistered_jev...`,
  `..._jev_rejection_imports_no_adapter...`). Added
  `test_open_model_routes_jev_to_the_experimental_adapter_never_to_laya`
  (fake Laya and fake Jev constructors; exact registration inventory;
  `responses` rejected before either),
  `test_open_model_rejects_an_admitted_but_unregistered_provider_before_any_adapter`
  (admitted `other`, and `jev` with registration monkeypatched away, both
  `not registered` with nothing constructed; `unsupported` still rejected),
  `test_open_model_jev_imports_lazily_and_fails_before_any_key_read_or_socket`
  (fresh `-I` interpreter with socket and `JEV_API_KEY` reads blocked:
  `responses` rejected before import, offline rejected by the adapter before
  the key, online path's first observable event is the blocked key read; no
  Laya/torch module loads) and
  `test_jev_lock_verify_replay_round_trip_over_a_fake_transport` (real
  `JevModel` over the conformance fake connection through `open_model`;
  lock identity `jev`/`jev-1.13.0`/empty artifact hashes; all 6 cases
  captured verbatim; `assess` and `replay` agree; Laya against the Jev lock
  refused before the factory). `test_open_model_fixture_rules` now expects
  `responses` rejection for `jev` instead of provider rejection; the existing
  `test_admitted_jev_provider_against_a_fixture_lock_is_rejected_before_the_factory`
  is kept.
- `tests/unit/test_cli.py`: `USAGE_ERRORS` gains the three replay/demo/root
  flag rejections; help assertions cover the flag and the choices on
  lock/verify and their absence on replay/demo; invalid-choice messages
  updated. New: parametrized
  `test_experimental_flag_rules_are_usage_errors_before_any_provider_or_environment`
  (12 cases over lock/verify with `open_model`, `lock_run`, `verify_run`, the
  key read and the connection factory all forbidden; text and JSON receipts;
  nothing written), `test_jev_offline_is_a_setup_error_before_the_key_is_read`,
  `test_jev_cli_round_trip_over_a_fake_transport` (lock/verify/replay receipts
  byte-shape-equal to the fixture receipts; 128 mocked requests; exit code
  equals the recomputed verdict; isolated replay with the experimental package
  denied) and `test_jev_lock_refuses_stable_providers_missing_opt_in_and_offline`.
  `test_importing_the_cli_loads_no_adapter` now also denies
  `actseal.experimental`, `http` and `ssl`.
- `tests/unit/test_stability.py`: `--experimental-provider` added to the
  lock/verify option inventory; every other oracle (signatures, receipts,
  constants, `PROVIDERS == {fixture, laya, jev}`) unchanged.
- `tests/docs/test_cli_reference.py`: new
  `test_documented_experimental_flag_restrictions_match_the_cli` (table rows,
  prose rules and the actual usage errors per command). The existing
  usage-line and option-table tests now pass against the regenerated
  signatures in `docs/cli.md`.
- `tests/docs/test_policy_and_metadata.py`: the stale "unshipped" test is
  replaced by
  `test_providers_doc_distinguishes_stable_providers_from_provisional_jev`
  (exact `PROVIDERS`, stable vs experimental CLI tuples, importable module,
  required and forbidden phrases in providers/python-api/faq/cli/stability).
  It does not infer live capability from mocks.

## Documentation

- `docs/cli.md`: signatures regenerated from the actual help
  (`{fixture,laya,jev}`, `[--experimental-provider]`), option table and rules
  state the opt-in, rejection, offline, replay/demo and receipt-shape facts.
- `docs/stability.md`: lock/verify rows keep the STABLE
  `--provider {fixture,laya}` in the Required column and note the PROVISIONAL
  `--provider jev` with `--experimental-provider` in Optional; the provider
  rules paragraph replaces "not part of this task's deliverable" with the
  actual rules and the no-promise statement. Review-sensitive choice: the
  manifest table deliberately shows the stable set, while `docs/cli.md`
  mirrors the help verbatim.
- `docs/providers.md`: the "conditional experimental work, not shipped"
  section is replaced by "Jev: PROVISIONAL experimental provider, explicit
  opt-in only": selection rules, fixed execution profile, identity (vendor
  claim, empty artifact hashes), credential handling and the echo guard's
  limits, capture/normalization profile and status mapping, and an explicit
  verification status: **no live Jev request has been made or verified; all
  Jev tests are mocked**, not part of the default quickstart/demo/stable set,
  registry and live audit remain separate decisions. Fallback and MCA
  paragraphs preserved unchanged.
- `docs/python-api.md`, `docs/faq.md`: "accepts exactly these two / only
  those two" and "not shipped" wording replaced with the stable-plus-provisional
  boundary; `open_model("jev", ...)` named as the Python opt-in. Python fences
  are unchanged (the docs test still forbids `experimental` in examples).
- `docs/schemas/README.md`: one sentence updated (CLI registration behind the
  flag; stable choices unchanged; no receipt field added). Jev body profile
  and all three release-receipt sections preserved.

## Commands and results

| Command | Result |
|---|---|
| `UV_OFFLINE=1 uv run --frozen pytest tests/unit/test_cli.py tests/unit/test_runner.py tests/unit/test_stability.py tests/unit/test_compatibility.py tests/unit/test_cross_release.py tests/unit/test_schemas.py tests/conformance tests/docs tests/release` | `1092 passed in 22.95s` (exit 0) at the working tree later committed as `0d85fc7`; post-merge baseline before edits was `1 failed, 451 passed` with `-x` on the stale docs test |
| `UV_OFFLINE=1 uv run --frozen pre-commit run --all-files` | `ruff check` Passed, `ruff format --check` Passed, `mypy --strict` Passed (exit 0) |
| `UV_OFFLINE=1 uv run --frozen pytest -m "not integration"` | `3812 passed, 1 skipped, 6 deselected in 88.57s` (exit 0) at the tree committed as `0d85fc7`. The single skip is pre-existing and environmental: `tests/visual/test_outline.py` module-level `importorskip` (`No module named 'fontTools'`; the dev group here lacks it, CI provisions it per the checklist). The 6 deselected are the `integration` marker. No test was skipped, weakened or deselected by this task. |

Manual probes during development (all ERROR 3, nothing written): `python -m
actseal lock ... --provider jev` (missing opt-in), `... --provider jev
--experimental-provider --offline` (`ProviderSetupError: offline`),
`... --provider fixture --responses ... --experimental-provider`, and
`replay`/`demo` with the flag. `ruff format` was applied to the edited test
files; no other tool modified files. Native, integration-marker, mutation,
visual regeneration, packaging rehearsal and hosted CI were not run: they are
later gates.

## Deviations and open issues

1. **Stale Jev wording outside the owned documents** was left untouched and
   needs its owner/Codex: `README.md:87` ("Jev is deferred, not a v0.1.0
   dependency"), `docs/dependencies.md:193` ("optional v2 service adapter"),
   and ADR 0017 "Consequences" ("until Task 19 integrates the experimental
   flag", "Accepted main carries neither change yet", "describes Jev as
   conditional preparation, not shipped behaviour"). The README is a later
   Task 19 phase; the ADR is a dated record and may warrant a short status
   amendment rather than a rewrite.
2. **Diagnostic wording changes** (nonsemantic): `open_model` now says
   `responses: not accepted by the <provider> provider` for both laya and jev
   (was the literal laya text); the CLI invalid-choice hint lists `jev`.
3. **`docs/stability.md` table shape** (see above) is a judgement call;
   `docs/cli.md` is the verbatim-help reference and is tested as such.
4. **Mocked only.** Every Jev assertion runs over the conformance fake
   connection or an injected exchange. Nothing here evidences vendor
   availability, accuracy, cost or terms; no Jev request was made.
5. **Not done in this phase, by instruction:** Task 07 archive/compatibility
   integration (its 7 red merge-preview tests are neither imported nor
   excluded here), registry entries, version/classifier/lock, final README
   and P1 assets, Task 06/15 changes, native receipts, hosted CI at the exact
   head, main merge.
6. **Branch footprint vs reviewed main `20b9969`:** 47 files beyond the
   three snapshots' own content are not touched; Task 19 edits are confined
   to the 13 owned files listed in the two commits.

## Spend

Executor-visible spend receipts: none available in this session; usage is
explicitly **unknown** and is not estimated. No model, executor, credential
or billing substitution occurred.
