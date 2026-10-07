# REPORT 13 (preparation, V1-028)

Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, dispatched by Codex through the CLI. Worktree `actseal-v1-visuals`, child branch `claude/v1-13-architecture-preparation` started at the reviewed Task 12 head `f712daef51ee005c1b34c9744dbe1d99cf499c33`. No subagent, Agent/Task tool, other model or nested Claude produced any text. No personal-memory writes, downloads, secrets, provider or model call, push, merge or publication. Earlier REPORT files are unchanged.

Status: **PARTIAL** by design. This dispatch authorized source and unit preparation only. Inventory registration, committed SVG outputs, the Task 13 done-when command, rendered arrow/readability review, README integration and the final provider-inclusion reconciliation remain open gates and are listed under "Unrun gates".

## Changes

Commits on `claude/v1-13-architecture-preparation` after `f712dae`:

- `33c028d` feat(assets): draft the architecture figure source for seven shipped groups
- `da557a2` test(assets): check architecture mapping, edges, boundary, fit and sizes
- (this report) docs(v1): REPORT 13 preparation

Owned files only:

| File | Git blob SHA-1 (at commit) |
|---|---|
| `docs/assets/src/actseal_assets/architecture.py` (new) | `b89e946e56a67819e5c48c45fc9405147cb2519a` |
| `tests/visual/test_architecture.py` (new) | `200a11a42f8437f404b72ce3b75e239f1e19b5b0` |
| `plan/v1/reports/13-preparation.md` (new) | this file |

Not touched: `inventory.py` (the `architecture` asset still declares the provisional single `architecture.svg` 1600×900 with `renderer=None`), `__init__.py` (the module is not exported yet; tests import it by dotted name), `docs/assets/*.svg`, `docs/assets/src/README.md`, root README, `how_it_works.py`, `svg.py`, `checks.py`, `pipeline.py`, dependencies, lockfile, product code.

### Sources read (git blob SHA-1 at `f712dae`)

The group mapping below was derived from these module sources, `docs/architecture.md`, `docs/stability.md` and `docs/threat-model.md`. Reports were treated as claims, not evidence.

| Module | Blob |
|---|---|
| `src/actseal/cli.py` | `dd907388ae63ea6fac5392dc8cdb1141501fd303` |
| `src/actseal/records.py` | `7bc1068b6fc6f3c7a031e72a6b3088bbc7aeadb3` |
| `src/actseal/contract.py` | `f047e67641441e4bf754552f12c984fe718b5ea6` |
| `src/actseal/locking.py` | `3fbd872e72fbc512d4a75653e4117c6c4639a2f2` |
| `src/actseal/compatibility.py` | `01f7d302ac5489601f1d17ee8045452b0972a298` |
| `src/actseal/serialization.py` | `8646b97843210b83b9e35cc255febd41ec157a6b` |
| `src/actseal/errors.py` | `316c06197c3e116684a5d90f8b1bbfc033cc176b` |
| `src/actseal/adapters/base.py` | `9b8457c6cbe6e0925fad6f4883167413d14a9201` |
| `src/actseal/adapters/fixture.py` | `d574c61315a90501c4e7dd7a5899de9f8e42ba1a` |
| `src/actseal/adapters/laya.py` | `bdd19ceec8bc118c0f96d15a9aad477d9da876cc` |
| `src/actseal/normalization.py` | `363d3083dc8633b85e5ea5414cd77c8423dd5213` |
| `src/actseal/policy.py` | `53da77d743d690ab1a1f78484a88265567dd7dab` |
| `src/actseal/assessment.py` | `ec4bc3a75983432162ef86793e2155f669e29f2d` |
| `src/actseal/stats.py` | `21a76b457a3a3296cab840e1c28d4d9558b30278` |
| `src/actseal/faults.py` | `7514b846e614ae909cfd20b88d8f7a6db5ac76f2` |
| `src/actseal/evidence.py` | `9947255ff507616a7603e4424dc6754f9031c7bc` |
| `src/actseal/replay.py` | `73ed1b6ae1da3534e6478ed006cc82e103cb7fe4` |
| `src/actseal/runner.py` | `8b4bcbac1a409d32393e92f81f08349c130408f9` |
| `docs/assets/src/actseal_assets/how_it_works.py` (reused, unmodified) | `7784ab80871b020f60f96c1a73363764426b1312` |
| `docs/assets/src/actseal_assets/svg.py` (reused, unmodified) | `4486234a84372c425b861bb6e82ce22d63a5e178` |
| `docs/assets/src/actseal_assets/checks.py` (reused, unmodified) | `46972cfcfbdce449b5cff082e70ab0624a17e598` |
| `docs/assets/src/actseal_assets/inventory.py` (read, unmodified) | `45a5ad690260354eaa3128e7abff4ddd80820088` |

## Module-to-node mapping

Seven groups; every `src/actseal/**/*.py` module is drawn exactly once as an accent-coloured name inside its group box. The only source file not drawn is `adapters/__init__.py` (an 8-line package marker whose three members are all drawn). The mapping follows the boundary table in `docs/architecture.md`.

| Group (SVG `<g id>`) | Heading | Modules drawn | Muted note lines |
|---|---|---|---|
| `group-contracts` | Contracts / locks | `contract`, `records`, `errors`, `serialization`, `locking`, `compatibility` | parse, seal, validate · no model call |
| `group-cli` | CLI / typed API | `cli`, `runner`, `__init__`, `__main__`, `demo_data` | lock, verify, replay, demo |
| `group-providers` | Providers | `adapters.base`, `adapters.fixture`; **`adapters.laya` inside the dashed `live-boundary-providers` rectangle with the label "live inference"** | fixture: recorded file · laya: pinned checkpoint |
| `group-normalization` | Normalization / policy | `normalization`, `policy` | pure; no provider import · decision per capture |
| `group-assessment` | Assessment / statistics / faults | `assessment`, `stats`, `faults` | 6 synthetic faults; no model call · recomputes decisions, then the verdict |
| `group-evidence` | Evidence | `evidence` | 7-file bundle, bounded · atomic publish |
| `group-replay` | Replay | `replay` | offline; no provider import · recomputes the verdict |

Why these placements, from the sources: `locking.py` imports `compatibility`, `contract`, `records`, `serialization` and no provider or fault code; `faults.py` imports `normalization`, `policy`, `records`, `serialization` and no adapter; `assessment.py` imports `faults.fault_capture`, `locking.validate_lock`, `normalize`, `evaluate`, `stats`; `replay.py` imports `assessment`, `compatibility`, `errors`, `evidence`, `locking`, `records`, `serialization` and no adapter; `runner.py` imports the fixture and Laya adapters only inside the branches of `open_model`; `cli.py` imports `replay` and `runner`. `demo_data` is packaged input data used only by `runner.demo_run`, so it sits with the CLI/runner. `errors` is the shared exception module from the records/errors/serialization boundary.

Live-model boundary: the dashed rectangle encloses only the `adapters.laya` line. `FixtureModel` reads one local JSONL file and derives its identity from the file bytes; `run_fault_campaign` is a pure generator from the lock. Neither performs inference, so neither is inside the boundary.

No Jev adapter exists under `src/actseal` (grep for `jev`/`experimental` returned nothing), so none is drawn. The SVG does not mention Jev at all; the description says "The shipped providers are fixture and Laya." The test forbids the token `jev` in every label, title and description.

## Arrow mapping

Nine directed edges, each an orthogonal polyline with one arrowhead, placed inside the `<g>` of its source group and tagged `data-source`/`data-target`. Arrows leaving Replay are drawn in the muted colour; all others in the accent colour.

| Edge id | From → to | Label | Meaning in the sources |
|---|---|---|---|
| `edge-cli-contracts` | cli → contracts | (none; adjacent) | `lock_run`/`verify_run` call `parse_contract`, `parse_cases`, `create_lock`, `parse_lock`, `validate_inputs` |
| `edge-cli-providers` | cli → providers | (none; adjacent) | `open_model` builds the adapter; `collect` calls `identity()`/`decide()` |
| `edge-providers-normalization` | providers → normalization | (none; adjacent) | each `CapturedOutcome` goes through `normalize` then `evaluate` |
| `edge-normalization-assessment` | normalization → assessment | decisions | `DecisionRecord`s are assessed |
| `edge-contracts-assessment` | contracts → assessment | 6 synthetic faults | `run_fault_campaign(lock)` derives the six captures from the lock alone |
| `edge-assessment-evidence` | assessment → evidence | verdict, records, faults | `write_bundle(EvidenceBundle(...))` |
| `edge-evidence-replay` | evidence → replay | (none; adjacent) | `read_bundle_files`, `decode_rows`, `decode_document` |
| `edge-replay-contracts` | replay → contracts | lock, inputs | `parse_lock`, `validate_lock`, `validate_inputs` |
| `edge-replay-assessment` | replay → assessment | recompute | `assess(records, lock, faults)`, which re-normalizes and re-evaluates every record and fault |

Replay has exactly one inbound edge (from evidence) and two outbound edges (to contracts and assessment). No edge joins replay and providers in either direction; the only edges touching providers are cli → providers and providers → normalization. The fault campaign is fed from contracts, not from providers, so the figure does not read as a linear chain in which faults call the live model.

Layout (desktop 1600×900, four 358-unit columns, 40-unit gaps): row 0 is Contracts | CLI | Providers | Normalization/policy with the CLI between the two groups it drives; row 1 is the wide Assessment box under the CLI, Providers and Normalization columns; row 2 is Replay (under Contracts) and Evidence (under Assessment's left end). The empty slot under Contracts is the channel for Replay's two return arrows. Mobile (720 wide, height derived from content) stacks Contracts, CLI, Providers, Normalization, Assessment, Evidence, Replay with spine arrows between neighbours and three side-channel arrows (contracts → assessment on the right margin; replay → assessment and replay → contracts on two left margins). Both canvases draw all nine edges and the same labels.

Typography: desktop headings 32 bold, labels 26 (14.3 px at the 880 px README column); mobile headings 36 bold, labels 30 (15 px at 360 px). "Normalization / policy" wraps to two heading lines on desktop because it does not fit one 326-unit column at 32 bold; nothing is shrunk. Flat colours from the reviewed `LIGHT`/`DARK` palettes, generic-terminated font stack, no transforms, markers, gradients, scripts, styles or external references.

## Tests

`tests/visual/test_architecture.py`, 50 tests, all on in-memory bytes. These are structural checks, not a review of rendered pixels.

- Exact output set and determinism; every output passes `checks.check_output` with the four `Output` declarations the figure will register (1600×900 at 880; 720×`mobile_height()` at 360).
- Exactly seven top-level `<g>` elements; no other containers; headings present.
- Every module under `src/actseal` (scanned from the checkout, not from a constant) is drawn exactly once; the only undrawn source file is the `adapters` package marker; each group's drawn set equals the mapping table above.
- The live boundary is one dashed, unfilled rectangle inside the Providers group containing exactly `adapters.laya` and `live inference`; every other Providers label lies geometrically outside it.
- Edge set equals the table above; each edge sits inside its source group, has one polyline and one polygon, and carries exactly its label or none; replay's targets are `{contracts, assessment}`, its only source is `evidence`, no edge touches both providers and replay.
- Arrows are axis-aligned, start on the source box edge and end on the target box edge (within 6 units), pass through no box interior, and no two different edges' segments cross or overlap.
- Every text fits inside its box (or the canvas, for edge labels) under the width model, and no text bounding box overlaps another text, any arrow segment or any divider line.
- Font-size floors 26/30, headings larger than every label, no transforms, generic family last.
- Forbidden language (authentication, proof, tamper, secure, trust, guarantee, enforce, sandbox, padlock, shield, truth, safe, jev) absent from labels, title and description; description names every module and the key limits.
- Light/dark differ only in `fill`/`stroke`; desktop and mobile carry the same module names, phrases, labels and edges.
- Width model: wrap behaviour, oversized phrase fails with "does not fit", too many lines fails with "desktop layout needs", a diagonal final segment is rejected; palette/font/width model are the reviewed `how_it_works` objects, not copies.

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen --group assets pytest tests/visual/test_architecture.py` | 50 passed | 0 |
| `uv run --frozen --group assets pytest tests/visual` | 286 passed (236 before this task) | 0 |
| `uv run --frozen ruff check docs/assets/src/actseal_assets/architecture.py tests/visual/test_architecture.py` | All checks passed | 0 |
| `uv run --frozen ruff format --check .` | 247 files already formatted | 0 |
| `uv run --frozen mypy --strict docs/assets/src/actseal_assets/architecture.py tests/visual/test_architecture.py` | Success: no issues found in 2 source files | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check Passed; ruff format --check Passed; mypy --strict Passed | 0 |
| `git diff --check` | clean | 0 |

During development the overlap test caught two desktop labels whose descenders touched their own arrow shaft; both were moved one full label gap above the line before the commit. The first layout draft needed 912 units; the row gaps were reduced to 80/60 so the finished layout fits 900 with the overflow check still in place.

## Deviations

1. **Edge labels only on non-adjacent edges.** The four adjacent horizontal arrows (cli → contracts, cli → providers, providers → normalization, evidence → replay) cross a 40-unit gap, where any 26-unit label would overlap the neighbouring boxes; their meaning is carried by the box contents. The five routed edges are labelled.
2. **Replay → normalization/policy is not a separate arrow.** `replay.py` calls `assess()`, and `assessment.py` is what re-normalizes and re-evaluates every record; the drawn edges follow the actual call structure (replay → contracts for `parse_lock`/`validate_*`, replay → assessment for `assess`). The Normalization/policy note "pure; no provider import" and the Assessment note "recomputes decisions, then the verdict" state the recomputation path in words.
3. **Four outputs instead of the provisional single `architecture.svg`**, matching the Task 12 convention. The inventory still declares the provisional single output; changing it is part of the deferred registration.
4. **Heading wrap on desktop** for "Normalization / policy" (two lines) rather than a smaller heading.
5. Implementation was done directly by Fable 5.1 per the no-subagent instruction.

## Unrun gates (all mandatory before Task 13 can be DONE)

- Final provider inclusion decision and reconciliation of the group contents against it.
- `inventory.py` registration (renderer, four outputs, finalized mobile height) and `__init__.py` export; `render.py --write --only architecture`; committed SVGs; the done-when `uv run --frozen --group assets python docs/assets/src/render.py --check --only architecture`.
- Rendered arrow and readability review at 880 px desktop and 360 px mobile, light and dark. Rasterization and previews remain denied in this lane and were not attempted.
- `docs/assets/src/README.md` toolchain section and root README integration (Task 08 ordering).
- Hosted CI on this branch; the full default suite was not rerun here (only `tests/visual` changed and it passed in full).

## Spend

Claude subscription session only; subscription cost not measured. No paid API calls, no model inference, no Jev credits, no downloads. Commits timestamped 2026-10-07 04:31:01 and 04:31:06 IST; this report follows immediately after.
