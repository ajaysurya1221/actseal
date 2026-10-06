# Security policy

## Reporting and support

Report a vulnerability privately through
[GitHub's advisory form](https://github.com/ajaysurya1221/actseal/security/advisories/new).
Include the affected commit/version, a minimal reproduction and the observed
impact. Do not include credentials or private evaluation data. During release preparation, fixes land on current main. The v0.1.x release line
will be supported after publication.

## System and trust boundary

Actseal is a local Python library and CLI for frozen categorical decision
policies, finite-sample risk/coverage assessment, deterministic provider-fault
tests and offline replay. The core uses the standard library. Optional pinned
Laya CPU inference runs in a child process; Actseal provides no hosted service,
OS sandbox or application-action executor.

Contracts, labels, responses and bundle files are untrusted for parsing and
resource use. Replay must not execute bundled code, restore environments,
import live providers or contact a network. The installed implementation,
interpreter and host are trusted. The integrating application must protect its
expected policy identity and honor the evaluated policy's dispositions.

A separately trusted expected lock digest anchors the **locked identity only**.
It does not authenticate provider responses, authorship, execution, labels or
sampling history. A digest kept beside an untrusted bundle is not an independent
trust channel. Even with an unchanged trusted lock, an author can replace
responses and recompute internally consistent outcomes, verdicts and hashes.
That coherent rewrite is outside v1's authenticity assurance; no signature,
remote attestation or tamperproof attempt ledger is provided.

## Required invariants

- Strict bounded parsing rejects unsupported schemas, duplicate keys, invalid
  numeric values, incomplete inventories, symlinks and unexpected bundle files.
- Every scheduled case has exactly one terminal record. Abstentions, denials,
  escalations and nonfatal failures remain in a valid run's coverage denominator.
  Invalid evidence takes ERROR precedence; its zero verdict counts do not erase
  retained diagnostic records.
- Assessment and replay reconstruct requests, normalize captures, apply policy,
  validate canonical fault evidence and recompute bounds. Stored PASS or merely
  matching checksums are insufficient.
- Policy order is explicit: any fallback flag ESCALATEs first; otherwise an
  unknown-choice failure DENYs, other provider/identity failures ESCALATE,
  disallowed choices DENY, and selected probability below threshold ABSTAINs.
  Only the remaining allowed choice ACTs. v1 performs no automatic fallback.
- Native startup is bounded at 120 seconds; normal evidence-collection requests
  use exactly 30.0 seconds. Timeout/death/unusable IPC invalidates the worker;
  no silent restart or replacement sample is permitted. Regular Laya
  timeout/unavailable invalidates the statistical experiment as ERROR after
  integrity validation. Canonical injected faults are separate.
- Recorded error/identity metadata excludes credentials, authentication headers
  and arbitrary exception text. Raw case text and provider bodies may still
  contain caller-supplied private data and must be reviewed before sharing.

These invariants define reportable behavior. Task acceptance supports tested
boundaries; it is not a claim of comprehensive security assurance.

## Reportable defects and explicit limits

Report reachable acceptance of **inconsistent** evidence as valid: for example,
stored outcomes that disagree with reconstructed policy, incomplete case/fault
inventories, invalid seals or a supplied expected-lock mismatch. Incorrect
statistical verdicts, replay code execution, escaped bundle paths, unbounded
parsing, error-message leaks and worker-lifecycle defects are also reportable.
Severity depends on demonstrated impact and prerequisites. Dependencies, local
inputs and tests have no blanket exemption from review.

Distinguish those validation defects from an internally coherent same-lock
response rewrite, false labels or dishonest sampling history. Replay cannot
establish their authenticity. A surrounding application may also ignore its
returned decisions. A parser or validation defect within these same paths
remains reportable; the limited authenticity claim is not an excuse to accept
inconsistent evidence.

Bundle publication atomically refuses an existing destination using supported
macOS/Linux system APIs. Unsupported native/filesystem support fails explicitly.
This is not a power-loss durability guarantee or defense against a hostile
process controlling ancestor directories or modifying files during/after checks.

The pinned Laya checkpoint's calibration is unvalidated for user workloads.
Authored demonstrations provide no population assurance. Statistical bounds
require independent case outcomes under a fixed policy and operating regime
over one prespecified attempt; they do not bound uptime, completion probability
or distribution shift. Do not discard ERROR attempts and retry until PASS.

See [trust boundaries](docs/threat-model.md),
[statistical assumptions](docs/statistical-contract.md),
[provider limits](docs/providers.md) and [exact contracts](plan/CONTRACTS.md).
