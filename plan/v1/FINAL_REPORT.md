# Actseal v1.0.0 — release report

**PUBLISHED — 7 October 2026.** `actseal` 1.0.0 is live on PyPI and as the
public GitHub release
[v1.0.0](https://github.com/ajaysurya1221/actseal/releases/tag/v1.0.0), both
from the annotated immutable tag `v1.0.0` (`04c10d3fec60727310cf65acf6528f13264a26d4`).
Tagged workflow run [37603727302](https://github.com/ajaysurya1221/actseal/actions/runs/37603727302)
completed all nine jobs after the owner approved the `pypi` environment:
build once, four-platform verification of the exact bytes, static asset
regeneration, Trusted Publishing, clean-container verification from the
public index, and mirroring to a draft GitHub release. Publication-scope
ACCEPT is recorded in [REVIEW 20](reviews/20-publication.md); the pre-tag
gate in [REVIEW 20 pre-tag](reviews/20-pretag.md).

**Release closure (dated checkpoint, 7 October 2026).** The post-publication
media was reviewed at PR 48 head `f26af8ff43302020be5dbc8eeb6c497d089fdbc2`
(ten hosted source and assets jobs SUCCESS, runs 37607862358 and
37607886554) and merged to `main` as `0a0a2288bed813e9fcbf7116ef97294912ca04b1`
(2026-10-07T10:37:34Z). The accepted post-publication documentation was
reviewed at PR 49 head `814059a78dfad9eb1aad51fe1802fbf85b98302d` (ten
hosted source and assets jobs SUCCESS, runs 37609789928 and 37609797286)
and merged as `3c3a339e86f0c17fd55bf529b90f1c26c38d0c0e` (10:54:59Z). GitHub
release 405628842 was then published at 2026-10-07T10:55:05Z (`draft`
false, `prerelease` false, shown as Latest, title "Actseal 1.0.0") with the
accepted release notes byte-equal to `plan/v1/RELEASE_NOTES.md` (SHA-256
`9cc94039…`) and its four uploaded assets unchanged; the receipt is
[`plan/v1/receipts/github-publication.json`](receipts/github-publication.json)
and the public verification is [REVIEW 22](reviews/22.md), which accepts
the public release scope. The tag was never moved and no distribution was
rebuilt or replaced. This closing update to the report is itself subject to
independent review and exact-head hosted CI before it merges; no result of
that review or CI is claimed here, and no second container run was made.
This report records what shipped, what did not, and the receipt for each
claim.

| Release field | Verified result |
|---|---|
| Tag target | `04c10d3fec60727310cf65acf6528f13264a26d4`, annotated, never moved |
| Implementation fingerprint | `8f316f67…98ed3`, unchanged since candidate `5e7931a` (exact value in [versioning](../../docs/versioning.md)) |
| Wheel | `actseal-1.0.0-py3-none-any.whl`, 101,900 bytes, SHA-256 `4497fef4878cb67f03845e13f91c8b8c4e7686361198d0ebc52a1764157ae3bf` |
| Sdist | `actseal-1.0.0.tar.gz`, 2,054,855 bytes, SHA-256 `aa31ccf9f5cce30c40269dd5d9904ef61f147f9c4aaf21e3db288981b3278da6` |
| Actions artifact | id 11474201373, digest `sha256:30fff8a3ad125cfee12f1101b047ade5cadf445919402fcefa4c32df9fa0d8af`. The four verify-matrix jobs, the publish job and the mirror job downloaded this exact artifact by id and compared its hashes with the build checksums; verify-published downloaded the official PyPI files instead and compared them with the build checksums; the assets job downloads no distribution |
| Public index verification | Pinned clean container, installed outside the checkout: `actseal 1.0.0`; demo exit 0 (bad BLOCK, fixed PASS); fixed replay 0; bad replay 1; both files match the build checksums and PyPI's declared digests |
| Attestations | One PEP 740 attestation per file from GitHub `ajaysurya1221/actseal`, workflow `publish-pypi.yml`, environment `pypi`, subjects equal to the file digests. Presence, identity and subjects inspected; no independent cryptographic verification is claimed |
| Independent download comparison | Codex downloaded the official PyPI files and the assets of release 405628842 (then still a draft) separately; both pairs byte-identical and equal to the build checksums; independent receipt reviewer ACCEPT ([REVIEW 20](reviews/20-publication.md)) |
| GitHub release | 405628842, published 2026-10-07T10:55:05Z at [releases/tag/v1.0.0](https://github.com/ajaysurya1221/actseal/releases/tag/v1.0.0), not draft, not prerelease, Latest. Four uploaded assets: `actseal-1.0.0-py3-none-any.whl` (id 618308471, 101,900 bytes, `sha256:4497fef4…`), `actseal-1.0.0.tar.gz` (id 618308469, 2,054,855 bytes, `sha256:aa31ccf9…`), `release-receipt.json` (id 618308475, 4,263 bytes, `sha256:bd69dcad…`), `SHA256SUMS` (id 618308468, 184 bytes, `sha256:f96cf664…`); GitHub also offers its automatic source archives. Public rendering observed: the notes' how-it-works SVG loaded at 1600×400 and the repository README's recording loaded at 979×918 ([REVIEW 22](reviews/22.md), `github-publication.json`) |
| Hosted CI | Pre-tag head `4d7966f`: ten source/assets jobs SUCCESS (runs 37602503653, 37602539917) and final rehearsal 37602547044 SUCCESS; `git diff 4d7966f..04c10d3` empty; `main` CI 37603576993 at the tagged source SUCCESS; reviewed PR 48 head `f26af8ff43302020be5dbc8eeb6c497d089fdbc2`: ten source/assets jobs SUCCESS (runs 37607862358, 37607886554), then merged as `0a0a2288bed813e9fcbf7116ef97294912ca04b1`; reviewed PR 49 head `814059a78dfad9eb1aad51fe1802fbf85b98302d`: ten source/assets jobs SUCCESS (runs 37609789928, 37609797286), then merged as `3c3a339e86f0c17fd55bf529b90f1c26c38d0c0e`. The closing-document commit after `3c3a339` has its own pending review and CI, not claimed here |
| Receipts | `plan/v1/receipts/release-receipt.json`, `postpublish-receipt.json`, `SHA256SUMS` (committed at `712fb78`), `github-publication.json` (public release event), `claude-usage.json` and `claude-usage-final.json` (dated usage observations); [RELEASE_NOTES](RELEASE_NOTES.md) maps each release claim to them |
| Paid inference | Zero Jev requests observed in the sprint; no paid model API. Subscription usage is recorded below as an API-equivalent observation, not a charge |

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
| 14 genuine PyPI demo recording | Raw capture from the official 1.0.0 wheel ACCEPT at `f55fd5b` ([REVIEW 14 capture](reviews/14-capture.md)); activation ACCEPT at `31c9916` with additive correction `a3397fe` ([REVIEW 14 activation](reviews/14-activation.md)); merged to `main` as `0a0a228` after ten hosted jobs. Raw cast 21.517 s with exits 0, 0 and 1; GIFs 24.51 s; 15 generated outputs (12 SVG, 2 GIF, 1 PNG) regenerate byte-identically |
| 16–18 P2 figures | **Cut to 1.1** (V1-052); not implemented; evidence limits remain in plain text |
| 19 release candidate integration | ACCEPT `ff0f66c` → `main` `277d729` ([REVIEW 19](reviews/19-combined-static.md)) |
| 20 release gate and publication | ACCEPT ([REVIEW 20 pre-tag](reviews/20-pretag.md), [REVIEW 20](reviews/20-publication.md)) |
| 21 final documentation | This report, the release notes, the launch draft and the README recording section; see [REPORT 21](reports/21.md) and [REPORT 21 finalization](reports/21-finalization.md) |
| 22 publication closure | ACCEPT for the public release scope ([REVIEW 22](reviews/22.md)): release 405628842 published 2026-10-07T10:55:05Z with the accepted notes and four unchanged assets after PR 49 head `814059a7` passed ten hosted jobs and merged as `3c3a339`. The integration of this closing documentation update is the remaining review step. The social preview upload is optional, non-blocking and not claimed |

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
| Raw demo capture | 21.517 s cast, exit 0, demo 0 / fixed replay 0 / bad replay 1 from the official wheel; GIFs 24.51 s, 8 frames, 979×918 px, 571,102 and 569,379 bytes, two identical renders each; parent replayed both recorded bundles through the bound installed executable with the same verdicts | [REVIEW 14 capture](reviews/14-capture.md), [REPORT 14 capture](reports/14-capture.md) |
| Recording activation `31c9916` | Parent: 481 visual tests; 15 generated outputs byte-identical with 16 references; strict typing over 33 files; hooks. Independent reviewer: 123 focused checks, no frozen-path drift. Additive correction `a3397fe` fixed the output count (15, not 17), the agg call count and the controlled-environment scope | [REVIEW 14 activation](reviews/14-activation.md), [correction](reports/14-activation-correction.md) |
| Reviewed PR 48 head `f26af8ff43302020be5dbc8eeb6c497d089fdbc2` | Ten hosted source and assets jobs SUCCESS (runs 37607862358, 37607886554; both report that head SHA), then merged as `0a0a2288bed813e9fcbf7116ef97294912ca04b1` | this report's dispatch; hosted runs |

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
| Recording procedure's Python-shebang premise | uv 0.12.5 writes a `#!/bin/sh` relocatable launcher; the environment binding was established from the launcher's exec target and `pyvenv.cfg` instead, accepted as a bounded factual deviation. The controlled `env -i` environment governed the package probes and the capture; file diffs, validation and rendering used the authoring environment. No re-recording or retiming occurred | [REVIEW 14 capture](reviews/14-capture.md), [correction](reports/14-activation-correction.md) |
| P2 figures, broader statistics, roadmap items | Not shipped in 1.0.0: P2 figures, broader comparisons, per-slice gates, sequential designs and signed evidence. They are not prohibited for 1.x; any later addition follows the additive, separately versioned rules of [ADR 0015](../../docs/decisions/0015-v1-stability-and-replay-compatibility.md) and leaves existing stable behaviour unchanged | V1-052, [AUDIT](AUDIT.md) |

Executor history: the Fable-led Task 02 and Task 09 sessions delegated
parts of their early work to non-Fable workers (Sonnet and Opus). Those
drafts were not accepted; under V1-007, the primary record, they were
preserved with hashes, restored to baseline and reimplemented directly by
Claude Fable 5.1. No accepted implementation is attributed to the delegated
drafts, and their usage is included in the spend observation below.

## Source and case identity preserved

- The product source fingerprint `8f316f67…98ed3` did not change between the
  retained candidate `5e7931a`, the integrated head `ff0f66c`, the tag, the
  media head `0a0a228` and this report; the compatibility registry holds
  exactly it and the example's original producer.
- The original `examples/action_gate` archive bytes and its external lock
  digest are unchanged and replay under the release.
- The Task 06 preregistration (959 fixed cases, thresholds and inventories)
  is frozen and unrun; any 1.1 live run must keep it fixed before inference.
- The recording's two demo locks carry the same fingerprint and
  `replay_engine_version actseal-choice-v1` as the release.

## Known limitations and open issues

- Replay checks bounded data and recomputes semantics offline. A trusted
  lock does not authenticate rewritten responses, inference execution or
  label truth. 1.0.0 ships no signatures or remote attestation; a future
  1.x addition would be a separately versioned, opt-in surface.
- Population claims need independent cases and one prespecified attempt
  under a fixed policy; the demo and example are synthetic
  (`evidence_scope=demo`). The recording is an illustrative receipt of the
  public package, not authenticated model evidence.
- Native Laya support covers only the documented tested CPU configurations
  on arm64 macOS and x86_64 glibc Linux; no GPU, Windows, Intel Mac, Linux
  ARM, musl or native Python 3.13 inference evidence.
- The experimental Jev adapter's identity is a vendor-reported version; its
  key-exclusion guard covers adapter-generated metadata and diagnostics, not
  arbitrary raw inputs or provider bodies.
- The live Jev audit and the P2 figures are deferred to 1.1. The social
  preview file is delivered under `docs/assets/social.png`; its upload in
  GitHub settings is an optional, non-blocking manual step that is not
  claimed. The launch post remains a draft and has not been sent.
- Post-publication media (the recording and its GIFs) is absent from the
  immutable tag, the wheel, the sdist and the PyPI package page; it exists
  only in the later repository from `0a0a228`, as Decision 2A approved.

## Spend

No paid inference API was used: zero Jev requests were observed in the
sprint, and the Jev account balance or credit change is UNKNOWN because it
was not inspected. Claude Code ran under the existing subscription.

The committed ledger [`plan/v1/receipts/claude-usage.json`](receipts/claude-usage.json)
is a Codex read-only observation taken at 2026-10-07T10:38:02 UTC, before
this finalization, over 92 orchestration streams, 96 terminal results and
17 Claude sessions, keeping the maximum terminal cumulative meter per
session and never summing resumed-session totals. It records about
**USD 557.91478250 of API-equivalent list-price usage** (Fable 5.1
548.47390075, Sonnet 5 3.20635100, Opus 5 6.21186675, Haiku 4.5
0.02266400). That figure is **not an invoice or billed spend**: the actual
billed cost is UNKNOWN, and Codex usage, manual work and any Claude work
after the observation timestamp are excluded. Later observations supersede
it by date; this report does not assert a final cost. The earlier pre-tag
observation (USD 536.13327225, same method) is preserved as history. A
later terminal metadata snapshot,
[`plan/v1/receipts/claude-usage-final.json`](receipts/claude-usage-final.json),
records its own observation cutoff, method and exclusions under the same
rules; it is likewise not an invoice, this report does not restate its
total, and Codex refreshes the final ledger after this closing update and
before final review. The Sonnet and Opus amounts are the rejected delegated
drafts noted above.
Publication completed on 7 October 2026 within the planned window; the
optional 17:59 cut was unused because scope was frozen earlier (V1-052).

## Next three steps after v1.0.0

The release itself is closed ([REVIEW 22](reviews/22.md)); the tag and the
published distributions are never moved or rebuilt. The post-release
roadmap, in priority order:

1. **Gated preregistered Jev audit.** Run the live audit only once the
   key-loading prerequisite is effectively permitted, with the frozen
   959-case preregistration, thresholds and inventories unchanged before
   inference and a fresh compatible-implementation review; report it in
   full, including BLOCK, INCONCLUSIVE or ERROR.
2. **Independently reproduced application integration.** Record one
   external application integration with genuinely held-out data under a
   prespecified policy, publish its exact scope and limitations with
   permission, and use its friction points to prioritize 1.1.
3. **Deferred P2 figures.** Implement the where-it-sits,
   decision/verdict-matrix and evidence-boundary figures through the same
   pinned renderer, measured-width validation and review gates.
