# REVIEW 20 — Published distribution verification

Verdict: ACCEPT (publication scope only)
Reviewed source: `04c10d3fec60727310cf65acf6528f13264a26d4`, immutable tag `v1.0.0`.
Observation: 7 October 2026, approximately 15:44 IST.

## Evidence

- Human approved the `pypi` environment. [Release run 37603727302](https://github.com/ajaysurya1221/actseal/actions/runs/37603727302) completed SUCCESS: all nine jobs, including trusted publishing, pinned clean-container verification and draft mirroring.
- Codex downloaded the actual official PyPI wheel and sdist from the URLs in PyPI JSON, computed hashes and sizes, and compared their complete bytes with separately downloaded GitHub draft assets. Both pairs are identical and equal the tagged build receipt. The draft release receipt and SHA256SUMS also match the Actions copies exactly.
- Wheel: `actseal-1.0.0-py3-none-any.whl`, 101900 bytes, SHA256 `4497fef4878cb67f03845e13f91c8b8c4e7686361198d0ebc52a1764157ae3bf`.
- Sdist: `actseal-1.0.0.tar.gz`, 2054855 bytes, SHA256 `aa31ccf9f5cce30c40269dd5d9904ef61f147f9c4aaf21e3db288981b3278da6`.
- PyPI shows Production/Stable, Python >=3.12 and Apache-2.0. Both Publish attestations identify the repository, workflow, environment, tag, source and run; both subjects match their distribution. This is presence/identity/material inspection, not independent cryptographic verification.
- The actual successful pinned Linux-container job and its receipt record version1.0.0 installed outside the checkout, demo exit0 with BLOCK/PASS cases, fixed replay0 and bad replay1. Codex inspected that job and receipt; this review does not claim a second independently run container.
- Independent read-only reviewer `/root/v1_receipt_review` fetched run/tag/approval/artifact/PyPI/provenance metadata and independently hashed the downloaded files: ACCEPT, no publication defect found.

## Findings ordered by severity

No publication-scope defect found. GitHub release405628842 remains a draft with four uploaded assets. Publication success alone does not complete Tasks14/21/22.

## Required changes

Complete genuine public-PyPI recording, raw/media review, final documentation and receipt review; require exact-head green CI before postpublication main merges; then publish the receipt-backed GitHub notes. Never move the tag or rebuild/reupload released distributions.

## Follow-ups filed

Tasks14/21/22 track media, final report/launch draft and public closure. Social preview upload remains the human's manual step. Experimental Jev remains mocked-only; its unstarted live audit and P2 figures are deferred1.1 under V1-052.
