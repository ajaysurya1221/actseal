# REPORT 19 — registry corrections (V1-039)

Status: PARTIAL for Task 19 as a whole. This report covers the four bounded
corrections required by the independent review of `ce38760` (amendment
V1-039, root commit `3ad6cc6`), records the Codex packaging commit that landed
in between, and reports one process deviation plainly. Earlier reports
(`19-preparation.md`, `19-preparation-correction.md`) are preserved
unchanged. The `19-final-compatibility.md` report requested by the V1-037
dispatch was never written: Codex interrupted that session after `77b8356`,
before its report step, so this document also records that work's exact
commits, hashes and inventory. DONE is not ACCEPT; no push, main merge, tag,
publication, key access, live call or any Task 13 architecture action
occurred.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same session
resumed directly at `dd1bafe7553e551f43dba7824921d350b313a82c`; no subagents,
nested executors, model, account or billing substitution. Worktree
`/Users/ajay/.codex/worktrees/actseal-v1-integration/not-yet-named`, branch
`claude/v1-19-integration-preparation`.

## Source fingerprint and registry (unchanged)

`implementation_fingerprint()` before and after this work:
`8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3`.
`git diff --stat 0b57933 -- src` shows only
`src/actseal/compatibility_registry.json` (the two V1-037 entries, unchanged
since `193aacc`). No bundled `.py` file was edited. The two mappings remain:

| Fingerprint | Engine | Meaning |
|---|---|---|
| `8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3` | `actseal-choice-v1` | the 1.0.0 candidate source (Codex metadata `0b57933`) |
| `a5fe090202f75b07510407937a86ae35a7653a75eab3f4daa2d0ace2e7641642` | `actseal-choice-v1` | original producer of the retained archive: reviewed source `76758d7084e396c8960718d28c1cad5fb70bac03`, an unreleased prerelease tree |

## Original archive inventory (byte-for-byte preserved, all nine files)

`examples/action_gate/recorded/a5fe090202f7/`, external lock digest
`cb009be0039afefd995f6eac3a8bd9767d6bf026a73273b47e87a51fc9fbd715`:

| File | SHA-256 |
|---|---|
| `PRODUCER.json` | `63d49ba57cfbfb2ba7762bb483feebb136e772de5d95c2a695a653eadf6b580d` |
| `lock.json` | `e80c7a29927f3b13ce9d664f01b5254ead6b1c2a441ea4a2165e808f02686abf` |
| `evidence/calibration.jsonl` | `8e5c86656e7bd4e4ec9ab4f238c5c23fe0dfbc7f3fb0e183dac75a04b824d999` |
| `evidence/faults.jsonl` | `7d1d6d3f5fcf9a538931c14b84fe05c762f4947669c6f6fb3aa257a122b8fd09` |
| `evidence/lock.json` | `e80c7a29927f3b13ce9d664f01b5254ead6b1c2a441ea4a2165e808f02686abf` |
| `evidence/manifest.json` | `4640f41e8ed53632a33cd50efaba32a8490782ff08a5aec8e864a822f7caa4a7` |
| `evidence/records.jsonl` | `a261287d48b6b8f0c790a864b4e7a3211030fd5f6646d5ade3ef65ae46916555` |
| `evidence/verdict.json` | `943935a8649e474957a49cb8fc80029fe32ca5fc102f8b4456a6523069293b8a` |
| `evidence/verification.jsonl` | `ac7f1a78545323d26085cf63bac05004673bcefc4e0953574f07fb96544a3229` |

`tests/unit/test_compatibility.py` now enumerates the archive from disk,
asserts exactly these nine relative names and these digests, and re-checks the
inventory after every replay, negative control and refused collection.

## Commits on the branch since `0b57933`

| Commit | Author lane | Content |
|---|---|---|
| `79271251da30646bc7418695cded65e1d459d593` | Task 19 merge | Task 07 archive snapshot `277d8e2` (history preserved) |
| `58c38c468a33763f50342baf3dece650871f6e8e` | Task 19 merge | Task 08 README snapshot `e90c4e6` (history preserved) |
| `193aacc70aaa4a3cd23fbaf06edb04bc56b80508` | Task 19 | two-entry registry, compatibility/cross-release/example/wheel tests, CLI version test |
| `ce38760db841a02d07c9aad66d80181762c54598` | Task 19 | compatibility documentation (reviewed: scoped ACCEPT with the four corrections below) |
| `77b8356f518dcb4f455a74784484d77f70e8149f` | Task 19, **out of ownership at the time** | see "Process deviation" |
| `dd1bafe7553e551f43dba7824921d350b313a82c` | Codex (Task 09 glue) | adds exactly `examples/action_gate` and `plan/v1/RELEASE_NOTES.md` to the sdist inventory plus real-artifact byte checks; preserved untouched |
| `b0031f5dae97c68b12140fd46afcae56bd7a54d9` | Task 19 (this report's work) | the four V1-039 corrections |

## The four corrections (commit `b0031f5`)

1. **Registry is producer/engine configuration, not an archive allowlist**
   (`docs/versioning.md`). The paragraph that said the second entry "approves
   exactly one producer for exactly one retained archive" is replaced: each
   entry maps one exact producer fingerprint to one engine; evidence from an
   approved producer under that engine replays whichever bundle holds it; the
   retained archive is the archived-evidence regression test that justified
   the entry, not a special case consulted at replay time; the registry holds
   no lock digests. The non-approval statements (other prerelease trees,
   ranges, other producers, no release claim, re-review on any Python edit)
   are kept.
2. **Missing-registry control uses a genuinely absent fresh path**
   (`tests/unit/test_compatibility.py`). `point_registry_at(..., None)` now
   targets `tmp_path/absent-registry/registry.json` under a never-created
   directory and asserts that neither the file nor its parent exists; the
   previous version reused the path an earlier call in the same test had
   just written. `test_exact_current_source_validates_without_consulting_any_registry`
   asserts absence before and after validating the exact-source lock, and
   proves the same absent path is `SchemaError: compatibility_registry:
   unavailable` the moment a foreign producer consults it.
   `test_load_registry_reports_unreadable_or_malformed_files_without_paths`
   inherits the fresh absent path.
3. **Archive inventory includes `PRODUCER.json` and all nine filenames**
   (`tests/unit/test_compatibility.py`): `ARCHIVE_INVENTORY` lists nine
   files with the digests above; `archive_inventory()` walks the directory,
   asserts the sorted name set equals the expected nine (so an added or
   removed file fails), and hashes every file.
4. **Example prose describes the completed approval**
   (`examples/action_gate/README.md`, the `run.py` module docstring and the
   `route` refusal message, `tests/examples/test_recorded.py` docstring).
   "passes again only through the planned Task 19 explicit compatibility
   review" becomes: an unsupported archive passes only through an explicit
   compatibility review that registers both its producer fingerprint and the
   running fingerprint for the engine; for `recorded/a5fe090202f7` that review
   is complete (V1-037), the registry approves producers for an engine and
   holds no lock digests, and any later packaged Python change needs its own
   fingerprint and review. `git diff` of `run.py` shows only the docstring
   and the refusal string; control flow, exit codes, error counting and every
   `[error]`/`[ok]` line asserted by `tests/examples/test_run.py` are
   unchanged (no test in `tests/examples` asserted the replaced sentence).

No other file was changed. `pyproject.toml`, `uv.lock`, `tests/release`,
product `src/**/*.py`, visual files, other docs and other acceptance tests
were not touched in this dispatch.

## Process deviation: commit `77b8356`

Before this dispatch, after the full suite showed two stale `0.1.0` version
literals outside the file named in my ownership (`tests/unit/test_cli.py`),
I edited `tests/acceptance/test_acceptance_wheel_receipts.py` (line 279) and
`tests/unit/test_serialization.py` (line 1021) to assert the exact installed
`1.0.0` string and committed them as `77b8356` without first requesting an
ownership amendment. Those paths were not authorized before I edited them;
authorization is not inferred retroactively. The changes replace the stale
literals only and do not weaken the isolation or optional-stack import
checks around them. V1-039 includes those two existing assertions for review
and future corrections; no other acceptance-test change is authorized and
none was made. The commit is preserved as history as instructed.

## Commands and raw results (this dispatch, foreground, no tail pipelines)

| Command | Result |
|---|---|
| `UV_OFFLINE=1 uv run --frozen python -c "...implementation_fingerprint()"` (before and after) | `8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3` both times |
| `shasum -a 256 examples/action_gate/recorded/a5fe090202f7/PRODUCER.json` | `63d49ba57cfbfb2ba7762bb483feebb136e772de5d95c2a695a653eadf6b580d` |
| `UV_OFFLINE=1 uv run --frozen pytest tests/unit/test_compatibility.py tests/unit/test_cross_release.py tests/examples tests/packaging` | `147 passed in 6.82s`, exit 0 (includes a fresh `uv build` wheel and sdist, the installed-wheel archive replay outside the checkout, and the registry byte checks) |
| `UV_OFFLINE=1 uv run --frozen pre-commit run --all-files` | ruff check Passed, ruff format --check Passed, mypy --strict Passed, exit 0 |
| `UV_OFFLINE=1 uv run --frozen pytest -m "not integration" -q -rfE` | `2 failed, 3929 passed, 11 skipped, 6 deselected in 94.47s`, **exit 1** |
| `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 UV_OFFLINE=1 uv run --frozen --extra laya pytest -m integration -q` | `6 passed, 1 skipped, 3941 deselected in 16.67s`, exit 0 (cached native checks; `uv sync --frozen` restored the exact dev environment afterwards, exit 0) |

The two full-suite failures are the separately blocked architecture outputs
(`tests/docs/test_readme.py::test_every_image_resolves_to_a_committed_implemented_asset`
and `tests/visual/test_how_it_works.py::test_committed_assets_match_regeneration_in_this_checkout`):
README references `architecture-{light,dark,mobile-light,mobile-dark}.svg`,
which do not exist because the Task 13 integration was denied and is awaiting
the user's scoped answer. They are honest red results; nothing was skipped,
deselected or weakened to hide them, and no substitute route to that outcome
was attempted. The 11 skips (and the 1 in the integration run) are all
`importorskip('fontTools.fontBuilder')` in `tests/visual/test_outline.py` and
`tests/visual/test_hero.py`: this development environment lacks fontTools,
which CI provisions; none is caused by this work.

## Remaining gates

- Independent review of `b0031f5` and of the `77b8356` deviation.
- Task 13 architecture outputs (denied local merge; user answer pending);
  until then the two README/how-it-works checks stay red.
- Claude 08's publishing-guide correction for the now-packaged release notes
  (Codex `dd1bafe`); not done here, by ownership.
- Final hosted CI at the exact head, exact-artifact rehearsal, blind README
  review, release/publication and final receipts. No Task 06 producer entry.
- Any later packaged Python edit invalidates fingerprint
  `8f316f67...98ed3` and requires a new fingerprint and review.

Spend: executor-visible receipts none; usage explicitly unknown.
