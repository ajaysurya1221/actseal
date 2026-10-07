# REPORT 08-readme-preparation

Status: PARTIAL (README, publishing guide, CHANGELOG and release-note
preparation under the ownership/scheduling amendment at `3e32aeb`; full
Task 08 stays PARTIAL until the architecture outputs exist, final
provider/example facts are integrated, every original check passes, actual
rendering is reviewed and the blind ten-second test passes). Candidate for
Codex review; DONE is not ACCEPT.

Executor: Claude Code, model `claude-fable-5-1`, effort high, run directly
(no nested agents or executors, no model, billing or permission change, no
personal memory). Worktree `/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`,
branch `claude/v1-08-readme-completion`, starting at the committed
integration snapshot `e81f6782c79b28f46376d84ca2d6b413c8b1d8ef` (accepted
05 `c2e27d2`, 08 `eb21e87`, 09 `c0a183c` on reviewed main `20b9969`). No
active Task 19 working change was copied. No `.env`, key, provider, network,
push, main merge or publication. Task 19-owned CLI/provider/Python/FAQ/
stability/schema docs, their tests, `tests/docs/conftest.py`, product code,
workflows, packaging and `docs/assets` were not edited.

## Task 15 merge (isolated preparation, not main-merge approval)

`git merge --no-ff --no-edit fcdcfe40f6dbac73ea09b7a1016447646604328c`
completed without conflict as `d75b8f5`. `git diff fcdcfe4 HEAD --stat --
docs/assets tests/visual` is empty: every hero, how-it-works, social, font,
receipt and visual-test byte from the accepted Task 15 commit is carried
unchanged. Committed figures now present: four hero SVGs, four how-it-works
SVGs and `social.png` (1280×640). No semantic conflict arose, so nothing was
resolved by hand.

## Changes (owned paths only)

| File | Change |
|---|---|
| `README.md` | Rewritten to PLAN section D: hero `<picture>` (light/dark/mobile sources) → the exact one-sentence description → four badges (CI workflow, PyPI version, Python versions, licence) → how-it-works `<picture>` → the three PyPI commands verbatim → three guarantees → three limits → architecture `<picture>` → documentation/stability/threat-model/release link table. Every link and image target is an absolute `https://github.com/ajaysurya1221/actseal/blob/main/...` or `raw.githubusercontent.com/.../main/docs/assets/...` URL; every `<img>` carries descriptive alt text taken from the SVGs' own `<desc>`. Windows stated unsupported; version-neutral; no `demo.gif`, no 0.1.0 pin, no publication-state claim. Removed: the 0.1.0 `--from` commands, the 0.17-second timing, "v0.1.0 supports", "Jev is deferred" and the candidate-`434c682` native paragraph (that receipt remains in `docs/providers.md`). |
| `docs/publishing.md` | Rewritten for the reviewed `publish-pypi.yml`: `workflow_dispatch` with no inputs is a rehearsal that never uploads; a `v*` tag push runs build-once, four-platform verification of the exact artifact by ID, asset regeneration, the `pypi` environment approval, Trusted Publishing with `skip-existing: false`, clean-container post-publication verification and a draft GitHub mirror. One-time publisher setup kept. New failure/partial-publication recovery section: nothing re-uploaded, failed runs kept as receipts, `mirror`-only rerun for a missing draft. Retired `publish=true/false` instructions removed without touching the workflow. Rehearsal results explicitly not public PyPI receipts; v0.1.0 history kept. |
| `CHANGELOG.md` | New `## v1.0.0 — unreleased candidate` section (stability/compatibility, providers/verification/examples, platforms/release/documentation) with an explicit pending list; conditional Jev/example items worded as pending; no hashes, totals or live results. v0.1.0 section unchanged. |
| `plan/v1/RELEASE_NOTES.md` (new draft) | How-it-works figure, description, three commands, the 1.0 promise and non-promises, a receipts table with every row `PENDING` (commit/tag, distribution hashes, run/artifact id, matrix, attestations with the non-cryptographic wording, post-publication smoke, classifier, assets, ten-second test, recording), conditional Jev/benchmark/example sections, known limits. Contains no 64-hex hash. |
| `docs/decisions/0017-experimental-decision-provider.md` | Evidence/status paragraph only: on the reviewed source `jev` is admitted in `records.PROVIDERS`/schemas, `open_model` refuses it, the `.env.example` placeholder was verified (V1-029); pending items are the Task 19 CLI opt-in/runner registration, native receipts, inclusion decision and live integration; live behaviour unverified, no request or credit. Decision text unchanged. |
| `docs/decisions/0020-reproducible-visual-assets.md` | Status line and evidence paragraph only: pinned fonts/tools fetched with hash verification under V1-029 (Linux agg pinned, not executed); hero accepted after pixel review; how-it-works ACCEPT `f712dae`; `social.png` delivered, Task 15 done-when passing at `fcdcfe4` with scoped ACCEPT, hosted gate and Codex pixel review pending; architecture outputs, recording, ten-second test, P2 and hosted assets job pending. Decision text unchanged. |
| `tests/docs/test_readme.py` (new) | Section D order; verbatim description, commands, guarantees, limits; four badges; no stale 0.1.0/timing/Jev-deferred wording; no `demo.gif`; every Markdown link absolute and same-repo `blob/main` links resolve; every `<source srcset>`, `<img src>` and Markdown image absolute with alt text; every non-badge image maps to an existing output of an implemented asset in the committed inventory (no HTTP, no skip, no xfail; badge-only exemption preserved); the four frozen architecture filenames; light/dark/desktop/mobile variant order per figure. |
| `tests/docs/test_publishing.py` (new) | No retired `publish=` input in guide or workflow; guide names the actual triggers, environment, `skip-existing: false`, `id-token: write`, artifact-by-ID download, checksum re-check and all six jobs as present in the workflow text; rehearsal-never-uploads, candidate-not-receipt and recovery wording; no v1 publication claim. |

`docs/quickstart.md` and `docs/concepts.md` needed no edit: the quickstart is
already version-neutral with the three commands and the Windows statement.

## Commands and results

Run from the worktree root on the final tree before committing.

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs` | **2 failed, 99 passed** (both expected and listed below) | 1 |
| `uv run --frozen python tools/check_release.py docs` | `docs gate has 1 unmet requirement(s): README.md links to missing file docs/assets/architecture-mobile-dark.svg` (the helper reports the first missing file; all four architecture outputs are absent) | 1 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `uv run --frozen ruff check tests/docs` | All checks passed | 0 |
| `uv run --frozen ruff format --check .` | 359 files already formatted (Markdown fences included) | 0 |
| `uv run --frozen mypy --strict src tests` | Success: no issues found in 94 source files | 0 |
| `uv run --frozen pytest tests/release -k docs` | 34 passed, 525 deselected (helper's own docs-gate tests, unchanged) | 0 |
| in-process `actseal_assets.references.check_references(".", ASSETS)` | 16 references checked; 4 errors, all `architecture-*.svg does not exist`; hero, how-it-works and badge references pass; no orphans | n/a |
| `git diff --check` | no output | 0 |

Before this work, `check_release.py docs` on the snapshot failed with three
requirements (relative README links, missing description, `-f publish=` in
the publishing guide); those three are now satisfied.

Intermediate test-side failures, fixed without weakening: Ruff ISC004/PT018/
PLC0207 on three new test lines; one mypy loop-variable retyping. Not run:
`render.py --check` (would read the operator tool cache and run renderers),
native/mutation/example tests, previews, packaging, network.

## Expected failures and existing assertion conflicts (reported, not edited)

1. **Architecture outputs missing (expected).** `tests/docs/test_readme.py::test_every_image_resolves_to_a_committed_implemented_asset` and `check_release.py docs` fail because `architecture-light.svg`, `architecture-dark.svg`, `architecture-mobile-light.svg` and `architecture-mobile-dark.svg` are not committed and the `architecture` asset has no renderer in the inventory. Task 13 owns those outputs and their registration; the README references the frozen names and will pass once the accepted files land. No draft output was synthesized or copied.
2. **Jev provider assertion conflict (Task 19).** `tests/docs/test_policy_and_metadata.py::test_providers_doc_describes_jev_as_unshipped_and_experimental` fails on this snapshot: accepted Task 05 admits `jev` in `records.PROVIDERS` and `src/actseal/experimental/providers/jev.py` exists, while the test (written for accepted main) asserts exactly `{fixture, laya}` and an absent module, and `docs/providers.md` still says the current source ships no Jev adapter. INTEGRATION_CHECKLIST already assigns the atomic update of these assertions and provider docs to Task 19; neither was edited here.
3. **Demo recording.** No `demo.gif` reference exists; Task 21 adds the genuine post-PyPI capture.
4. **Example archive.** `examples/action_gate/` is not in this snapshot (Task 07 `277d8e2` pending registry integration); the README links no example path, and the CHANGELOG/release-note draft name it as pending.

## Gates still pending for full Task 08

Accepted architecture outputs and their README check; Task 19's final
provider inclusion facts (then README/providers wording and the conflicting
test); Task 07 example integration; `tools/check_release.py docs` green on
the integrated tree; the exact-head hosted CI; actual rendering review of the
README; the blind ten-second test with its prompt, screenshot hash and answer
saved under `plan/v1/reports/`; final release notes with receipts (Tasks
20/21) and the genuine demo recording (Task 14). No v1 tag or publication
exists.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this CLI process; elapsed time unknown until Codex's
  stream result is available. Not estimated.
