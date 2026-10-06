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
was verified against Laya 0.3.28 source and a fresh offline smoke. The canonical
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

## 2026-10-06 — fixed v1 collection deadlines

Removed the proposed verify --timeout-seconds flag before T50 implementation.
Timeouts alter failures and later worker availability, so an unsealed override
would change the evaluated system under an identical lock. v1 evidence runners
always use 30.0s per request and 120s startup, bound by the source fingerprint.
Low-level provider timeout arguments remain for direct use/tests. Configurable
deadlines move to a future versioned execution schema. No public record changes.

## 2026-10-06 — persistent worker loss and binomial assumptions

ADR 0009 corrects a cross-case dependence gap discovered before parallel dispatch.
A regular Laya timeout/unavailable makes statistical assessment infrastructure
ERROR after complete integrity checks; diagnostic records remain complete. The
canonical synthetic fault campaign is unaffected. Permanent worker-loss paths
report unavailable, no silent restart. Population interpretation requires fixed
independent case behavior and remains unconditional over one prespecified attempt,
never persistent-process uptime or completion probability. No public signatures
changed; T20/T30 specs amended before dispatch, T40/T50 inherit the contract.
This is a correctness correction to research-derived failure semantics, not scope
expansion. The human's standing approval covers routine execution; original
material scope, license and budget escalation conditions remain.

## 2026-10-06 — T10 bounded I/O and shared helper review

ADR0010 accepts four small shared helpers before downstream use: read_input_text,
case_digest, lock_digest and parse_lock. Exact signatures/semantics are frozen in
CONTRACTS section 3. The existing reader/lock limits are clarified at allocation
and canonical wire boundaries, including terminal LF. Standalone validation must
check cross-split IDs already visible in inventories. No new dependency, feature
or shared record change. T10-01 is REVISE for three independently reproduced
defects; the earlier 738 passing tests do not establish these missing invariants.

## 2026-10-06 — T30 provider review and downstream packet consistency

ADR0011 approves the package marker and request/timeout helpers and explicitly
caps aggregate fixture input at128MiB. T30-01 requires deadline, malformed-IPC,
Linux CPU-test and fixture-bound repairs despite235 passing unit/5 native Mac
tests. T40/T50 packet wording now explicitly matches ADR0009 worker-loss ERROR,
complete diagnostics and synthetic-fault exclusion, and the ADR0010 helpers.
This prevents stale generic failure wording from overriding the frozen contract.

## 2026-10-06 — acceptance packet clarification

T60 now explicitly distinguishes regular Laya worker-loss diagnostic ERROR from
nonfatal denominator failures, matching ADR0009. A nonblocking T30 test-quality
follow-up requires an actually injected policy violation while retaining all six
campaign results; the current straight-line implementation already continues.
This corrects the advertised test coverage without changing the product contract.

## 2026-10-06 — JSONL terminators and aggregate bundle accounting

Clarified size conventions before T40 dispatch: row payload bytes exclude the LF
separator, count any CR, and match the accepted T10/T30 readers. Whole bundle
size includes all seven files and their terminators. No record/signature change;
the clarification prevents downstream off-by-one or manifest-omission errors.

## 2026-10-06 — T40 pre-dispatch diagnostic and publication clarification

ADR0012 freezes unknown-lock ERROR metadata and requires exclusive native rename
to honor the existing no-overwrite promise, including a target created immediately
before publication. Stdlib ctypes only; fail explicitly on unsupported systems.
No record/signature or scope expansion. T40/CONTRACTS updated before dispatch.
ADR0005 also clarifies that a trusted lock hash cannot authenticate same-lock
rewritten responses or provider execution.

## 2026-10-06 — prespecified demonstration

ADR0013 fixes the T50 synthetic data rules before implementation: two128-case
runs, same threshold/limits, zero versus32 authored wrong accepted decisions.
Planning bounds establish expected behavior only; actual receipts must come from
the installed product. No population, training or paired-model comparison claim.
