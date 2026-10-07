# REPORT 21 (finalization, continuation 21R)

Status: DONE for the owned scope. All six required checks exit 0 from this
worktree with the accepted Task 14 media integrated. This report does not
claim ACCEPT; Codex reviews independently. The GitHub release 405628842
remains a draft and is not published by this task; PyPI 1.0.0 is live and
unchanged. REPORT 21 (`plan/v1/reports/21.md`), the Task 14 reports and the
usage ledger are preserved unchanged; this report is additive.

Executor: Claude Code, model `claude-fable-5-1`, effort high, normal
permissions, existing account and billing, no subagent or alternate model.
Branch `claude/v1-21-release-receipts` in worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, continued
from `04e8c8d7bd815bebc483fa6744ac00d18ad3d664` (Codex's merge of the media
`f26af8f` and the usage observation). No tag, product, schema, asset,
pin, registry, package, state, review, PLAN or existing-report edit; no
network, credential, model or provider call; no merge, push or
publication command. No tool operation was denied.

## Commits

| Commit | Content |
| --- | --- |
| `230462c1962c2d0f9580337e717fcfc78806f853` | `plan/v1/FINAL_REPORT.md`, `plan/v1/RELEASE_NOTES.md`, `plan/v1/LAUNCH.md`, `docs/decisions/0020-reproducible-visual-assets.md`, `tests/docs/test_readme.py` (+136/-79) |
| (this report) | `plan/v1/reports/21-finalization.md` only |

`README.md` and `docs/publishing.md` needed no change: the README recording
section already references the activated `demo-light.gif` and
`demo-dark.gif`, and the publishing status note already states the GitHub
release is a draft.

## Review findings and how each was corrected

1. **Artifact provenance.** Release notes artifact row and final report
   distribution row now state that the four verify-matrix jobs, the publish
   job and the mirror job download the exact Actions artifact by id and
   compare it with the build checksums; verify-published downloads the
   official PyPI files and compares them with the build checksums; the
   assets job downloads no distribution. The "every later job" wording is
   gone (confirmed against `.github/workflows/publish-pypi.yml`).
2. **Scope wording.** Final report deviations row and known-limits bullet
   now say P2 figures, broader comparisons, per-slice gates, sequential
   designs and signed evidence are not shipped in 1.0.0 and are not
   prohibited for 1.x; any later addition follows ADR 0015's additive,
   separately versioned rules.
3. **Executor history.** The final report now says the Fable-led Task 02
   and Task 09 sessions delegated parts of their early work to non-Fable
   workers; those drafts were rejected under V1-007 (the primary record),
   preserved with hashes, restored to baseline and reimplemented directly by
   Fable 5.1. No whole session is attributed to another model.
4. **Spend.** The final report cites `plan/v1/receipts/claude-usage.json`,
   a Codex read-only observation at 2026-10-07T10:38:02 UTC before this
   finalization: about USD 557.91478250 API-equivalent list-price usage
   (Fable 5.1 548.47390075, Sonnet 5 3.20635100, Opus 5 6.21186675, Haiku
   4.5 0.02266400), explicitly not an invoice or billed spend; actual billed
   cost UNKNOWN; Codex, manual and later Claude work excluded; later dated
   observations supersede it and no final cost is asserted. Zero observed
   sprint Jev requests; balance or credit change UNKNOWN, not inspected.
   The earlier pre-tag figure (USD 536.13327225) is kept as dated history.
5. **Launch schema claim.** The launch draft now says published JSON
   Schemas cover the lock, evidence-bundle, CLI-receipt and release-receipt
   formats and that the TOML contract is specified separately.
6. **Outcome claim.** The release notes replace "no item ended BLOCK,
   INCONCLUSIVE or ERROR except the demo" with the measured demo outcomes
   (bad BLOCK, replay exit 1; fixed PASS, replay exit 0; demo exit 0, in the
   clean container and the recording), the statement that the live Jev
   audit was not run and has no verdict, and that earlier failed runs,
   denials and negative probes stay recorded as history.
7. **Social preview.** Release notes, final report and Task 22 row now say
   the file is delivered and the GitHub-settings upload is a manual,
   non-blocking step, not a Task 22 blocker.
8. **Task 14 facts.** Release notes, final report and ADR 0020 record the
   accepted activation at `31c9916` with additive correction `a3397fe`:
   raw cast 21.517 s, GIFs 24.51 s, exits 0/0/1, 15 generated outputs
   (12 SVG, 2 GIF, 1 PNG), the committed paths and public receipt, the
   `env -i` scope qualification (package probes and capture only) and the
   relocatable `#!/bin/sh` launcher binding, with no re-recording or
   retiming. The media merge `0a0a228` (PR 48, 2026-10-07T10:37:34Z) and
   its ten hosted jobs (37607862358, 37607886554) are cited as supplied.
9. **Checkpoint and next steps.** The final report opens with the current
   checkpoint (PyPI live, media merged, GitHub release draft awaiting this
   gate and Task 22, bounded follow-up after actual publication) and splits
   next steps into release closure (Task 22) and the post-release 1.1
   roadmap; it predicts no CI or publication result.

**Docs test amendment (completion-only).** The `_implemented_outputs`
helper in `tests/docs/test_readme.py` read only literal output names from
`inventory.py`; the activated `demo` asset declares its outputs through
`demo.THEMES`, so the helper now resolves those two names from the literal
`LIGHT_OUTPUT`/`DARK_OUTPUT` constants in `demo.py` when a renderer-bound
block uses `demo.THEMES`. Planned assets without a renderer still
contribute nothing, so a README reference to an unimplemented asset still
fails; no negative check was weakened. All other README tests, including
the recording placement, dark-before-light, alt-text and `"demo.gif" not
in text` checks, are unchanged.

## Commands and exit codes

Separate, unwrapped commands from this worktree on the committed content.
The docs suite, hooks, receipts gate and docs gate were rerun after the
test helper amendment; the visual suite and regeneration check do not read
that file.

| Command | Result | Exit |
| --- | --- | --- |
| `uv run --frozen python tools/check_release.py receipts` | no output | 0 |
| `uv run --frozen pytest tests/docs` | 111 passed in 1.22 s | 0 |
| `uv run --frozen python tools/check_release.py docs` | no output | 0 |
| `uv run --frozen --group assets pytest tests/visual` | 481 passed in 1.85 s | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` | 18 image references checked; all 15 generated outputs (hero 4, how-it-works 4, architecture 4, demo 2, social 1) match regeneration; `5 asset(s) checked; 3 planned/not implemented; 0 error(s)` | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `git diff --check` | no output | 0 |

Before the helper amendment, the docs suite had exactly one failure:
`test_every_image_resolves_to_a_committed_implemented_asset` reported
`demo-dark.gif is not an implemented asset output` because the helper did
not read `demo.THEMES`; the GIFs were present and regenerating. The full
product suite was not run; no product source changed. The release notes
contain exactly three full 64-hex hashes (the wheel, the sdist and the
artifact digest), all present in the release receipt; recording hashes
remain abbreviated with links to their own reports.

## Deviations

None from the continuation packet. Judgement calls for review: the
`main` CI run 37603576993, PR 48 merge time and the two media-head runs are
cited exactly as supplied in the dispatch; the final report lists the
Task 22 closure as the single release-closure step and keeps two roadmap
steps, giving three next steps in total.

## Remaining limitations and gates

- Codex's independent review of `230462c` and this report; exact-head
  hosted CI on the integrated documentation; then Task 22 publishes the
  draft GitHub release. None of those outcomes is predicted here.
- A bounded follow-up after the release is actually published must record
  its final status in the final report.
- The live Jev audit and the P2 figures stay deferred to 1.1; the social
  preview upload stays manual and non-blocking.

## Spend

Unknown; not measured by the executor. No paid API, provider call,
download or Jev request occurred in this continuation. The committed
ledger observation predates this work and excludes it.
