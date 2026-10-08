# Actseal v1.0.1 — release report

This report records the implementation and scope of the 1.0.1 patch, what
stayed sealed, the gates that run before the tag and what the tagged
release pipeline records. It is written before the tag; the two values that
only the tagged pipeline produces appear as named placeholders, listed with
every other 1.0.1 placeholder in the
[release notes](RELEASE_NOTES.md#placeholders-filled-after-publication).

| Release field | Value |
|---|---|
| Version | 1.0.1, a patch release of the 1.x line; `pyproject.toml`, `actseal.__version__` and the `uv.lock` self entry agree |
| Tag | annotated `v1.0.1`; `source_commit` `<<build.source_commit>>` |
| Tagged workflow run | `<<build.run_id>>` (`publish-pypi.yml`; release receipt `workflow_run.id`) |
| Implementation fingerprint | `dced01d79e64799a19a75c0957f3684a48249c58ebb27d346336e7420195bcb4`, the approved final fingerprint of the A2b review; it is the third `actseal-choice-v1` entry of the packaged compatibility registry |
| Release receipts | `plan/v1/releases/1.0.1/release-receipt.json`, `postpublish-receipt.json` and `SHA256SUMS`, committed after publication |
| Release notes | [RELEASE_NOTES.md](RELEASE_NOTES.md), packaged in the sdist at the tag |
| 1.0.0 history | The 1.0.0 receipts under `plan/v1/receipts/`, `plan/v1/RELEASE_NOTES.md`, `plan/v1/FINAL_REPORT.md` and `plan/v1/LAUNCH.md` are unchanged and remain the 1.0.0 records |

## What changed in `src/`

Six files changed between the `v1.0.0` tag and the 1.0.1 source, all in
the reviewed bundle merged to `main` as `d1f3215` (PR 56, amendment
V1-055). No file under `src/` changed after it through this release
preparation.

| File | Change |
|---|---|
| `src/actseal/contract.py` | Case rows are yielded one at a time on LF (`_iter_rows`) instead of being split into a list first; one terminating LF is still a terminator, not an empty row |
| `src/actseal/adapters/fixture.py` | Response rows are yielded one at a time on LF (`_iter_lines`); the empty-file check runs after iteration with the same message, and the fixture adapter still has no row-count limit |
| `src/actseal/evidence.py` | `decode_rows` checks the row count from the LF count before decoding any row, then slices rows one at a time, so an overlong row is rejected before it is copied |
| `src/actseal/adapters/laya.py` | A worker reply's `seq` must be a JSON integer equal to the request's sequence; a boolean, floating-point or missing `seq` invalidates the worker and returns `unavailable` with `laya.unavailable:ipc` |
| `src/actseal/compatibility_registry.json` | Adds `dced01d79e64799a19a75c0957f3684a48249c58ebb27d346336e7420195bcb4` for `actseal-choice-v1`; the 1.0.0 source and the retained archive's producer stay approved |
| `src/actseal/__init__.py` | `__version__` is `1.0.1` |

Documentation changed with the bundle: the numerical-kernel exception guide
in `docs/python-api.md` (`clopper_pearson_tail` raises built-in `TypeError`
or `ValueError`, not `ActsealError`), `docs/versioning.md`, `docs/stability.md`,
`docs/migration.md`, a dated addendum to ADR 0015 and the action-gate
example's `run.py` and README. Replay semantics are unchanged; no new ADR
was needed.

## What stayed sealed

- The statistical contract, the verdict rules, the published JSON Schemas
  and `plan/v1/PLAN.md` are unchanged since `v1.0.0`.
- The retained `examples/action_gate/recorded/a5fe090202f7` archive is
  byte-identical and replays to its stored verdict; the 1.0.0 source and its
  original producer remain approved registry entries.
- The 1.0.0 receipts and release documents are retained unchanged; nothing
  1.0.0 published is relabelled as 1.0.1 evidence.
- The 8 October 2026 Jev audit archive keeps its seals; its sealed inputs
  and archived producer source are published verbatim.

## Scope of the release beyond `src/`

The tag also carries the repository changes accepted since 1.0.0 (see the
`v1.0.1` section of `CHANGELOG.md`): repository automation (Dependabot,
CodeQL, dependency review, Gitleaks and the `CI / required` aggregate
check), project URLs and `CITATION.cff` metadata, the result-first README
with its evidence-card hero (V1-058), the corrected GitHub figure
selection, and the 8 October 2026 Jev audit archive under
`docs/results/jev-audit-2026-10-08/` (INCONCLUSIVE; finite-benchmark,
demo-scope evidence collected with benchmark snapshot d3edbab, not with a
released Actseal package). The source distribution packages `docs/` and
`plan/v1/releases/` (the release notes and this report); the wheel contains
only the `actseal` package.

## Gates before the tag

- The source bundle: A2 ACCEPT-WITH-FIXES, then A2b ACCEPT, on executor
  evidence corroborated by hosted CI on the exact reviewed commit
  (`plan/v1/reviews/2026-10-08-refinement-acceptance.md`).
- The release preparation (V1-059): `tools/check_release.py docs`,
  `workflow`, `candidate` and `receipts`, ruff lint and format, strict
  mypy, the ordinary test suite, the packaging tests against a locally built
  wheel and sdist, the pre-commit hooks, a listing of that sdist showing
  `plan/v1/releases/1.0.1/`, and the cached-native Laya integration tests
  on macOS and on the hosted Linux native workflow. The tested trees, the
  exact commands and their results are recorded, with their source
  attributed (executor-reported, orchestrator re-run, or hosted run id), in
  the [release-preparation record](../../reviews/2026-10-08-release-preparation-1.0.1.md).
  Before the tag, the only expected failures are the candidate gate's
  clean-tree check on an uncommitted tree and the receipts gate's missing
  1.0.1 receipt files. Per the
  [publishing guide](../../../../docs/publishing.md), the tag is created
  only on a commit whose candidate gate passes on a clean tree.
- `tools/check_release.py receipts` resolves the 1.0.1 paths under
  `plan/v1/releases/1.0.1/` and fails before publication only because the
  three receipt files do not exist yet; it is the final gate after
  publication.

## What the tagged pipeline records

The tag-triggered `publish-pypi.yml` validates tag, source, lock and
package-version agreement, builds the wheel and sdist once, verifies the
exact bytes on Linux and macOS with Python 3.12 and 3.13, regenerates the
required static assets, waits for the owner's `pypi` environment approval,
publishes through Trusted Publishing, verifies the public copy in a pinned
clean container and mirrors the identical files to a draft GitHub release.
Its receipts are the build checksums (`SHA256SUMS`), the post-publication
receipt (index, published metadata, per-file digests and attestation
inspection, install and smoke results) and the release receipt that binds
the artifact identity, the verify-matrix result and the post-publication
results. Attestation presence, publisher identity and statement subjects
are inspected; no independent cryptographic verification is claimed.

## Known limits

- The 1.0.0 native Laya receipts do not establish native verification of the
  1.0.1 patch; the patch's changed Laya path has its own cached-native
  receipts (macOS and hosted Linux, five tests each, in the
  [release-preparation record](../../reviews/2026-10-08-release-preparation-1.0.1.md);
  ADR 0019). Native support stays limited to the documented tested CPU
  configurations.
- The Jev audit verdict is INCONCLUSIVE; neither PASS nor BLOCK is claimed,
  and the audit is not evidence produced by 1.0.1.
- The README's demo recording shows the published 1.0.0 wheel; it is not a
  1.0.1 recording.
- Phone text legibility remains a known limitation (V1-058).
