# REPORT PYPI-03 — first publication attempt

Status: **BLOCKED**

Date: 2026-10-06. Workflow commit `548c697f53c1584a45141a3b82060985d318424f`.
[Publication run](https://github.com/ajaysurya1221/actseal/actions/runs/37484412303).

## Changes (files + summary)

After the user reported registering the publisher, Codex created the GitHub
`pypi` environment with a custom deployment policy allowing only the `main`
branch. The environment had not previously existed. Its branch policy was
read back and confirmed. No credentials, product code, release assets, tag or
workflow file changed.

Codex dispatched `publish-pypi.yml` on main with `publish=true`. This report and
the corresponding review preserve the unsuccessful attempt.

## Tests (commands + results)

- `gh run view 37484412303 --repo ajaysurya1221/actseal --json status,conclusion,headSha,jobs,url`:
  completed **failure**, with `validate` successful and `publish` failed.
- The validation job passed release identity, release CI, exact artifact inventory,
  both pinned SHA-256 checks, strict Twine metadata checks and artifact retention.
  The publication job successfully downloaded that artifact.
- PyPI rejected the identity exchange with `invalid-publisher`: a valid token
  had no corresponding publisher with matching claims. The failure occurred
  before distribution upload. No publication, attestation or installation
  success is inferred from the successful validation job.
- Independent HTTPS observations at 15:08:32 UTC returned HTTP404 for both
  `https://pypi.org/pypi/actseal/json` and
  `https://pypi.org/pypi/actseal/0.1.0/json`.

The public workflow claims identify repository `ajaysurya1221/actseal`, owner
`ajaysurya1221`, workflow
`ajaysurya1221/actseal/.github/workflows/publish-pypi.yml@refs/heads/main`,
ref `refs/heads/main` and environment `pypi`. No token is copied into this report.

## Deviations from spec (with reason)

Publication and fresh PyPI-install verification could not complete because the
identity exchange failed. No API-token fallback, altered identity or automatic
retry was attempted. Original GitHub v0.1.0 publication remains intact.

## Open issues

The user must confirm/correct the pending publisher on **pypi.org**, using
project `actseal`, owner `ajaysurya1221`, repository `actseal`, workflow filename
`publish-pypi.yml` and environment `pypi`. The browser available to Codex is not
signed in, so the exact registration mismatch has not been established.
Do not assume the user made a typo; upstream matching remains another possibility.
After diagnosis, inspect PyPI state before a retry and independently verify the
published bytes and a fresh install/demo if upload succeeds.

## Spend

Incremental paid inference API spend: USD0. No model call or paid hosting added.
