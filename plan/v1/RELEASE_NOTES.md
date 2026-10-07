# Actseal 1.0.0 — DRAFT release notes

**Status: draft, not published.** No `v1.0.0` tag exists and nothing for
1.0.0 is on PyPI. Every bracketed `PENDING` item below is filled only from an
actual receipt by Task 21 after Task 20 publishes; no hash, run id, timing or
live result is claimed here. The final notes must pass
`uv run --frozen python tools/check_release.py receipts`.

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
https://pypi.org/project/actseal/1.0.0/ (`PENDING`: resolves only after
publication).

## What 1.0.0 promises

- A documented 1.x contract for the CLI, typed Python interfaces, wire
  formats and verdict semantics ([stability manifest](https://github.com/ajaysurya1221/actseal/blob/main/docs/stability.md),
  [versioning policy](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md)).
- Explicit handling of historical evidence: 0.1.0 locks and bundles are not
  converted and replay under an isolated pinned 0.1.0
  ([migration guide](https://github.com/ajaysurya1221/actseal/blob/main/docs/migration.md)).
- A CI-tested, attested distribution whose release claims map to receipts
  (this document, once final).

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
support with Windows unsupported, the tag-triggered release pipeline and the
new reference documentation.

## Receipts (`PENDING` until Task 20/21)

| Claim | Receipt |
|---|---|
| Source commit and tag | `PENDING` (release receipt `source.commit`, tag `v1.0.0`) |
| Wheel and sdist filenames, sizes and SHA-256 | `PENDING` (`SHA256SUMS` and release receipt `distributions`) |
| Build-once workflow run and immutable artifact id | `PENDING` (release receipt `workflow_run`, `artifact`) |
| Four-platform verification of the exact bytes | `PENDING` (`verify` job results) |
| Trusted Publishing with attestations | `PENDING`; attestation presence, publisher identity and statement subjects are inspected, and no independent cryptographic verification is claimed |
| Clean-container install from the public index; demo exit 0, replays 0 and 1 | `PENDING` (post-publication receipt) |
| Production/Stable classifier on PyPI | `PENDING` (post-publication receipt `published_metadata.classifiers`) |
| Static figures regenerate byte-identically | `PENDING` (`assets` job); hero, how-it-works and social preview committed; architecture pending Task 13 |
| Blind ten-second README test | `PENDING` (Task 08 acceptance; prompt, screenshot hash and answer in `plan/v1/reports/`) |
| Genuine PyPI demo recording | `PENDING` (Task 14, captured after publication under Decision 2A; added by Task 21) |

## Conditional items

- **Experimental Jev provider.** Prepared as PROVISIONAL behind an explicit
  experimental flag; whether 1.0.0 includes it is decided at integration
  (Task 19). If included, this section states the flag, the identity
  limits and the absence or presence of audit results; if cut, it states the
  later 1.x target. No live Jev result exists today. `PENDING`
- **Finite-benchmark audit.** The preregistered 959-request descriptive
  Banking77 audit has not been executed. If it runs before release, its
  separate cohort receipts are linked here with the explicit "no power or
  population claim" wording from ADR 0018; otherwise it is recorded as not
  run. `PENDING`
- **Application example archive.** `examples/action_gate/` ships with its
  recorded synthetic bundle once its original producer is explicitly approved
  in the compatibility registry (Task 19). `PENDING`

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
