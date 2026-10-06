# Actseal planning and contract change log

## 2026-10-06 — initial authorization and materialization

- User selected Decision Contract and focused two-day scope after reconciliation.
- Codex selected public name Actseal under the user's naming delegation. Exact
  GitHub-name search and PyPI lookup found no match; no name reservation claimed.
- User explicitly requested implementation in Default mode. The former plan-only
  write restriction and earlier approval wait are superseded by that request.
- Mandatory v1 is categorical risk/coverage, fixture+Laya, faults and data-only
  replay. Jev and a reusable Marketplace Action are deferred, not silently dropped.
- Planning contracts explicitly include verification cases in the lock so assess
  can independently recover gold labels; hashes alone cannot supply labels.
- Pure replay and identity checks are separated from provider imports. Full native
  token-layout preflight is required because upstream can truncate silently.
- Fixture fault injection uses a complete ordered six-scenario inventory; no
  randomness is needed for coverage of this fixed v1 fault set. This replaces
  research's random scheduling without weakening the required fault scenarios.

## 2026-10-06 — contract review before T00 acceptance

Independent review found five specification gaps. Approved amendments: assessment
must reconstruct requests and normalize raw captures before counting; fault
captures are canonical and scenario-bound; low-confidence chooses an allowed
label; generic JSON parsing is bounded at 128 MiB with 1 MiB JSONL rows and a
32 MiB lock limit; ADR fallback precedence now matches the contract and Jev stays
deferred. Added fault_capture signature and exact manifest keys. T00 was already
running against its original packet: its acceptance requires the revised parsing
limit through a follow-up. T10/T20/T30/T40 receive revised contracts at dispatch.

Laya capture now explicitly preserves the full native response envelope instead
of extracting its answer in the adapter. Pure normalization can therefore replay
question-ID and native truncation/option-collapse checks. The exact usage schema
was verified against Laya0.3.28 source and a fresh offline smoke. The canonical
fault generator wraps Laya answers in a synthetic zero-usage envelope. No provider
interface or product scope changes. Added explicit record-local normalized mass,
provider-domain, overflow and verdict-count invariants from the T00 static review.

## 2026-10-06 — T00 dependency and wire review

Initial Linux PyPI Torch resolution pulled proprietary NVIDIA packages. This is
a release blocker under the OSS constraint. Verified official Linux x86_64 CPU
wheels replace that resolution: torch==2.14.1+cpu in published optional dependency
metadata and a Linux-only explicit CPU index in uv. macOS retains tested PyPI
torch==2.14.1. Corrected resolution and runtime checks are still required; metadata
availability alone does not establish Linux inference compatibility.

Approved the executor's explicit wire layout before freezing: artifact_hashes and
runtime are JSON objects; probabilities retain ordered pair arrays; other tuples
are arrays. Supporting constants, a read-only question.labels property and the
PEP695 Outcome alias are accepted conveniences, not added product scope. All
reported schema/size/license findings remain mandatory fixes before T00 ACCEPT.
