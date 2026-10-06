# Security policy

## Reporting and support

Report a vulnerability privately through
[GitHub's advisory form](https://github.com/ajaysurya1221/actseal/security/advisories/new).
Include the affected commit/version, a minimal reproduction and the observed
impact. Do not include credentials or private evaluation data. Development main
is currently the only supported line; no release has yet passed acceptance.

## System and scope

Actseal is a local Python library and CLI for frozen categorical decision
policies, finite-sample risk/coverage assessment, deterministic provider-fault
tests, and data-only offline replay. It provides no network service, multi-tenant
hosting, OS isolation or application execution capability. The core is stdlib
Python; local Laya inference is optional and runs in a child process.

## Trust boundaries

The caller supplies a contract, labels and provider data. All are untrusted for
parsing and resource use. Evidence bundles are untrusted files; replay must not
import or execute bundled content, restore environments, import live providers,
or contact a network. The installed Actseal implementation, interpreter and host
are trusted. An expected lock hash must come from a separately trusted channel
when provenance matters; hashes inside a bundle alone establish consistency.

The caller is responsible for label truth, the declared sampling process, and
using the verified policy in its application. A model response is data and never
authorizes execution by itself. Raw captured bodies and case text may be private;
the caller must review them before sharing a bundle.

## Required invariants

- Strict bounded parsing rejects unsupported schemas, duplicate keys, nonfinite
  values, incomplete inventories, symlinks and unexpected bundle files.
- Every scheduled case has exactly one terminal record. Failed or abstained
  cases stay in the coverage denominator. Corruption takes ERROR precedence.
- Assessment and replay reconstruct requests, normalize captured responses,
  evaluate policy and recompute bounds; neither trusts an archived PASS.
- Unknown/disallowed choices cannot ACT. Provider or identity failures ESCALATE.
  Low-confidence choices ABSTAIN. v1 performs no cloud or autonomous fallback.
- Provider workers respect deadlines and are closed. Credentials, headers and
  arbitrary exception text are excluded from recorded errors and identities.

These are requirements to verify, not evidence that implementation is correct.

## Reportable findings and limits

Report a reachable violation of the invariants above: forged evidence accepted
as valid, incorrect statistical verdicts, code execution during replay, escaped
bundle paths, unbounded parsing, leaked credentials, or provider lifecycle bugs.
Severity depends on the demonstrated impact and required caller privileges.
There are no blanket exclusions for dependencies, local inputs or tests.

Self-authored evidence with consistently rewritten labels cannot prove those
labels are true. An attacker who replaces both installed code and its trusted
lock hash controls the trust base. A surrounding application can ignore Actseal's
returned decision. Those are stated assurance boundaries, not findings against
claims of universal containment. A parser or verification defect within those
same paths remains reportable.

The pinned Laya checkpoint has unvalidated calibration. Its confidence is not a
security guarantee. Authored demos supply no population assurance. Statistical
bounds require the prespecified sampling assumptions and do not establish
distribution-shift robustness. See [contracts](plan/CONTRACTS.md) and
[provider limitations](docs/providers.md).
