# Actseal v2 — change log

## V2-001 — 13 November 2026 — roles and deadline

The human approved the 2.0 plan (`plan/v2/PLAN.md`) and then instructed Claude
Code directly: "you handle everything please. Let's try to finish this and
publish it in github by tomorrow."

Effect, for v2 only:

- Claude Code plans, builds, checks and prepares the release. The v1 split
  (Codex plans and reviews, Claude Code builds) is suspended for v2 by this
  instruction. No independent Codex review exists for v2 work unless the human
  asks for one; every record must say so and must not claim an ACCEPT.
- The executor is the Claude Code session the human is using (model
  `claude-fable-5-2`). The v1 pin to `claude-fable-5-1` applied to Codex
  dispatch and does not apply to this direct instruction.
- Target: the work is on GitHub by 14 November 2026. "Publish in github" is read
  as pushing the branch and opening the release pull request. A PyPI publish, a
  tag and any public post still need the human's explicit approval.

### V2-001a — same day — role assignment by the human

"You can use Fable 5.2 Medium (You) as the Orchestrator, Reviewer. Codex Astra 6
as the executor, co-planner."

- Claude Code (`claude-fable-5-2`) orchestrates and reviews. Codex (Astra 6)
  executes and co-plans. This replaces the role lines in V2-001.
- Two Claude subagent tasks were already running when this arrived (M3
  selector, M2 fingerprint). They finish; Claude Code reviews them like any
  other executor work. All later execution is dispatched to Codex.
- Review is by the orchestrator, not by an independent third party.

## V2-002 — 13 November 2026 — scope under the one-day target

Order of work: M1, M2, M3 and M4 in parallel, M5, M6. Each is cut rather than
weakened if it cannot pass its checks in time.

- The public comparison (M7, M8) needs model downloads, which need the human's
  permission, and one to three days of machine time. It ships after the code,
  not inside the one-day target, unless the spike shows otherwise.
- The separate 1.0.2 registry patch is prepared as its own change and is not
  published without approval.
- No statistical rule, test or gate is weakened to meet the date.

## V2-003 — 13 November 2026 — keep engine v1 and schema 2; calibration is a sidecar

Amends PLAN "Engine v2 without the replay tax" and the nine-file bundle.

- Lock schema 2, bundle schema 2 (seven files) and engine `actseal-choice-v1`
  are unchanged. Old evidence must replay to its stored verdict under 2.0; the
  archived Jev audit becomes a golden replay test. No separate 1.0.2 is needed.
- The implementation fingerprint keeps its name and rules but excludes a short
  explicit list of files that cannot change decision or replay semantics
  (version string, entry point, command line, report rendering). New files are
  hashed by default.
- Calibration evidence is a separate, hash-linked directory written before the
  verification lock exists: a selection plan (grid, rule, sizes, input hashes),
  the calibration records and the selection result. Replay recomputes the
  selection from those files. The verification lock then carries the selected
  threshold in an ordinary contract.

Reason: the same user-visible result with far less change to audited code, no
break for existing evidence, and it fits `docs/stability.md` ("additional
formats arrive only as a separately versioned, explicitly opt-in interface").
What is lost: the lock itself does not name the calibration directory; the
qualification receipt and report link the two by SHA-256.
