# Actseal v1.0.0 — release report

**PUBLISHED — 7 October 2026.** `actseal` 1.0.0 is on PyPI from the annotated
immutable tag `v1.0.0` (`04c10d3fec60727310cf65acf6528f13264a26d4`). Tagged
workflow run [37603727302](https://github.com/ajaysurya1221/actseal/actions/runs/37603727302)
completed all nine jobs after the owner approved the `pypi` environment:
build once, four-platform verification of the exact bytes, static asset
regeneration, Trusted Publishing, clean-container verification from the
public index, and mirroring to a draft GitHub release. Publication-scope
ACCEPT is recorded in [REVIEW 20](reviews/20-publication.md); the pre-tag
gate in [REVIEW 20 pre-tag](reviews/20-pretag.md). This report records what
shipped, what did not, and the receipts for each claim. It does not claim
the post-publication media integration, the public GitHub release or the
final closure (Task 22) are complete.

| Release field | Verified result |
|---|---|
| Tag target | `04c10d3fec60727310cf65acf6528f13264a26d4`, annotated, never moved |
| Implementation fingerprint | `8f316f67…98ed3`, unchanged since candidate `5e7931a` (exact value in [versioning](../../docs/versioning.md)) |
| Wheel | `actseal-1.0.0-py3-none-any.whl`, 101,900 bytes, SHA-256 `4497fef4878cb67f03845e13f91c8b8c4e7686361198d0ebc52a1764157ae3bf` |
| Sdist | `actseal-1.0.0.tar.gz`, 2,054,855 bytes, SHA-256 `aa31ccf9f5cce30c40269dd5d9904ef61f147f9c4aaf21e3db288981b3278da6` |
| Actions artifact | id 11474201373, digest `sha256:30fff8a3ad125cfee12f1101b047ade5cadf445919402fcefa4c32df9fa0d8af`; downloaded by id by every later job |
| Public index verification | Pinned clean container, installed outside the checkout: `actseal 1.0.0`; demo exit 0 (bad BLOCK, fixed PASS); fixed replay 0; bad replay 1; both files match the build checksums and PyPI's declared digests |
| Attestations | One PEP 740 attestation per file from GitHub `ajaysurya1221/actseal`, workflow `publish-pypi.yml`, environment `pypi`, subjects equal to the file digests. Presence, identity and subjects inspected; no independent cryptographic verification is claimed |
| Independent download comparison | Codex downloaded the official PyPI files and the GitHub draft assets separately; both pairs byte-identical and equal to the build checksums; independent receipt reviewer ACCEPT ([REVIEW 20](reviews/20-publication.md)) |
| GitHub release | 405628842, **draft**, four assets uploaded; publishing it is Task 22 |
| Hosted CI | Pre-tag head `4d7966f`: ten source/assets jobs SUCCESS (runs 37602503653, 37602539917) and final rehearsal 37602547044 SUCCESS; `git diff 4d7966f..04c10d3` empty; `main` CI 37603576993 at the tagged source SUCCESS |
| Receipts | `plan/v1/receipts/release-receipt.json`, `postpublish-receipt.json`, `SHA256SUMS` (committed at `712fb78`); [RELEASE_NOTES](RELEASE_NOTES.md) maps each claim to them |
| Incremental paid inference spend | Zero Jev calls; no paid model API. Subscription usage is accounted below as a list-price equivalent, not a charge |

## Shipped versus planned

The [plan](PLAN.md) scheduled Tasks 00–22. Dispositions below cite the
accepting review or the recorded decision; earlier REVISE, PARTIAL, BLOCKED
and denial reports stay in `plan/v1/reports/` and `plan/v1/reviews/` as
history and are not rewritten.

| Planned task | Shipped state and receipt |
|---|---|
| 00–01 plan persistence and baseline | ACCEPT; baseline 2,302 tests including native ([STATE](STATE.md)) |
| 02 stability and replay compatibility | ACCEPT; frozen 1.x surface, schema-2 locks/manifests, schema-1 receipts, registry, legacy isolation ([ADR 0015](../../docs/decisions/0015-v1-stability-and-replay-compatibility.md)) |
| 03 provider conformance | ACCEPT `212a1d6`; 177 conformance/provider plus 5 cached-native tests |
| 04 numerical properties and mutations | ACCEPT `732914d`; 252 tests, all 8 targeted mutations killed |
| 05 experimental Jev adapter | Shipped as PROVISIONAL behind `--provider jev --experimental-provider`, mocked transport only; retained by human decision V1-049 and release decision V1-052 ([ADR 0017](../../docs/decisions/0017-experimental-decision-provider.md)) |
| 06 preregistered Jev audit | Preregistration (959 fixed cases, candidate 3) accepted offline at `d3edbab`; **live collection not run**: no key read, no `--execute`, no journal, request or verdict; blocked by effective harness denials and deferred to 1.1 under V1-052. No ERROR run was fabricated |
| 07 application action-gate example | ACCEPT `277d8e2`; original synthetic archive unchanged; two-entry registry replays it (V1-037) |
| 08 documentation and README | ACCEPT through 08R/08R2 (`95e17b4`), 08F/08F2/08F3 (`75626ae`); final blind first-screen ACCEPT at `277d729` |
| 09 CI and publication pipeline | ACCEPT; rehearsals 37599844342 and 37602547044 SUCCESS; tagged run 37603727302 SUCCESS ([ADR 0016](../../docs/decisions/0016-release-promotion-and-receipts.md)) |
| 10–13, 15 static assets | ACCEPT; toolchain, hero, how-it-works, architecture and social preview; three SVG groups re-validated at the measured 838/254 px README widths (`77a13bd`, [REVIEW 13](reviews/13-readability.md)) |
| 14 genuine PyPI demo recording | Raw capture from the official 1.0.0 wheel ACCEPT at `f55fd5b` ([REVIEW 14](reviews/14-capture.md)); repository activation, inventory registration and hosted regeneration are the separately reviewed step still running when this report was written |
| 16–18 P2 figures | **Cut to 1.1** (V1-052); not implemented; evidence limits remain in plain text |
| 19 release candidate integration | ACCEPT `ff0f66c` → `main` `277d729` ([REVIEW 19](reviews/19-combined-static.md)) |
| 20 release gate and publication | ACCEPT ([REVIEW 20 pre-tag](reviews/20-pretag.md), [REVIEW 20](reviews/20-publication.md)) |
| 21 final documentation | This report, the release notes, the launch draft and the README recording section; see [REPORT 21](reports/21.md) |
| 22 publication closure | Open: publish the draft GitHub release after accepted media and green CI; manual social preview upload |

No mandatory 1.0 scope was cut. Optional scope frozen under V1-052: the
live Jev audit and the three P2 figures.

## Checks actually completed

| Scope | Result | Receipt |
|---|---|---|
| Combined integration head `ff0f66c` | 4,163 ordinary tests passed, 1 explicit obsolete-manifest observation skip, 31 deselected; 25 packaging passed; 6 cached-native passed, no skips; all 4,195 collected cases accounted for; 590 docs/visual checks; hooks; full static regeneration with 16 README references | [REVIEW 19](reviews/19-combined-static.md) |
| Hosted CI at `ff0f66c` | Ten source/assets jobs SUCCESS (37599734305, 37599764080) | same |
| Pre-tag documentation `75626ae` | 110 docs tests, docs gate, hooks; independent review | [REVIEW 20 pre-tag](reviews/20-pretag.md) |
| Pre-tag head `4d7966f` | Ten jobs SUCCESS (37602503653, 37602539917); rehearsal 37602547044 SUCCESS; bare candidate checker exit 0 on clean `main` | same |
| Tagged release run 37603727302 | Nine jobs SUCCESS; verify matrix success; assets job passed; post-publication checks as tabled above | [REVIEW 20](reviews/20-publication.md), receipts |
| Final blind README first screen | Fresh context-free reviewer named purpose, audience, offline recomputation and all three evidence limits from one 1366×900 screenshot at `277d729` | [receipt](reports/readme-ten-second-final.md) |
| Raw demo capture | 21.517 s cast, exit 0, demo 0 / fixed replay 0 / bad replay 1 from the official wheel; GIFs 24.51 s, 8 frames, 979×918 px, 571,102 and 569,379 bytes, two identical renders each; parent replayed both recorded bundles through the bound installed executable with the same verdicts | [REVIEW 14](reviews/14-capture.md), [REPORT 14 capture](reports/14-capture.md) |

Counts are per check and not additive. The demo's own output reported
`duration_s: 0.129` inside the recording; no other timing is claimed.

## Deviations from the research and the plan

The v0.1 [reconciliation](../RECONCILIATION.md) dispositions stand. The v1
[audit](AUDIT.md) mapped the research expectations to v1.0; the material
departures during execution were:

| Expectation | What happened | Reference |
|---|---|---|
| Researcher A's enforcement/containment tooling | Remained rejected; no sandbox, proxy or action-enforcement claim | [AUDIT](AUDIT.md), [threat model](../../docs/threat-model.md) |
| Optional Jev adapter with a real recorded audit (plan option (a)) | Adapter shipped as PROVISIONAL with mocked-transport evidence; the recorded audit was preregistered but never collected because the harness denied the key-loading step; deferred to 1.1 rather than fabricated | V1-041, V1-052, [ADR 0017](../../docs/decisions/0017-experimental-decision-provider.md) |
| 14:00 IST Jev-cut trigger | Activated, then superseded by the human ("not a hard one"); the reviewed adapter was retained and the removal drafts were never merged | V1-049, [REVIEW 19 cancelled cuts](reviews/19-cancelled-cut-attempts.md) |
| README figures at an assumed 880/360 px column | GitHub measured 838 px (desktop) and 254–294 px (mobile); three SVG groups were reflowed and the README breakpoint moved to 1280 px | V1-051, [ADR 0020](../../docs/decisions/0020-reproducible-visual-assets.md) |
| Architecture figure merge | Two prerequisite merges were denied to the executor and completed manually by the human; the figure then followed the normal review path | V1-050 |
| Recording procedure's Python-shebang premise | uv 0.12.5 writes a `#!/bin/sh` relocatable launcher; the environment binding was established from the launcher's exec target and `pyvenv.cfg` instead, accepted as a bounded factual deviation. Package probes and the capture ran under the controlled `env -i` prefix; file diffs, validation and rendering used the authoring environment | [REVIEW 14](reviews/14-capture.md) |
| P2 figures, broader statistics, roadmap items | Not implemented; broader comparisons, slices, sequential designs and signed evidence stay out of 1.x scope | V1-052, [AUDIT](AUDIT.md) |

Historical note on model usage: the initial Task 02 and Task 09 attempts
were run by non-Fable models, rejected under V1-007, preserved as drafts and
reimplemented directly by Claude Fable 5.1; no accepted implementation is
attributed to those attempts, and their usage is counted in the spend
section below.

## Source and case identity preserved

- The product source fingerprint `8f316f67…98ed3` did not change between the
  retained candidate `5e7931a`, the integrated head `ff0f66c`, the tag and
  this report; the compatibility registry holds exactly it and the example's
  original producer.
- The original `examples/action_gate` archive bytes and its external lock
  digest are unchanged and replay under the release.
- The Task 06 preregistration (959 fixed cases, thresholds and inventories)
  is frozen and unrun; any 1.1 live run must keep it fixed before inference.
- The recording's two demo locks carry the same fingerprint and
  `replay_engine_version actseal-choice-v1` as the release.

## Known limitations and open issues

- Replay checks bounded data and recomputes semantics offline. A trusted
  lock does not authenticate rewritten responses, inference execution or
  label truth; there are no signatures or remote attestation in 1.x.
- Population claims need independent cases and one prespecified attempt
  under a fixed policy; the demo and example are synthetic
  (`evidence_scope=demo`).
- Native Laya support covers only the documented tested CPU configurations
  on arm64 macOS and x86_64 glibc Linux; no GPU, Windows, Intel Mac, Linux
  ARM, musl or native Python 3.13 inference evidence.
- The experimental Jev adapter's identity is a vendor-reported version; its
  key-exclusion guard covers adapter-generated metadata and diagnostics, not
  arbitrary raw inputs or provider bodies.
- The live Jev audit and the P2 figures are deferred to 1.1. The social
  preview is delivered as a file; its upload in GitHub settings is manual
  and not done. The GitHub release is still a draft.
- Post-publication media (the recording and its GIFs) is absent from the
  immutable tag, the wheel, the sdist and the PyPI package page; it exists
  only in the later repository, as Decision 2A approved.

## Spend

No paid inference API was used: zero Jev requests, no credit consumed, and
the Jev balance was not measured. Claude Code ran under the existing
subscription. The observed pre-tag ledger (`spend-pretag-observation.md`,
Codex read-only aggregation over 88 orchestration streams, 92 result records
and 17 Claude sessions, taking the maximum cumulative meter per session
rather than summing resumes) gives a **list-price equivalent of
USD 536.13327225**: Fable 5.1 526.69239050, Sonnet 5 3.20635100, Opus 5
6.21186675, Haiku 4.5 0.02266400. That figure is not a billed amount; actual
subscription charges are unknown, Codex and manual work are outside it, and
Codex will refresh the final session maxima after Tasks 14 and 21 before
closure. The non-Fable amounts are the rejected initial attempts noted above.
Publication completed on 7 October 2026 within the planned window; the
optional 17:59 cut was unused because scope was frozen earlier (V1-052).

## Next three steps

1. **Close the publication (Task 22).** After the Task 14 activation and this
   documentation pass independent review with exact-head green hosted CI,
   publish the draft GitHub release 405628842 with these receipt-backed notes
   and upload the social preview manually. Never move the tag or rebuild the
   released distributions.
2. **Run the preregistered live Jev audit in 1.1** only once the key-loading
   prerequisite is effectively available, with a fresh compatible
   implementation review and the frozen 959-case preregistration, thresholds
   and inventories unchanged before inference; report it in full, including
   BLOCK, INCONCLUSIVE or ERROR.
3. **Gather one external integration and the P2 figures for 1.1.** Record one
   independently reproduced application integration with held-out data and
   publish its exact scope, and implement the where-it-sits,
   decision/verdict-matrix and evidence-boundary figures through the same
   pinned renderer and review gates.
