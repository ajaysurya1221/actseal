# Actseal 1.0.0 release notes

Actseal 1.0.0 was built once from the annotated, immutable tag `v1.0.0`
(source commit `04c10d3fec60727310cf65acf6528f13264a26d4`), verified on the
four supported platforms, published to PyPI through Trusted Publishing after
the owner's approval, and verified from the public index in a clean
container. Every claim below names its receipt: the release and
post-publication receipts under `plan/v1/receipts/`, the accepted reports and
reviews under `plan/v1/`, or a hosted workflow run. Items that were not run,
or ended BLOCK, INCONCLUSIVE or ERROR, stay visible. The implementation
fingerprint is `8f316f67…98ed3`; the exact value is in the registry table of
the [versioning policy](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md).

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

The third command exits 1 by design. Package page:
https://pypi.org/project/actseal/1.0.0/. The published metadata reports
`actseal 1.0.0`, `Development Status :: 5 - Production/Stable`, Python 3.12
and 3.13, macOS and Linux, and is not yanked (post-publication receipt
`published_metadata`).

## What 1.0.0 promises

- A documented 1.x contract for the CLI, typed Python interfaces, wire
  formats and verdict semantics ([stability manifest](https://github.com/ajaysurya1221/actseal/blob/main/docs/stability.md),
  [versioning policy](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md)).
- Explicit handling of historical evidence: 0.1.0 locks and bundles are not
  converted and replay under an isolated pinned 0.1.0
  ([migration guide](https://github.com/ajaysurya1221/actseal/blob/main/docs/migration.md)).
- A CI-tested distribution whose release claims map to the receipts in this
  document; attestation presence is inspected, not cryptographically
  verified.

It does **not** promise authenticated model responses, proof that inference
occurred, correct labels, universal calibration or enforcement of surrounding
application actions. See the
[threat model](https://github.com/ajaysurya1221/actseal/blob/main/docs/threat-model.md).

## Changes since 0.1.0

See the `v1.0.0` section of
[CHANGELOG.md](https://github.com/ajaysurya1221/actseal/blob/main/CHANGELOG.md):
replay-engine compatibility and the reviewed registry, versioned receipts
(schema 1) and published schemas, rejected option abbreviations, the
documented numeric-domain error, shared provider conformance, property and
mutation tests, the application action-gate example, Linux/macOS 3.12/3.13
support with Windows unsupported, the tag-triggered release pipeline, the
new reference documentation and the reproducible README figures.

## Release-pipeline receipts

Tagged workflow run [37603727302](https://github.com/ajaysurya1221/actseal/actions/runs/37603727302)
(`publish-pypi.yml`, build attempt 1, verification attempt 1): all nine jobs
SUCCESS. Values below are copied from `plan/v1/receipts/release-receipt.json`,
`plan/v1/receipts/postpublish-receipt.json` and `plan/v1/receipts/SHA256SUMS`.

| Claim | Receipt |
|---|---|
| Source commit and tag | `source_commit` `04c10d3fec60727310cf65acf6528f13264a26d4`, tag `v1.0.0`; the tag is annotated and was never moved |
| Wheel | `actseal-1.0.0-py3-none-any.whl`, 101,900 bytes, SHA-256 `4497fef4878cb67f03845e13f91c8b8c4e7686361198d0ebc52a1764157ae3bf` (`distributions`, `SHA256SUMS`) |
| Sdist | `actseal-1.0.0.tar.gz`, 2,054,855 bytes, SHA-256 `aa31ccf9f5cce30c40269dd5d9904ef61f147f9c4aaf21e3db288981b3278da6` (`distributions`, `SHA256SUMS`) |
| Build-once workflow run and immutable artifact | `workflow_run` id 37603727302; Actions artifact id 11474201373, digest `sha256:30fff8a3ad125cfee12f1101b047ade5cadf445919402fcefa4c32df9fa0d8af`; every later job downloaded that artifact by id and compared its hashes with the build checksums; `lock_sha256` is the `uv.lock` digest at the source commit, not a decision lock |
| Four-platform verification of the exact bytes | `verification.verify_matrix` = `success` (Linux and macOS, Python 3.12 and 3.13, packaging tests against the downloaded artifact) |
| Static figures regenerate byte-identically on the tagged commit | The `assets` job of run 37603727302 passed with the pinned toolchain |
| Trusted Publishing with attestations | One PEP 740 attestation per distribution; publisher kind GitHub, repository `ajaysurya1221/actseal`, workflow `publish-pypi.yml`, environment `pypi`; each statement subject equals its file's SHA-256. Attestation presence, publisher identity and statement subjects were inspected; no independent cryptographic verification is claimed. |
| Clean-container install from the public index | Index `https://pypi.org`; `installed_outside_checkout` true; `version_output` `actseal 1.0.0`; `demo_exit` 0 with `demo_bad_status` BLOCK and `demo_fixed_status` PASS; `fixed_replay_exit` 0; `bad_replay_exit` 1; both downloaded files `matches_build` true against the declared PyPI digests |
| Production/Stable classifier on PyPI | `published_metadata.classifiers` includes `Development Status :: 5 - Production/Stable`; `yanked` false |
| Independent download comparison | Codex separately downloaded the official PyPI wheel and sdist and the GitHub draft-release assets; both pairs are byte-identical and equal the tagged build checksums (`plan/v1/reviews/20-publication.md`, independent receipt reviewer ACCEPT). GitHub release 405628842 holds the wheel, sdist, `SHA256SUMS` and receipt as a **draft**; publishing it is the Task 22 closure step |
| Hosted CI at the tagged source | The pre-tag head `4d7966f` passed all ten source and assets jobs (runs 37602503653 and 37602539917) and the non-publishing rehearsal 37602547044; `git diff` between that head and the tagged `main` `04c10d3` is empty; `main` CI run 37603576993 at the tagged source is SUCCESS (`plan/v1/reviews/20-pretag.md`, `20-publication.md`) |
| Genuine PyPI demo recording (Decision 2A) | Captured after publication from the official PyPI 1.0.0 wheel (re-hashed equal to the wheel above) on 7 October 2026 between 10:16:09 and 10:16:30 UTC; raw capture ACCEPT at report commit `f55fd5b` (`plan/v1/reviews/14-capture.md`). Raw cast 3,626 bytes, 21.517 s, 21 output events and one final exit 0, no input, resize or marker events, header env `LANG` and `TERM` only; recorded outcomes demo exit 0 (bad BLOCK, fixed PASS), fixed replay exit 0, bad replay exit 1. Both GIFs 24.51 s, 8 frames, 979×918 px, light 571,102 bytes and dark 569,379 bytes, each rendered twice to identical bytes at speed 1 with no trimming. The cast and GIF SHA-256 values (`cdce70c6…`, `653f6bb6…`, `5af6a3ce…`) are in the capture report `plan/v1/reports/14-capture.md`; they are recording receipts, not release-artifact hashes. Copying the recording into `docs/assets/`, registering it in the asset inventory and the hosted regeneration check are the separately reviewed Task 14 activation; the recording is absent from the tag, the wheel and the PyPI package page and present only in the later repository, as Decision 2A approved |

## Pre-publication receipts

These were produced before the tag and did not change with it.

| Claim | Receipt |
|---|---|
| Implementation source | Fingerprint `8f316f67…98ed3` (exact value in the [versioning policy](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md)), unchanged from the retained candidate `5e7931a` through every later documentation and asset commit to the tag; the packaged compatibility registry holds exactly this fingerprint and the example's original producer (amendment V1-037) |
| Integrated head and hosted CI | Combined implementation and static figures independently accepted for integration at `ff0f66c` (`plan/v1/reviews/19-combined-static.md`) and merged to `main` as `277d729` (PR 46); all ten hosted source and assets jobs at that exact head succeeded (push run 37599734305, PR run 37599764080). Parent combined checks at that head: 4,163 ordinary tests passed with one explicit obsolete-manifest observation skip and 31 deselected, 25 packaging tests passed, 6 cached-native tests passed with no skips (all 4,195 collected cases accounted for), 590 docs/visual checks, hooks, full static regeneration and all 16 README image references passed |
| Non-publishing release rehearsals | `publish-pypi.yml` rehearsal run [37599844342](https://github.com/ajaysurya1221/actseal/actions/runs/37599844342) at `ff0f66c` and the final rehearsal 37602547044 at `4d7966f` both completed SUCCESS: build once, assets regeneration and all four exact-artifact platform verify jobs; publish, post-publish and mirror intentionally skipped (`plan/v1/reports/09-rehearsal-37599844342.md`, `plan/v1/reviews/20-pretag.md`) |
| Static figures: twelve SVG variants and the social preview | Hero and how-it-works accepted at `fcdcfe4`/`7820dba` (Tasks 11, 12, 15); architecture and the measured-width correction accepted at `77a13bd` (`plan/v1/reviews/13-readability.md`): byte-identical regeneration of all twelve SVGs and `social.png`, 337 visual tests, 3,898 ordinary tests, strict typing and hooks, and every variant viewed as actual pixels at 838 px desktop and 254 px mobile with no label below 14 px |
| README responsive selection | Vertical variants below a 1280 px viewport, accepted at `95e17b4` (`plan/v1/reviews/08-responsive.md`); the combined README and assets regenerate with all 16 image references resolved and 590 parent docs/visual checks, the docs gate and hooks passing at `c1b5481` |
| Pre-tag documentation | Final scope and status wording accepted at `75626ae` after the 08F, 08F2 and 08F3 corrections (`plan/v1/reviews/20-pretag.md`): 110 docs tests, docs gate and hooks |
| Blind ten-second README test (final, on the integrated README) | Screenshot of the public GitHub README first screen at `main` `277d729`, 1366×900 CSS viewport, device pixel ratio 1, README image rendered at 838 px, captured 7 October 2026 09:32:34 UTC (`plan/v1/reports/readme-first-screen-277d729-final.jpg`). A fresh, context-free reviewer who saw only that screenshot wrote: "Actseal helps developers test model-chosen application actions by freezing a policy, checking recorded decisions against risk and coverage bounds and fault rules, and sealing evidence for offline replay. It can recompute the verdict without a model call, but replay cannot authenticate responses, prove inference occurred, or establish label truth." Codex accepted the semantic ten-second gate on that answer (`plan/v1/reports/readme-ten-second-final.md`). This is one reviewer's reading of one screenshot, not a timed human study. The screenshot shows the PyPI badge for the then-current 0.1.0 release, which was accurate before publication. The earlier preflight at `710ae55` (`readme-ten-second-preflight.md`, `readme-viewport-observation.md`) is retained as history |
| Native paths | Cached-native checks repeated at the Task 19 integration (six tests, no skips) on this source; the historical T30 Linux/macOS native receipts are in `docs/dependencies.md` |

## Decided implementation facts

- **Experimental Jev provider: included as PROVISIONAL.** The adapter
  `actseal.experimental.providers.jev` ships behind the explicit opt-in
  `--provider jev --experimental-provider` (bring your own `JEV_API_KEY`;
  one attempt per request; no retry, redirect or fallback; vendor-reported
  model version, not a weight attestation). It carries no 1.x promise. Every
  test runs over a mocked transport. Zero live Jev requests were made during
  the release; no live Jev result is accepted as evidence, and none appears
  here.
- **Finite-benchmark audit: not run.** The offline preregistration (959
  fixed cases, candidate 3) was accepted as a preregistration only; it is not
  a run receipt. Live collection did not begin for 1.0.0: no key was read,
  no `--execute` call was made, and no journal, request count or result
  exists, so nothing is claimed. The chronology, including the harness
  denials, is in the Task 06 receipts. Under amendment V1-052 the live audit
  is deferred to 1.1 with its preregistration, thresholds and inventories
  frozen. ADR 0018's "no power or population claim" wording applies to any
  future run.
- **Application example archive: approved.** `examples/action_gate/` ships
  with its retained recorded synthetic bundle, unchanged; its original
  producer and the 1.0.0 source are the two approved registry entries
  (amendment V1-037), and the unchanged archive replays under this release.
- **Figures.** The P1 set (hero, how-it-works, architecture, social preview)
  is committed and accepted; the P2 figures (where-it-sits, decision/verdict
  matrix, evidence boundary) were not implemented for 1.0.0, are deferred to
  1.1 under V1-052, and the three evidence-boundary limitations stay in
  plain text. The genuine demo recording follows the approved post-PyPI
  exception (Decision 2A) and is recorded above.

## Known limits and not-run items

- Native Laya support is limited to the documented tested CPU
  configurations; no GPU, Windows, Intel Mac, Linux ARM or musl support.
- Demo and example evidence is synthetic (`evidence_scope=demo`) and is not a
  population or model-quality result. The recorded demo is an illustration
  of the published package's behaviour, not authenticated model evidence.
- Not run: the live Jev audit (above). No item of the release ended BLOCK,
  INCONCLUSIVE or ERROR except the demo's deliberately bad run, which BLOCKs
  by design and replays to exit 1.
- Optional scope frozen under V1-052 for 1.0: live audit and P2 figures.

Launch posts remain drafts (`plan/v1/LAUNCH.md`). The GitHub release that
mirrors the published files is a draft until the post-publication
documentation is accepted. The social preview file is delivered under
`docs/assets/social.png`; uploading it in GitHub settings is a manual step and
is not claimed as done.
