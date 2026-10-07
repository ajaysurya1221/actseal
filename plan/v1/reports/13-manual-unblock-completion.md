# REPORT 13 — completion after the human's manual merges (V1-036, V1-049, V1-050)

Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, resuming the Task 13 session on `claude/v1-13-architecture-preparation`. Source commit at dispatch: `05eca93e6623c181927a53100114b85d17459968` (the human's second merge, verified clean by Codex). No merge command was run in this dispatch. No subagent, other model or nested Claude. No personal-memory writes, downloads, secrets, provider or model call, push, main merge or publication. All earlier reports (`13-preparation.md`, `13-blocked.md`, `13-blocked-02.md`, `13-blocked-03.md`, `13-blocked-04.md`) are unchanged.

Status: **DONE candidate** for the Task 13 scope and V1-036 architecture content. The original done-when command passes against committed files. Structural tests, full visual suite, strict typing, hooks and the ordinary test suite pass. Temporary review pixels were rendered with the pinned resvg and inspected by the executor; Codex's independent pixel, source, regeneration and hosted CI review remains required before ACCEPT, as does the final README/blind review.

## Commits (after `05eca93`)

| Commit | Subject |
|---|---|
| `25b47ab213d0128a082d72e6d4f8bc07d46be2a3` | feat(assets): draw the experimental Jev adapter inside the live-inference boundary |
| `8b5c2154d70f9546e243d1227d5f1854f4f59620` | feat(assets): register the four architecture outputs and export the module |
| `1f34abcbf8c3b3fc0a1f81fd7e371797cc39fa5d` | test(assets): cover the Jev node, registration and the second font-free renderer |
| `f924fa498d0f65eb92566eacb100c6911ae397f0` | assets: generate the four architecture SVGs |
| `0cac6deb85a380d7e224244dece7f6f81938872b` | docs(assets): describe the architecture figure in the toolchain README |
| (this report) | docs(v1): REPORT 13 manual-unblock completion |

`git diff --stat 05eca93 HEAD` touches exactly ten files, all owned: the four SVGs, `docs/assets/src/README.md`, `actseal_assets/__init__.py`, `architecture.py`, `inventory.py`, `tests/visual/test_architecture.py`, `tests/visual/test_render_cli.py`. `git diff --stat 7820dba HEAD` over the hero, how-it-works and social outputs, their renderers, `tools.toml` and `fonts/` is empty: every accepted byte is preserved. No product, root README, dependency, workflow or other-lane file changed.

### Owned files at HEAD (git blob SHA-1)

| File | Blob |
|---|---|
| `docs/assets/src/actseal_assets/architecture.py` | `d8921272e54d5bd03ddd375e813e280645ef00cb` |
| `docs/assets/src/actseal_assets/inventory.py` | `1ffde0585051a4ac037777624356a34913f1abc9` |
| `docs/assets/src/actseal_assets/__init__.py` | `2717bb2649ea9e2d479163604290f8462df3db93` |
| `tests/visual/test_architecture.py` | `f8c2f4f91fccc80cf2f89fb901429032099bd011` |
| `tests/visual/test_render_cli.py` | `5b8bb256055b6216a5ef5b322dcf081b2a3584fa` |
| `docs/assets/src/README.md` | `7975cacab47d18abd7b2b7926cee23fa6ab869e4` |

### Generated outputs (SHA-256; `render.py --check` confirms byte-identical regeneration)

| Output | Size | Bytes | SHA-256 |
|---|---|---|---|
| `docs/assets/architecture-light.svg` | 1600×980, displayed at 880 | 9,782 | `73123c12ab87c54c520ab198d48e6658a6ba789538a2f9c876d5a1d9db1506db` |
| `docs/assets/architecture-dark.svg` | 1600×980, displayed at 880 | 9,782 | `8a3b1636836382eaa32bfa7d8fadebf3ce10b4b8d91f58bcb492c0d259a49fbe` |
| `docs/assets/architecture-mobile-light.svg` | 720×2166, displayed at 360 | 9,506 | `56625f9a59a49f9d15d47d56c8dcd9b6c14a5905dfc919b6cedcc292ba20563a` |
| `docs/assets/architecture-mobile-dark.svg` | 720×2166, displayed at 360 | 9,506 | `e0e3075325bdeb40292d999039581e48ad74f3aff6867ff0c57be617e8881f97` |

### Integrated provider sources the figure was mapped against (blob at HEAD)

`src/actseal/experimental/providers/jev.py` `8027e47946595af3f3a37139069774d8ab90841e`; `src/actseal/runner.py` `da6990a16e88e7bcb0abc80293095705ac3ff90f`; `src/actseal/cli.py` `cf75031962b0c44d70d773a71e5aad4d736b7324`. Read first-hand after the merges: the Jev module docstring opens "Experimental Jev cloud adapter (PROVISIONAL ...)"; the runner constructs it only in the explicit `"jev"` branch of `open_model` with a lazy import; the CLI accepts `--provider jev` only together with `--experimental-provider`; `docs/providers.md` states no live Jev request has been made or verified. All other module placements were re-checked against the merged tree; the module set differs from the preparation report only by the three `experimental` files.

## Module-to-node mapping

Seven groups (`<g id="group-…">`). Every `src/actseal/**/*.py` module is drawn exactly once as an accent-coloured name; the only undrawn files are the three package markers `adapters/__init__.py`, `experimental/__init__.py`, `experimental/providers/__init__.py`, whose members are all drawn. The test derives the module set by scanning the checkout, not from a constant.

| Group | Heading | Drawn modules | Note lines |
|---|---|---|---|
| `group-contracts` | Contracts / locks | `contract`, `records`, `errors`, `serialization`, `locking`, `compatibility` | parse, seal, validate · no model call |
| `group-cli` | CLI / typed API | `cli`, `runner`, `__init__`, `__main__`, `demo_data` | lock, verify, replay, demo |
| `group-providers` | Providers | outside the boundary: `adapters.base`, `adapters.fixture`; **inside the dashed live-inference boundary: `adapters.laya`, `experimental.providers.jev`**, followed by the label "live inference" | fixture: recorded file · laya: pinned checkpoint · **jev: PROVISIONAL opt-in** |
| `group-normalization` | Normalization / policy | `normalization`, `policy` | pure; no provider import · decision per capture |
| `group-assessment` | Assessment / statistics / faults | `assessment`, `stats`, `faults` | 6 synthetic faults; no model call · recomputes decisions, then the verdict |
| `group-evidence` | Evidence | `evidence` | 7-file bundle, bounded · atomic publish |
| `group-replay` | Replay | `replay` | offline; no provider import · recomputes the verdict |

Jev status legibility: the module name is drawn under its real dotted path, not as a stable `adapters.*` member; the same box carries "jev: PROVISIONAL opt-in"; the `<desc>` says fixture and Laya are the stable providers and Jev "is an experimental cloud adapter selected only by explicit opt-in, with no stability promise and no claim here that its service was exercised". No label, title or description contains "verified", "audit", "attest", "live service", or any authentication, inference-occurrence, label-truth or enforcement wording (tested).

## Arrow mapping

Nine directed orthogonal arrows, each inside its source group's `<g>` with `data-source`/`data-target`. Arrows leaving Replay are muted; all others accent.

| Edge | Label | Source behaviour |
|---|---|---|
| cli → contracts | — | `parse_contract`, `parse_cases`, `create_lock`, `parse_lock`, `validate_inputs` |
| cli → providers | — | `open_model` builds fixture, Laya or (explicit opt-in) Jev; `collect` calls `identity`/`decide` |
| providers → normalization | — | each `CapturedOutcome` goes through `normalize` then `evaluate` |
| normalization → assessment | decisions | `DecisionRecord`s are assessed |
| contracts → assessment | 6 synthetic faults | `run_fault_campaign(lock)` derives the captures from the lock; no provider |
| assessment → evidence | verdict, records, faults | `write_bundle` |
| evidence → replay | — | `read_bundle_files`, `decode_rows`, `decode_document` |
| replay → contracts | lock, inputs | `parse_lock`, `validate_lock`, `validate_inputs` |
| replay → assessment | recompute | `assess`, which re-normalizes and re-evaluates every record and fault |

Replay has one inbound edge (evidence) and two outbound (contracts, assessment). No edge touches both replay and providers; the only provider edges are cli → providers and providers → normalization. Tested on all four outputs, together with: arrows axis-aligned, starting on the source box edge and ending on the target box edge, passing through no box interior, no two edges crossing or overlapping, and no label overlapping any other label, arrow or divider under the width model.

## Commands and results

| Command | Result | Exit |
|---|---|---|
| **`uv run --frozen --group assets python docs/assets/src/render.py --check --only architecture`** (done-when, run after the asset commit) | four `matches regeneration`; `check: 1 asset(s) checked; 0 planned/not implemented; 0 error(s)` | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --write --only architecture` (generation) | 4 file(s) written; 0 error(s) | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` (full inventory) | hero, how-it-works, architecture, social match; `4 asset(s) checked; 4 planned/not implemented; 0 error(s)` | 0 |
| `uv run --frozen --group assets pytest tests/visual/test_architecture.py -q` | 51 passed | 0 |
| `uv run --frozen --group assets pytest tests/visual -q` | 335 passed | 0 |
| `uv run --frozen ruff check` on the five owned Python files | All checks passed | 0 |
| `uv run --frozen ruff format --check .` | 367 files already formatted | 0 |
| `uv run --frozen mypy --strict docs/assets/src tests/visual` | Success: no issues found in 29 source files | 0 |
| `uv run --frozen pytest -m "not integration and not packaging" -q` | 3896 passed, 27 deselected in 73.89 s | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `git diff --check` | clean | 0 |

The ordinary suite includes the docs and release tests that previously failed only for missing architecture outputs; none fails now. Integration and packaging markers were not run (unchanged by this task). Hosted CI has not run on this branch.

## Actual pixels (temporary; not committed, not deliverables)

Rendered by the cached pinned resvg 0.48.1 after `tools.verified_binary` re-hashed the retained archive against `tools.toml` (archive SHA-256 `06440eb5…d09f`) and returned `/Users/ajay/.cache/actseal-assets/resvg-0.48.1/resvg`. Command shape: `resvg --width N docs/assets/<file>.svg /tmp/actseal-arch-review/<name>.png`, with system fonts allowed so the generic sans-serif stack resolves to Helvetica on this machine. A first pass with `--skip-system-fonts` produced font-match warnings and was discarded.

| Path | SHA-256 |
|---|---|
| `/tmp/actseal-arch-review/architecture-light-880.png` | `68db28028a173619bf4bd0a26249d6e30b9dff30a25eeecd4292b7436874425d` |
| `/tmp/actseal-arch-review/architecture-dark-880.png` | `cd0d610086861724a609d86931d4b3937bead7a1a66bfe43a0f2af2b1ab9e8f1` |
| `/tmp/actseal-arch-review/architecture-mobile-light-360.png` | `619bda1668af4d4744b0d4ffb345e1663c92460a284468a31c898e22e5dd7a79` |
| `/tmp/actseal-arch-review/architecture-mobile-dark-360.png` | `e13228e7ab447aab6c6c2c6d2ff0a98e2b28f3f995b4e94ae266b8a98017af76` |
| `/tmp/actseal-arch-review/architecture-light-1600.png` | `79f304ea0fb631d7ee76f4f93bf5f92c8461635c125d4d080713c5391e9692e8` |
| `/tmp/actseal-arch-review/architecture-mobile-light-720.png` | `2e607a4a5feaddd2c7c054a6c0c68b9ae3553d711351204a9ddc1f654c1be6a9` |

Executor's own reading of those images (distinct from the structural tests): all seven boxes, nine arrows and labels render as laid out; the dashed boundary visibly encloses exactly the two live lines and the "live inference" label; fixture sits above it; every label is legible at 880 and 360 px; light and dark differ only in colour. Two observations for Codex: on mobile the two muted replay return arrows run in left-margin channels 12 units apart (about 6 px at 360), visibly separate but close; on desktop the "Normalization / policy" heading wraps to two lines. Nothing was altered to pass the pixel review. The `/tmp` directory may be deleted at any time; these are review aids, not receipts.

## Deviations and judgement calls

1. **Desktop canvas finalized at 1600×980**, not the provisional 900: the Providers box grew by the Jev line, the boundary padding and a third note, and the renderer refuses to shrink text. The inventory comment lists architecture among the finalized heights.
2. **Desktop columns widened by 8 units** (margin 24→20, gap 40→36) so `experimental.providers.jev` (328 units at size 26) fits an unshrunk 331-unit column.
3. **Note wording** is `jev: PROVISIONAL opt-in` rather than "PROVISIONAL, explicit opt-in" (which did not fit); the description carries the full "explicit opt-in" phrase.
4. **Render CLI test updates are counts only**: implemented set gains `architecture`, planned set loses it, bootstrap `--check` expects eight uncommitted font-free outputs and `--write` writes eight; the planned-asset example moved from `architecture` to `where` (Task 16). Every missing-font (hero), missing-resvg (social) and skipped-rendering negative assertion is unchanged, and `PREREQUISITE_ERRORS` stays 5.
5. Adjacent horizontal arrows remain unlabelled (gap too narrow), and replay → normalization is expressed through replay → assessment, both as in REPORT 13 preparation.
6. The pixel renders used system fonts, which the committed SVGs also rely on in a browser; the stack ends in `sans-serif` per the validator. No font was downloaded or added.

## Remaining gates (not this executor's to close)

- Codex independent review of pixels, source, regeneration and exact-head hosted CI; the final README integration (Task 08 ordering) and blind ten-second review.
- If provider integration later fails its cut, V1-036 requires an explicitly reviewed amendment to remove Jev and regenerate this figure; the figure is data-driven (`GROUPS["providers"].live`), so that is a two-line source change plus regeneration and test updates.

## Spend

Claude subscription session only; cost not measured. No paid API calls, no model inference, no Jev credit, no downloads. The six resvg invocations ran the already-cached pinned binary. Commits are timestamped 7 October 2026 (IST) and this report follows immediately after.
