# Actseal 1.0.1 release notes

Actseal 1.0.1 is a patch release of the 1.x line. The implementation, scope
and inclusion facts below are final for the tagged 1.0.1 source
(implementation fingerprint `dced01d7…5bcb4`; the exact value is in the
registry table of the
[versioning policy](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md)).
The 1.x promises and non-promises stated in the
[1.0.0 release notes](https://github.com/ajaysurya1221/actseal/blob/main/plan/v1/RELEASE_NOTES.md)
still apply: 1.0.1 changes no CLI option, public Python signature, wire
format, schema or verdict rule.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-dark.svg">
  <img alt="How Actseal works: freeze, run, verify, seal, replay." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-light.svg" width="100%">
</picture>

Actseal verifies model-chosen application actions for developers: freeze a
policy, check its recorded decisions, and replay the evidence offline.

## Install and try

```bash
uvx --python 3.12 actseal demo --out ./actseal-demo
uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence
uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence
```

The third command exits 1 by design. Unpinned, `uvx` resolves the latest
Actseal release on PyPI; to run exactly this release, add
`--from "actseal==1.0.1"` to each command, for example
`uvx --python 3.12 --from "actseal==1.0.1" actseal demo --out ./actseal-demo`
([quickstart](https://github.com/ajaysurya1221/actseal/blob/main/docs/quickstart.md)).
Package page: https://pypi.org/project/actseal/1.0.1/.

## What changed in 1.0.1

See the `v1.0.1` section of
[CHANGELOG.md](https://github.com/ajaysurya1221/actseal/blob/main/CHANGELOG.md).

**Fixes**

- JSONL readers iterate LF-delimited rows without first building a list of
  every row. Row boundaries, validation order, diagnostics and existing
  limits are preserved; the fixture adapter still has no row-count limit.
- Native Laya worker reply sequences must be JSON integers equal to the
  sequence of the request they answer. Boolean, floating-point and missing
  sequences invalidate the worker and return `unavailable` with
  `laya.unavailable:ipc`.

**Replay compatibility**

- The reviewed 1.0.1 implementation fingerprint `dced01d7…5bcb4` is added to
  the `actseal-choice-v1` compatibility registry beside both existing
  mappings (the released 1.0.0 source and the retained archive's original
  producer), three entries in all (amendment V1-055). Evidence produced by
  1.0.0 and the retained `examples/action_gate` archive replay under 1.0.1
  to their stored verdicts; their bytes are unchanged. Replay compatibility
  is not collection permission: `collect` and `verify` against a 1.0.0 lock
  are refused under 1.0.1, and a new run needs a new exact-source lock from
  `actseal lock`
  ([migration guide](https://github.com/ajaysurya1221/actseal/blob/main/docs/migration.md)).

**Documentation**

- The numerical-kernel exception guide is corrected:
  `clopper_pearson_tail` raises built-in `TypeError` or `ValueError`, not
  `ActsealError`. The correction changes neither numerical behaviour nor
  results.
- GitHub README figure selection uses the dark or light desktop variants at
  every viewport width. This supersedes the 1.0.0 statement that the README
  selects vertical variants below 1280 px. Mobile SVGs remain committed;
  phone text legibility remains a known limitation.
- The README opens with the result: the ticket-routing problem, the recorded
  INCONCLUSIVE Jev audit (580 of 639 verification cases received ACT; 24
  disagreed with benchmark labels) with its offline-replay link, the
  execution and authenticity boundary and links to the design records,
  schemas, mutation harness and 1.0.0 receipt, then the synthetic
  quickstart. The hero is an evidence card (1600×520) stating the question
  Actseal answers beside the audit's recorded numbers, its fixed-benchmark
  scope, its producer (benchmark snapshot d3edbab, not a released package)
  and the archived producer its replay requires; tests compare the card with
  the committed audit files. Every text run is at
  least 14.1 nominal CSS px at an 838 px image width; at a 254 px phone
  width the thesis renders at about 7 px, a recorded exception (V1-058).
  `social.png` re-flows the same card. The workflow and architecture figures
  are linked instead of embedded; a maintainer note and the action-gate
  "before enabling automatic ticket routing" block were added.

**Repository automation and metadata**

- Weekly Dependabot updates for `uv` and GitHub Actions, CodeQL Python
  analysis, pull-request dependency review and full-history Gitleaks
  scanning.
- A `CI / required` aggregate check that passes only when every CI job
  succeeds; a failed, cancelled or skipped job fails it.
- Package metadata project URLs for the quickstart documentation,
  repository, issue tracker and changelog.
- `CITATION.cff` software citation metadata, kept in step with the released
  version (1.0.1, 8 October 2026).

**Evidence: the 8 October 2026 Jev audit archive**

- [`docs/results/jev-audit-2026-10-08/`](https://github.com/ajaysurya1221/actseal/blob/main/docs/results/jev-audit-2026-10-08/README.md)
  holds 959 recorded single-attempt captures across separate calibration and
  verification cohorts, with an INCONCLUSIVE verification verdict: 580 of
  639 verification cases received ACT, and 24 disagreed with benchmark
  labels. Neither PASS nor BLOCK is claimed.
- Scope: collection used benchmark snapshot d3edbab, not the released
  Actseal 1.0.0 package, on a fixed benchmark; results are finite-benchmark,
  demo-scope evidence. Offline replay of the archive requires its archived
  producer (d3edbab).
- Inclusion: the archive is part of the repository's `docs/` tree, which the
  source distribution packages; the wheel contains only the `actseal`
  package.

## Release-pipeline receipts

The tagged run of `publish-pypi.yml` builds the wheel and sdist once,
verifies those bytes on Linux and macOS with Python 3.12 and 3.13,
regenerates the required static assets, uploads through Trusted Publishing
only after the owner approves the `pypi` environment, verifies the public
copy in a clean container and mirrors identical files to a draft GitHub
release ([publishing guide](https://github.com/ajaysurya1221/actseal/blob/main/docs/publishing.md)).
Each value below comes from `plan/v1/releases/1.0.1/release-receipt.json`,
`plan/v1/releases/1.0.1/postpublish-receipt.json` or
`plan/v1/releases/1.0.1/SHA256SUMS`.

| Claim | Receipt |
|---|---|
| Source commit and tag | `source_commit` `758c65df0ae94402328209a33604ac8921678a28`, annotated tag `v1.0.1` |
| Tagged workflow run | `workflow_run.id` `37721934891` (`publish-pypi.yml`); the build and verification URLs are in the release receipt |
| Wheel | `actseal-1.0.1-py3-none-any.whl`, `104,868` bytes, SHA-256 `c74187b6b1df88befe27a81b34464480fd54ffe2459b7c2fb6e229245130050e` (`distributions`, `SHA256SUMS`) |
| Sdist | `actseal-1.0.1.tar.gz`, `4,318,825` bytes, SHA-256 `4ebb9c21043362591c39867c5679d5c10bfbb64cfff792c6e21b8558aed547e4` (`distributions`, `SHA256SUMS`) |
| Build-once immutable artifact | Actions artifact id `11526072025`, digest `sha256:7fbd7129e1132c067e834d73365a51d6e029e098284567024571b0e973aaccba` (`artifact`). The four verify-matrix jobs, the publish job and the mirror job download this artifact by id and compare its hashes with the build checksums; the verify-published job compares the official PyPI files with the build checksums; the assets job downloads no distribution. `lock_sha256` is the `uv.lock` digest at the source commit, not a decision lock |
| Four-platform verification and asset regeneration | The publish job runs only after `build`, all four `verify` jobs and `assets` succeed. The release receipt records the verify-matrix result as `verification.verify_matrix`, and the `release-receipt` command accepts no result other than `success` |
| Trusted Publishing with attestations | 1 attestation for the wheel and 1 for the sdist; publisher kind `GitHub`, repository `ajaysurya1221/actseal`, workflow `publish-pypi.yml`, environment `pypi`; each file's `subject_sha256` equals its SHA-256 (post-publication receipt `files[].provenance`). The inspection covers attestation presence, publisher identity and statement subjects; no independent cryptographic verification is claimed |
| Published metadata on PyPI | `name` `actseal`, `version` `1.0.1`, `yanked` `false`; `classifiers` (10): `Development Status :: 5 - Production/Stable`, `Intended Audience :: Developers`, `Operating System :: MacOS`, `Operating System :: POSIX :: Linux`, `Programming Language :: Python :: 3`, `Programming Language :: Python :: 3 :: Only`, `Programming Language :: Python :: 3.12`, `Programming Language :: Python :: 3.13`, `Topic :: Software Development :: Quality Assurance`, `Typing :: Typed` (post-publication receipt `published_metadata`) |
| Clean-container install from the public index | Index `https://pypi.org`; `installed_outside_checkout` `true`; `version_output` `actseal 1.0.1`; `demo_exit` `0` with `demo_bad_status` `BLOCK` and `demo_fixed_status` `PASS`; `fixed_replay_exit` `0`; `bad_replay_exit` `1`; downloaded files `matches_build` `true` (post-publication receipt `checks`, `files`) |
| Demo recording | No 1.0.1 recording was made; the README recording remains the 1.0.0 capture, made from the published 1.0.0 wheel |

## Pre-publication receipts

These were produced before the tag and do not change with it.

| Claim | Receipt |
|---|---|
| Implementation source | Fingerprint `dced01d7…5bcb4` (exact value in the [versioning policy](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md)): the reviewed final 1.0.1 source, version metadata included (V1-055). The hardening and 1.0.1 bundle was accepted (A2 ACCEPT-WITH-FIXES, then A2b ACCEPT; reviewed head `d66795a` with merge `887fa77`) and merged to `main` as `d1f3215` (PR 56); no file under `src/` changed after it through this release preparation. The packaged registry holds this fingerprint, the 1.0.0 source and the retained archive's original producer |
| Cached-native receipts for the changed Laya path | ADR 0019 requires a cached-native receipt for a changed native path. The five `tests/integration/test_laya.py` tests passed against the 1.0.1 source on macOS (arm64, Python 3.12.13; 5 passed in 32.63 s) and in the hosted Linux native workflow ([run 37719743745](https://github.com/ajaysurya1221/actseal/actions/runs/37719743745), Python 3.12.3, `laya==0.3.28`; 5 passed in 33.12 s); commands and trees in the [release-preparation record](https://github.com/ajaysurya1221/actseal/blob/main/plan/v1/reviews/2026-10-08-release-preparation-1.0.1.md) |
| Reviews and hosted CI | Verification limit recorded in the acceptance ledger (`plan/v1/reviews/2026-10-08-refinement-acceptance.md`): the reviewer's sandbox could not write temporary files, so test suites and packaging rebuilds were accepted as executor evidence corroborated by hosted CI on the exact reviewed commits |
| Repository automation | A3 ACCEPT at `75c0223` (with merge `2f02927`), merged as `8dea59d` (PR 54); the `main` ruleset is active (same ledger) |
| Jev audit archive | Collection from snapshot d3edbab (run `ec3877960b376021ce4c81110dad353c`) ACCEPT; result package ACCEPT-WITH-FIXES at `8912054` (with merge `acbf51b`), merged as `3d3a261` (PR 55) (same ledger) |
| README, hero and social preview | README first screen and figure selection: A1 and A1b ACCEPT-WITH-FIXES, merged as `72f4a2f` (PR 51) and `5e127fe` (PR 52) (same ledger); the result-first opening and evidence-card hero follow amendment V1-058 and its recorded readability exceptions and are on `main` as `39c75a2` (PR 60) |

## Known limits and not-run items

- The 1.0.0 native Laya receipts are 1.0.0 receipts; the 1.0.1 patch's
  changed Laya path has its own cached-native receipts (table above,
  [ADR 0019](https://github.com/ajaysurya1221/actseal/blob/main/docs/decisions/0019-supported-platforms.md)).
  Native Laya support remains limited to the documented tested CPU
  configurations on macOS and Linux; Windows is unsupported.
- Demo and example evidence is synthetic (`evidence_scope=demo`) and is not
  a population or model-quality result.
- The Jev audit is INCONCLUSIVE, finite-benchmark, demo-scope evidence from
  benchmark snapshot d3edbab, not from a released Actseal package.
- The README's demo recording is the capture of the published 1.0.0 wheel;
  it is not a 1.0.1 recording and is not authenticated model evidence.
- Phone text legibility remains a known limitation: at a 254 px phone width
  the hero thesis renders at about 7 px (V1-058).
- The tagged run creates the GitHub release as a draft; publishing it is a
  separate, later documentation step
  ([publishing guide](https://github.com/ajaysurya1221/actseal/blob/main/docs/publishing.md)).
