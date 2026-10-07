# REVIEW 14 — Activated recording implementation

Verdict: ACCEPT (implementation and additive receipt corrections).
Reviewed commit: `31c99168a2fe4d2eb8d0fbd07d781fff5d23aa8f`.

## Findings ordered by severity

No implementation blocker. Untouched raw cast and light/dark GIFs match the
accepted capture. Public provenance preserves the original receipt object and
its source-file hash. Only approved inventory registration, corresponding visual
test expectations and procedural status/launcher clarification changed.
Renderer/helper/pins/other figures/runtime/registry/original example unchanged.
All negative prerequisites remain; the social-only check still excludes demo.

Receipt arithmetic needs additive correction: 15 generated outputs (12SVG,
2GIF,1PNG), not17. Each regeneration command runs four agg invocations; both
commands total8, not4. The original raw-capture phase separately rendered4.
Clarify the original capture report's env-i scope as package probes/capture,
not every authoring validation/render command. Prior reports stay preserved.

## Independent checks

- Parent: `uv run --frozen --group assets pytest tests/visual` — 481 passed,1.91s.
- Parent: `uv run --frozen --group assets python docs/assets/src/render.py --check` — all15 generated outputs byte-identical,16 references,5 implemented groups,3 planned P2 groups,0errors.
- Parent: `uv run --frozen mypy --strict docs/assets/src tests/visual` —33filesPASS.
- Parent: `uv run --frozen pre-commit run --all-files` —lint/format/typesPASS.
- Independent `/root/v1_core_contract_review`: source/bytes ACCEPT;123focusedtestsPASS0.68s; no frozen-path drift.
- Raw capture and actual decoded pixels were independently reviewed in14-capture.md.

## Required changes

Claude-owned additive14-activation-correction report; then Task21 integration
and exact-head hosted Linux regeneration/source matrix before main merge.
No source or test repair needed for receipt-only corrections.

## Follow-ups filed

Task21 owns README/final report/release notes; Task22 owns final public closure.
Published tag/distributions remain immutable. This scoped acceptance does not
claim hosted Linux GIF regeneration before its actual job completes.

## Correction closure

Additive report `a3397fe` corrects the output/agg counts and controlled-environment
scope; source, tests and assets remain byte-identical to reviewed31c9916.
Parent read the correction and accepts it. Its Spend phrase about no tool
executions is interpreted narrowly as no rendering/service work: file/git tools
were used to make the report commit. Actual billing remains unknown.
Exact-head hosted regeneration and Task21/22 still gate main/final publication.
