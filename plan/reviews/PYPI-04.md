# REVIEW PYPI-04 — completed PyPI publication

Verdict: **ACCEPT**

Date: 2026-10-06. Reviewed workflow commit
`f8d602ecef8af5def808954e229d7cb5fbb7fb7d`;
[run37485461528](https://github.com/ajaysurya1221/actseal/actions/runs/37485461528).
Release source remains `83fd04a5d340000aed6518109dce666dc208ad70`.

## Findings ordered by severity

No blocking findings. Both hosted jobs passed using the unchanged reviewed
workflow; public PyPI files now exist and independently recomputed sizes/hashes
match the two accepted GitHub release artifacts. A separate read-only reviewer
reproduced the artifact hashes and inspected matching published provenance.

Root independently ran the PyPI quickstart in a fresh tool environment outside
the checkout, verified only the core package was installed, checked the source
fingerprint, replayed both bundles offline with externally recorded expected
lock hashes, and reproduced the complete24-file evidence digest. The expected
badBLOCK/fixedPASS and their replay exits1/0 were retained honestly.

The existing full four-job CI at the publishing workflow commit passed. Product
source, tests and released distributions were unchanged, so no new product
test suite was added or gratuitously repeated locally. Attestation contents
were inspected; independent cryptographic attestation verification is not claimed.
See REPORT PYPI-04 for exact receipts and measurement limits.

## Required changes

None for this publication. Keep the original release bytes and failed-attempt
receipts unchanged. Do not dispatch another upload for v0.1.0.

## Follow-ups filed

Future releases must update the workflow's complete reviewed pin set before
publication. Native Linux CPU-index guidance remains unchanged. Current docs
use the verified PyPI command; the historical artifacts retain their valid
GitHub command. Public launch messages remain drafts.
