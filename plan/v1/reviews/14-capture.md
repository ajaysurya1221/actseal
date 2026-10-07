# REVIEW 14 — Genuine raw capture

Verdict: ACCEPT (raw capture and equivalent environment binding; activation and hosted regeneration still required)
Reviewed report commit: `f55fd5bab8b150948a405bb00a8726f76794187f` on `claude/v1-14-published-recording`.
Capture source: immutable release `04c10d3fec60727310cf65acf6528f13264a26d4`.

## Findings ordered by severity

No blocking raw-capture finding. The recorded commands use the actual public PyPI
1.0.0 wheel. Independent wheel inspection matches all25 Python files and the
exact approved source fingerprint/registry. The single task-owned environment
matches all40 non-RECORD wheel payload files; report and stream show the same
path/inode and package/dist-info diff exits0 before and after capture.

The procedure's literal Python-shebang premise was inaccurate for uv0.12.5's
relocatable launcher. This capture truthfully used its `#!/bin/sh` launcher,
whose exec target is the sibling environment `bin/python`; wrapper content,
resolved target and pyvenv.cfg establish the equivalent binding. Accept that
bounded factual deviation; do not claim the literal shebang criterion passed.
Headless mode is already provided for noninteractive drivers. TERM=dumb is
recorded literally; no terminal feature, retiming or output rewrite is claimed.
The interpreter was selected again from the project-free warm-up directory
before capture. No capture was taken with the checkout's interpreter.

Parent inspected unedited output and header: 3626 bytes, SHA256
`cdce70c61100d9b38c247db272517ca3f28b7c01c84d38c5518b59feb54963e6`,
21.517 seconds, 21 output events and a single final exit0, no input/resize/marker
events, LANG/TERM only. Real outcomes are demo0 (badBLOCK/fixedPASS), fixed replay0,
bad replay1. Parent independently reran both recorded bundles through the bound
installed executable from /tmp with a clean environment: PASS0 and BLOCK1, same
counts, bounds and lock digests; neither replay changed evidence.

Parent decoded both GIFs using Pillow, independently counted8 frames and24.51s,
compared both repeated renders per theme, and viewed actual output frames around
5/14/21s (light and dark). Light571102 bytes and dark569379 bytes, 979x918,
correct chronological output/exit labels, no invented result. Raw recording and
renderings are illustrative receipts, not authenticated model evidence.
Independent reviewer `/root/v1_receipt_review` corroborated raw structure,
package identity, controls and the documented launcher deviation.

## Required changes

Activate only V1-053-owned paths: copy raw bytes unchanged, both theme GIFs,
provenance, existing renderer registration and narrow planned-to-implemented test
expectations. Update the procedure to describe both accepted launcher forms with
equally strict target/payload binding and preserve this original report/attempt.
Run all exact visual/regen/hooks/type checks. No runtime, package, registry, model,
threshold, original archive, tool pin or other figure change is authorized.

## Follow-ups filed

Task14 activation and exact-head hosted Linux rendering remain; Task21 integrates
README/final receipts afterward. This is not final release ACCEPT.

## Additive precision note

The independent reviewer confirms raw-capture ACCEPT at the full report commit.
REPORT14-capture's broad statement about every command after warm-up using env-i
is imprecise: package probes and capture used that controlled environment; file
diffs, validation and rendering used their separate authoring environment. This
qualification preserves the original report and does not change capture binding.
The final docs must not repeat the broader claim. No secret read was observed.
