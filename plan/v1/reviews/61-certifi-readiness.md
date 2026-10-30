# Task 61 — CA-bundle dependency acceptance

Date: 30 October 2026. Reviewer: Codex.

## VERDICT

**ACCEPT** the Certifi-only lock correction based on
`18471d69e1bbdabb40a5c11496462e8c9e350724`, with `uv.lock` SHA256
`a3bffc314d8fb3a89176d55e93f2889960a679d35c6d560daaec49f032107cfb`.
The integration owner independently reviewed the implementer's exact candidate,
re-downloaded its artifacts and accepted the bounded change. Merge still requires
green exact-head hosted checks. The PR is the later hosted-check/merge receipt;
this record does not claim future CI success or approve a release.

## FINDINGS and scope

No blocking finding remains. Only Certifi 2026.7.22 changes to 2026.10.19;
all 61 package identities, dependency edges, registries and resolution markers
remain unchanged. Product source/tests, direct/native pins, public contracts,
checkpoint hashes and frozen evidence are untouched. Task61 and V1-061 recorded
this scope before the lock change.

The [Certifi advisory](https://github.com/advisories/GHSA-6q48-6c7w-9gw2)
recommends 2026.10.19 or later, restoring unaffected roots after 2026.10.18
removed all emSign roots. The selected minimum recommended patch is non-yanked.
Fresh independent wheel/sdist downloads match the lock and
[exact PyPI metadata](https://pypi.org/pypi/certifi/2026.10.19/json) hashes and
sizes. Wheel metadata and its license file retain MPL-2.0; Python >=3.7 and
no added dependencies fit the supported Python 3.12/3.13 matrix. Dated
exact-version PyPI/GitHub checks report no matching advisory; this is not
proof that no unknown vulnerability exists.

Certifi is reached by the optional Hub/HTTPX artifact-download stack. The
inspected HTTPX default configuration loads Certifi when no explicit trust
configuration replaces it. The dependency-free core/offline replay do not
need this package. A compromised key and on-path attacker are advisory
prerequisites; no such Actseal exploit was reproduced. The corrected bundle
loads into a local SSL context, with 120 CA certificates, and omits the affected
emSign ECC Root CA - G3 label. The old/new wheel's Python source differs only
in its version assignment. No live TLS handshake or native inference was run.

## Validation

Local candidate commands passed at the unchanged lock hash:

- Frozen dev/assets setup and `uv lock --check`.
- Repository hooks: Ruff lint/format and strict Mypy.
- Ordinary suite: 4,216 passed, 1 skipped, 31 deselected. The skip concerns
  the approved Linux recording-renderer pin; integration is a separate selection.
- Wheel/sdist build and 25 packaging tests (4,223 deselected).
- Fixture demo: bad BLOCK, fixed PASS, both fresh replays match.
- Receipt and documentation gates; `git diff --check`.

The independent reviewer inspected these implementer-run logs without claiming
a second test execution. Local independent-review SHA256:
`70b04bc0f836366d4dbfd2dcaa78215e75773dfa25fe39633c5e029be23ffc47`. Local command-receipt SHA256:
`e75c0d19f2fb53c75558ef3332fc028588df1eaf391b4137e80745f7ba8198da`. These durable records are retained with the dated readiness
materials outside the checkout. Required hosted platform, assets, dependency,
CodeQL and secret checks remain separate gates.

## Remaining advisory and limitations

Setuptools alert15 (GHSA-xmj3-9gf7-h52w) remains visible and is **non-actionable
for the observed configured build path**. Windows exclusion alone would be
wrong: the [maintainer's fix](https://github.com/pypa/setuptools/commit/6d07b8d17890dda58d944ac51e58f54af92d52af)
explicitly also covers POSIX absolute paths. The affected route is deprecated
`setup_requires` / `Wheel.install_as_egg` outside a PEP517 frontend. Actseal
uses `hatchling.build` and `uv build --no-sources`, with no such legacy
invocation in the inspected source, tests, tools, hooks or workflows. The
Setuptools pin remains unchanged; re-evaluate if a legacy setup flow is added.
This does not certify arbitrary consumer installation workflows.

Native startup/inference and live TLS compatibility remain untested. The CA
trust correction does not change checkpoint identity or numerical/normalization
code, so no provider-identity amendment or model run is required by this bounded
review. Historical native receipts are not new execution evidence. No alert
dismissal, protection change, release, tag or distribution replacement occurred.
