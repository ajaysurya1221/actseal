# REVIEW PYPI-03 — publication attempt

Verdict: **REVISE** for completion of PyPI publication; no workflow-code defect
has been established.

Date: 2026-10-06. Reviewed workflow commit
`548c697f53c1584a45141a3b82060985d318424f` and
[run 37484412303](https://github.com/ajaysurya1221/actseal/actions/runs/37484412303).

## Findings ordered by severity

1. **Blocking:** PyPI returned `invalid-publisher` during identity exchange.
   Validation succeeded, but publishing failed before upload. The project and
   version APIs still returned404 after completion. This is an external
   publication blocker, not evidence of incorrect distribution bytes.
2. The exact cause is unconfirmed. The accessible browser is not signed in to
   PyPI, so the registered pending-publisher fields could not be inspected.

Root independently read the hosted job state, filtered failure diagnostics and
public PyPI API responses. A separate read-only reviewer reproduced the failure
and the404 project/version/provenance responses. No artifact, installation or
cryptographic-attestation verification is claimed for PyPI.

## Required changes

Reconcile the registered publisher with the workflow's public identity claims.
Inspect PyPI state before retrying, then verify file hashes/sizes and a fresh
installation/demo after successful upload. Do not bypass OIDC or replace the
reviewed GitHub assets to address a publisher-configuration failure.

## Follow-ups filed

The question about the pending-publisher row is with the user. REPORT PYPI-03
preserves this failed attempt. Append a new receipt for any subsequent attempt;
retain this review and the original validation-only reviews unchanged.
