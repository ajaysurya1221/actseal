# v2 assets execution report — 13 November 2026

Status: requested figures regenerated and all visual checks pass. The combined
Done-when test gate is **not satisfied**: one documentation test outside this
task's ownership still requires the superseded hero wording. No independent
third-party ACCEPT or hosted CI result is claimed.

Branch remains `claude/v2-foundations`. No branch switch, commit, push, stash or
revert occurred. Existing reviewed work was retained. The direct task authorizes
this report in addition to its asset/test/alt-text/Unreleased ownership.

## Changes

| Files | Change |
| --- | --- |
| `docs/assets/src/actseal_assets/architecture.py`, `tests/visual/test_architecture.py` | Draw `selection` with assessment/statistics/faults, `qualification` and `report` with CLI/orchestration/presentation, and `adapters.recorded` plus `experimental.providers.decision_api` with providers. All 27 runtime modules occur exactly once; only three package markers are omitted. |
| `docs/assets/architecture-{light,dark,mobile-light,mobile-dark}.svg` | Regenerated four variants. Decision API joins Laya/Jev inside live inference; fixture/recorded remain outside. |
| `docs/assets/src/actseal_assets/{hero,social}.py`, `tests/visual/test_hero.py`, `docs/assets/hero-{light,dark,mobile-light,mobile-dark}.svg`, `docs/assets/social.png` | Replace only the replay requirement with “replay with packaged registry”; preserve numbers, historical unreleased-producer/fixed-benchmark scope, geometry, type sizes and line counts. Tests retain audit provenance and check the archived producer's packaged registry entry. |
| `docs/assets/src/README.md`, `README.md`, `CHANGELOG.md` | Document updated inventory/layout and replay wording; root README changed only in image alt text, changelog only under Unreleased. |

Desktop architecture remains 1600×980, with columns 371/253/580/280 and evidence
spanning the CLI/provider columns. Mobile remains 720 wide (height derived as
3512). Body sizes remain 27/40 units, validated at 838/254 CSS px with the same
14 px minimum. Long dotted paths wrap at dots without losing characters; tests
reconstruct visible names and compare the entire source inventory. Existing
width, containment, arrow, overlap, legibility and overflow checks were not
relaxed. Shared Jev/decision-API status remains visibly `PROVISIONAL opt-in`.

All four hero SVGs were structurally compared with their originals: after
excluding the accessible description and `card-verdict` group, the SVG trees
are identical. No other hero content or geometry changed.

## Toolchain and denied command

Read `AGENTS.md`, active v2 state/plan/change log, v1 historical state and figure
amendments, contracts/stability guidance, ADR 0020, asset-source instructions,
the assets dependency group and CI assets job before implementation.

This exact command was denied before pytest started (exit **2**):

```sh
uv run --frozen --group assets pytest tests/visual/test_architecture.py -q
```

```text
error: Failed to initialize cache at `/Users/ajay/.cache/uv`
  Caused by: failed to open file `/Users/ajay/.cache/uv/sdists-v9/.git`: Operation not permitted (os error 1)
```

Used the task's explicitly permitted `.venv/bin/python -m` fallback. No cache
override, dependency substitution, permission bypass or download was attempted.
Installed versions match the pins: fontTools 4.66.1, pytest 9.1.1, Ruff 0.16.10,
mypy 2.4.0. The repository verifier checked JetBrains Mono 2.304 font bytes and
license, resvg 0.48.1 archive/binary bytes and agg 1.9.0 binary bytes against the
manifest before use. Existing verified macOS tools were readable/executable.
**No regeneration was blocked; no generated SVG was edited by hand.**

## Verification commands and exit codes

| Command | Exit / result |
| --- | --- |
| `.venv/bin/python -m pytest tests/visual/test_architecture.py -q` (baseline) | **1**: 8 failed, 44 passed; precisely the five omitted runtime modules. |
| `.venv/bin/python docs/assets/src/render.py --write --only architecture --only hero --only social` | **0**: 3 groups, 9 validated outputs written. |
| `.venv/bin/python -m pytest tests/visual -q` | **0**: 490 passed. |
| `.venv/bin/python -m pytest tests/visual tests/docs -q` | **1**: 613 passed, 1 failed; exact failure below. No unregistered-fingerprint test failures occurred in this run. |
| `.venv/bin/python -m ruff check` | **0**: all checks passed. |
| `.venv/bin/python -m ruff format --check` | **0**: 519 files already formatted. |
| `.venv/bin/python -m mypy --strict src tests` | **0**: 126 source files. |
| `.venv/bin/python -m mypy --strict docs/assets/src` | **0**: 17 source files. |
| `.venv/bin/python tools/check_release.py assets --renderer '.venv/bin/python docs/assets/src/render.py'` | **0**: required asset gate. |
| `.venv/bin/python docs/assets/src/render.py --check` | **0**: all 15 existing outputs match byte-identical regeneration; 5 implemented groups, 3 previously planned/unimplemented P2 groups, 0 errors. Each implemented renderer runs twice. |
| `git diff --check` | **0**. |
| `.venv/bin/python -m actseal replay docs/results/jev-audit-2026-10-08/evidence --json` | **3**: `ERROR`, reason `integrity.lock`; separate current-source registration issue below. |

Intermediate checks caught a 1138-unit architecture layout (exit 1), obsolete
status-string expectations (exit 1), and Ruff RUF005 (exit 1). The layout was
reflowed within the unchanged 980-unit limit, assertions now cover both
experimental adapters, and tuple construction was corrected. None was ignored
or suppressed. Hero worker checks: updated tests failed on old copy (3 failed,
22 passed), then focused hero/social checks passed (48 passed, exit 0).

Pinned-resvg raster review covered all eight changed SVGs in light/dark at
838 px desktop and 254 px mobile, plus the 1280×640 social PNG: no clipping or
overlap observed. Raster previews are temporary files under
`/tmp/actseal-assets-review/`; this is local pixel review, not hosted-browser
acceptance. The existing documented small-screen limitation for desktop hero
embeds and the mobile footer's accepted reference-size exception are unchanged.

Pre-edit SHA-256 snapshot comparison verified that only the 17 listed asset,
visual-test, root-alt-text and Unreleased files changed, followed by this report.
README bytes equal the starting file with exactly one alt-string replacement;
all historical changelog sections and non-owned files are unchanged. Read-only
helper review also checked exhaustive module membership, generated bytes and
preservation of the existing geometry checks; it is not an independent ACCEPT.

## Remaining work outside ownership

1. `tests/docs/test_readme.py::test_hero_alt_describes_the_evidence_card_and_the_prose_carries_the_limits`
   fails at line 606 because `HERO_ALT` lines 96–97 still demand the archived
   producer requirement. The same test's line 617 separately demands that old
   string inside every hero SVG. Update the expected alt to “replay with
   packaged registry”, update the positive SVG assertion to that wording and
   retain/add rejection of the obsolete requirement. Preserve the metrics,
   historical producer scope and limitation assertions. This is the sole
   non-fingerprint Done-when blocker; `tests/docs/**` was explicitly not owned.
2. Root `README.md:134` still instructs replay with the archived snapshot. That
   prose is outside the alt-only ownership. The orchestrator should align it
   with packaged-registry replay while preserving the historical 1.0.0/1.0.1
   limitation.
3. The packaged registry contains archived producer
   `167038cb709ff839f26a21ef55cc63ebd988d797ac56e82d0227ecad1a08eb7c` for
   `actseal-choice-v1`, but at the time of this report the then-current running
   fingerprint (later superseded, after a review finding moved report-command
   integrity logic into the fingerprinted `actseal.qualification` module, by
   `1c579ef18c4aada29bc7b0fc2d9b319e13cb30c973ec50484bfa025ccd233b42`)
   was absent. Direct replay therefore returns `ERROR integrity.lock`, not the
   recorded INCONCLUSIVE yet. Final source registration/review belongs to the
   orchestrator's source/registry lane. No registry or evidence was modified.

After those cross-lane corrections, rerun the combined test and quality commands
above. The standard unrestricted authoring/reproducibility commands remain:

```sh
uv sync --frozen --group dev --group assets
uv run --frozen python docs/assets/src/setup_tools.py --tool jetbrains-mono
uv run --frozen python docs/assets/src/setup_tools.py --tool resvg
uv run --frozen python docs/assets/src/setup_tools.py --tool agg
uv run --frozen --group assets python docs/assets/src/render.py --write --only architecture --only hero --only social
uv run --frozen --group assets python docs/assets/src/render.py --check
uv run --frozen python tools/check_release.py assets
```

These are handoff commands, not a request for broader sandbox permission.
Publication, tag, social upload and hosted CI were not performed.

## Spend

No provider/model API calls, tool downloads or paid external services were used.
Codex and delegated-agent actual billed spend/usage receipts are unavailable and
remain **UNKNOWN**; no zero-cost claim is made for agent execution.
