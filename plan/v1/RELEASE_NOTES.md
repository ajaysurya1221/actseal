# Actseal 1.0.0 release notes

The implementation, scope and inclusion facts below are final for the tagged
1.0.0 source (implementation fingerprint `8f316f67…98ed3`; the exact value
is in the registry table of the
[versioning policy](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md)).
Every bracketed `PENDING` item is a named release-pipeline receipt (build-time or
post-publication) that is filled only from the actual receipt by Task 21 once
the tagged pipeline produces it; no hash, run id, timing or live result is
claimed before its receipt exists. The final notes must pass
`uv run --frozen python tools/check_release.py receipts` (see the pre-tag
finalization gate in `docs/publishing.md`).

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
https://pypi.org/project/actseal/1.0.0/ (`PENDING`: post-publication receipt;
the page resolves only after the upload).

## What 1.0.0 promises

- A documented 1.x contract for the CLI, typed Python interfaces, wire
  formats and verdict semantics ([stability manifest](https://github.com/ajaysurya1221/actseal/blob/main/docs/stability.md),
  [versioning policy](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md)).
- Explicit handling of historical evidence: 0.1.0 locks and bundles are not
  converted and replay under an isolated pinned 0.1.0
  ([migration guide](https://github.com/ajaysurya1221/actseal/blob/main/docs/migration.md)).
- A CI-tested distribution whose release claims map to receipts (the
  `PENDING` rows below are those receipts; attestation presence is inspected,
  not cryptographically verified).

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

## Pre-publication receipts (final)

These were produced before the tag and do not change with it.

| Claim | Receipt |
|---|---|
| Implementation source | Fingerprint `8f316f67…98ed3` (exact value in the [versioning policy](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md)), unchanged from the retained candidate `5e7931a` through every later documentation and asset commit; the packaged compatibility registry holds exactly this fingerprint and the example's original producer (amendment V1-037) |
| Integrated head and hosted CI | Combined implementation and static figures independently accepted for integration at `ff0f66c` (`plan/v1/reviews/19-combined-static.md`) and merged to `main` as `277d729` (PR 46); all ten hosted source and assets jobs at that exact head succeeded (push run 37599734305, PR run 37599764080). Parent combined checks at that head: 4,163 ordinary tests passed with one explicit obsolete-manifest observation skip and 31 deselected, 25 packaging tests passed, 6 cached-native tests passed with no skips (all 4,195 collected cases accounted for), 590 docs/visual checks, hooks, full static regeneration and all 16 README image references passed |
| Non-publishing release rehearsal | `publish-pypi.yml` rehearsal run [37599844342](https://github.com/ajaysurya1221/actseal/actions/runs/37599844342) completed SUCCESS at `ff0f66c`: build once, assets regeneration, and all four exact-artifact platform verify jobs passed; the publish, post-publish and mirror jobs were intentionally skipped. This is pre-tag evidence that the pipeline works on these bytes, not a tag, artifact or PyPI receipt; the tagged run's receipts are the `PENDING` rows below |
| Static figures: twelve SVG variants and the social preview | Hero and how-it-works accepted at `fcdcfe4`/`7820dba` (Tasks 11, 12, 15); architecture and the measured-width correction accepted at `77a13bd` (`plan/v1/reviews/13-readability.md`): byte-identical regeneration of all twelve SVGs and `social.png`, 337 visual tests, 3,898 ordinary tests, strict typing and hooks, and every variant viewed as actual pixels at 838 px desktop and 254 px mobile with no label below 14 px |
| README responsive selection | Vertical variants below a 1280 px viewport, accepted at `95e17b4` (`plan/v1/reviews/08-responsive.md`); the combined README and assets regenerate with all 16 image references resolved and 590 parent docs/visual checks, the docs gate and hooks passing at `c1b5481` |
| Blind ten-second README test (final, on the integrated README) | Screenshot of the public GitHub README first screen at `main` `277d729`, 1366×900 CSS viewport, device pixel ratio 1, README image rendered at 838 px, captured 7 October 2026 09:33 UTC (`plan/v1/reports/readme-first-screen-277d729-final.jpg`). A fresh, context-free reviewer who saw only that screenshot wrote: "Actseal helps developers test model-chosen application actions by freezing a policy, checking recorded decisions against risk and coverage bounds and fault rules, and sealing evidence for offline replay. It can recompute the verdict without a model call, but replay cannot authenticate responses, prove inference occurred, or establish label truth." Codex accepted the semantic ten-second gate on that answer; the receipt is `plan/v1/reports/readme-ten-second-final.md`. This is one reviewer's reading of one screenshot, not a timed human study. The screenshot shows the PyPI badge for the then-current 0.1.0 release, which is accurate. The earlier preflight at `710ae55` (`readme-ten-second-preflight.md`, `readme-viewport-observation.md`) is retained as history |
| Native paths | Cached-native checks repeated at the Task 19 integration (six tests, no skips) on this source; the historical T30 Linux/macOS native receipts are in `docs/dependencies.md` |

## Release-pipeline receipts (`PENDING` until Task 20/21)

| Claim | Receipt |
|---|---|
| Source commit and tag | `PENDING` (release receipt `source_commit`, tag `v1.0.0`) |
| Wheel and sdist filenames, sizes and SHA-256 | `PENDING` (`SHA256SUMS` and release receipt `distributions`) |
| Build-once workflow run and immutable artifact id | `PENDING` (release receipt `workflow_run`, `artifact`) |
| Four-platform verification of the exact bytes | `PENDING` (`verify` job results) |
| Static figures regenerate byte-identically on the tagged commit | `PENDING` (`assets` job on the tagged commit) |
| Trusted Publishing with attestations | `PENDING`; attestation presence, publisher identity and statement subjects are inspected, and no independent cryptographic verification is claimed |
| Clean-container install from the public index; demo exit 0, replays 0 and 1 | `PENDING` (post-publication receipt) |
| Production/Stable classifier on PyPI | `PENDING` (post-publication receipt `published_metadata.classifiers`) |
| Genuine PyPI demo recording | `PENDING` (Task 14, captured after publication under Decision 2A; added by Task 21) |

## Decided implementation facts

- **Experimental Jev provider: included as PROVISIONAL.** The adapter
  `actseal.experimental.providers.jev` ships behind the explicit opt-in
  `--provider jev --experimental-provider` (bring your own `JEV_API_KEY`;
  one attempt per request; no retry, redirect or fallback; vendor-reported
  model version, not a weight attestation). It carries no 1.x promise. Every
  test runs over a mocked transport. No live Jev result is accepted as
  evidence, and none appears here.
- **Finite-benchmark audit: not run.** The offline preregistration (959
  fixed cases, candidate 3) was accepted as a preregistration only; it is not
  a run receipt. Live collection did not begin for 1.0.0: no key was read,
  no `--execute` call was made, and no journal, request count or result
  exists, so nothing is claimed. The chronology, including the harness
  denials, is in the Task 06 receipts. ADR 0018's "no power or population
  claim" wording applies to any future run.
- **Application example archive: approved.** `examples/action_gate/` ships
  with its retained recorded synthetic bundle, unchanged; its original
  producer and the 1.0.0 source are the two approved registry entries
  (amendment V1-037), and the unchanged archive replays under this release.
- **Figures.** The P1 set (hero, how-it-works, architecture, social preview)
  is committed and accepted; the P2 figures (where-it-sits, decision/verdict
  matrix, evidence boundary) were not implemented for 1.0.0 and the three
  evidence-boundary limitations stay in plain text. The genuine demo
  recording follows the approved post-PyPI exception (Decision 2A).

## Known limits and not-run items

- Native Laya support is limited to the documented tested CPU
  configurations; no GPU, Windows, Intel Mac, Linux ARM or musl support.
- Demo and example evidence is synthetic (`evidence_scope=demo`) and is not a
  population or model-quality result.
- Items recorded as not run, BLOCK, INCONCLUSIVE or ERROR in the final report
  stay visible here; none is omitted.

Launch posts remain drafts. The social preview file is delivered under
`docs/assets/social.png`; uploading it in GitHub settings is a manual step and
is not claimed as done.
