# REPORT 08-ADR

Status: PARTIAL (independent documentation-only ADR closure under V1-026;
full Task 08 still depends on accepted Task 07, accepted static P1 assets,
the final README and release notes). Candidate for Codex review; DONE is not
ACCEPT.

Executor: Claude Code, model `claude-fable-5-1`, effort high, run directly in
the same session and ownership as REPORTs 08-preparation, 08R, 08R2 and
08R3. Worktree `/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`,
branch `claude/v1-08-reference-preparation`, base
`a8510ede54b384e8c6a4afd28928338bc4247b36` (source-accepted). Nothing
pushed, merged, tagged or released. No nested executors, personal memory,
model/billing/permission change, network, downloads, live providers, keys,
`.env` or `.env.example` access, native tests, mutation harness, example
execution, render or preview. No external worktree or cache path was read.

## Changes

Five new files only; no existing file was modified.

| File | Content |
|---|---|
| `docs/decisions/0017-experimental-decision-provider.md` | PROVISIONAL `actseal.experimental.providers.jev.JevModel(*, offline=False)` behind `--provider jev --experimental-provider`; zero-dependency core/fixture/Laya usable without a key; proprietary BYOK service reading only `JEV_API_KEY`; selected-option probability gating, not vendor confidence; pinned vendor-reported target is not a local artifact attestation; one attempt, no retry/redirect/fallback; key never captured; terms reading is bounded, not a legal guarantee. Status: source-scoped ACCEPT on PR 28 at `c2e27d2235eb98be0f97c9ec6d38b0c8ff235dfa` with eight CI jobs; registration, native receipts, placeholder file, live integration and inclusion pending. |
| `docs/decisions/0018-finite-benchmark-audit.md` | 959-request (320 calibration / 639 verification) Banking77 descriptive audit with the exact approved selection, normalization and policy; no power, population-calibration or IID claim; ARCI planner not misused; calibration never fits the threshold; separate cohorts, full verification denominator, no retries/replacement/tuning, incomplete runs retained as ERROR; CC-BY-4.0 data separate from Apache-2.0 code; the supplement's 90-minute budget, journal and metric rules referenced as normative where they stand. Status: preregistration, implementation and live calls not accepted or completed; Task 06 stopped pending a scoped permission decision, incident details left to its receipt; no results or spend invented. |
| `docs/decisions/0019-supported-platforms.md` | Linux/macOS × Python 3.12/3.13 CI matrix; zero-dependency core, Python >= 3.12; Windows unsupported because exclusive publication depends on macOS/Linux facilities, no classifier or partial promise; native Laya limited to the documented CPU configuration; security support deferred to ADR 0015/SECURITY with no new exclusion; hosted deterministic checks are not native evidence and the native gate for changed paths is open. |
| `docs/decisions/0020-reproducible-visual-assets.md` | Single renderer `--write/--check`, authoring-only pinned licensed toolchain from PLAN section D (`tools.toml`, `NOTICES.md`); light/dark/mobile SVG, 1280×640 PNG social preview, raw `.cast` and real GIF rules; no scripts/external fonts/stylesheets in SVG; genuine post-publication PyPI recording under Decision 2A; no fake output, stock security symbols or unsupported metrics; acceptance is actual rendered review, repeated regeneration and the blind ten-second test, not unit passes; P1 mandatory, P2 cut line; user uploads the social preview manually after file delivery; pipeline choice distinguished from unmeasured reproducibility. Status: toolchain accepted (Task 10), downloads/previews and every actual asset pending; no generated media claimed. |
| `plan/v1/reports/08-ADR.md` | This report. |

Existing ADR 0015 is untouched and not duplicated; identifier 0016 is
reserved for Task 09's release-promotion ADR on its own branch and is not
created here. Each ADR cites the approved PLAN passages supplied with the
task and existing receipts; none adds product policy, interfaces, formats,
exclusions or legal assurance.

## Checks

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen ruff format --check .` | 268 files already formatted (Markdown fences included) | 0 |
| `git diff --check` | no output | 0 |
| `uv run --frozen pytest tests/docs/test_links.py` | 19 passed (existing read-only link checks; they cover the nine owned reference docs, not `docs/decisions/`) | 0 |
| `ls` of every relative link target used by the four ADRs | all nine targets exist | 0 |

Not run, as allowed by the packet for compact prose-only ADRs: the full
docs suite, product tests, native tests, mutations, example execution,
renderer, previews, package installation, network. No test mirroring the
ADR prose was added. `tools/check_release.py docs` remains absent on this
branch and is still reported as not run.

## Deviations

None. One judgement call: ADR 0018 points to the supplement
(`plan/v1/tasks/06-collection-supplement.md`, present in this worktree) for
its exact bin boundaries, journal and 90-minute budget rules instead of
restating them, so the ADR cannot drift from the approved text.

## Open issues

- Full Task 08 dependencies are unchanged: README composition, CHANGELOG,
  release notes, application-example claims and asset references wait for
  accepted Task 07 and static P1 assets.
- ADR 0017 and 0018 must be revisited at the Jev inclusion decision
  (Task 19): either record the shipped PROVISIONAL state and audit receipts,
  or record the cut to a later 1.x release. ADR 0020's pending list closes
  only with actual accepted assets and the post-publication recording.
- Out-of-ownership items noted in earlier Task 08 reports (README, CHANGELOG,
  `docs/publishing.md`, installed Alpha/0.1.0 metadata) remain for Codex.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this resumed CLI process; elapsed time unknown until
  Codex's stream result is available. Not estimated.
