# Task 60 — dependency readiness acceptance

Date: 30 October 2026. Reviewer: Codex.

## VERDICT

**ACCEPT** the scoped dependency-lock candidate based on
`ad62ec8ff33f858e1759149389f6700c03de6022`, with `uv.lock` SHA256
`0f908ce4d6f2a8a0ccea3b0f8c9136054a46bd9d61a0a445c6e7be6c20f38a77`.
This acceptance covers the lock and the task, change-log and review records.
Merge remains conditional on green hosted checks for the exact PR head.
The PR is the eventual hosted-check and merge receipt; this record does not
predict a future CI result. This is not release approval.

## FINDINGS

No surviving actionable finding remains in this candidate. Independent review
rejected the initial Virtualenv 21.14.10 proposal because
[GHSA-cx6f-vjhg-g3cc](https://github.com/advisories/GHSA-cx6f-vjhg-g3cc)
also affects it. The corrected 21.14.13 pin incorporates the maintainer's
[security fix](https://github.com/pypa/virtualenv/releases/tag/21.14.13).

The lock changes only Filelock 4.0.12 to 4.2.1 and Virtualenv 21.14.5 to
21.14.13. The 61 package records retain their identities, dependency edges,
registries and resolution markers. Direct requirements, optional native pins,
product source, tests, frozen interfaces, assets and historical evidence are
unchanged. The core still declares no runtime dependencies. Filelock is also
in the optional native graph, so the whole change is not development-only.

## Evidence and validation

Independent review compared the four corrected wheel/sdist artifacts with the
lock and exact-version PyPI metadata: URLs, sizes and SHA256 values match;
none is yanked. Both wheels declare MIT and contain MIT license grants.
[Filelock 4.2.1](https://pypi.org/pypi/filelock/4.2.1/json) requires Python
>=3.11 and adds no dependencies; [Virtualenv 21.14.13](https://pypi.org/pypi/virtualenv/21.14.13/json)
requires Python >=3.9 and its unchanged requirements fit the locked graph.
Both fit the project's Python 3.12/3.13 support matrix. No incompatible
license or newly introduced package was found in the two-record change.

The independent review checked the 14 imported advisory ranges and the
additional advisory above against the corrected pins. Its dated exact-version
GitHub Advisory Database queries returned no matching advisory for either pin.
Affected versions were present before this change; a reachable Actseal exploit
was not demonstrated. Database coverage does not establish absence of unknown
vulnerabilities. The Windows-only advisory is outside the supported macOS/Linux
contract, without exempting other dependency paths from review.

The final local execution logs were inspected, rather than treated as new
independent reruns:

- `uv sync --frozen --group dev --group assets` and `uv lock --check`: exit 0.
- Repository hooks: Ruff lint, formatting and strict Mypy passed.
- Ordinary tests: 4,216 passed, 1 skipped, 31 deselected. The skip is the
  macOS test of the approved Linux recording-renderer pin; integration and
  packaging selections are separate.
- `uv build --no-sources`: wheel and source distribution built successfully.
- Packaging selection: 25 passed, 4,223 deselected.
- Fixture demo and replay: expected bad BLOCK and fixed PASS, both replays match.
- `tools/check_release.py receipts`: exit 0; `git diff --check`: exit 0.

The local independent-review record has SHA256 `f4393244f41018f26b9ee7e91971f56f8fbcacbe23c474a06c19b43fdd2d90cf`;
the local execution receipt has SHA256 `b2be4690acb21c88417761a5a9521d644175d38ae5d4f28c68f2f92bc46d81f6`.
These records are retained in the dated readiness evidence outside this checkout.
Hosted Ubuntu/macOS Python 3.12/3.13 CI, assets, dependency review, CodeQL and
full-history secret scanning remain the exact-head merge gates.

## NOTES / limits

Native startup and inference compatibility for this exact transitive graph is
**untested**. The dependency gate in `docs/dependencies.md` requires a new
native smoke for changes that can affect predictions or normalization. The
review located this change in tooling and cache/file synchronization; model
artifacts, numerical/tokenizer/normalizer pins, provider source and frozen
execution settings are unchanged. No concrete prediction or normalization
change was found that requires a provider-identity amendment. Historical native
receipts are not reused as current evidence. The user prohibited model calls;
the manual native workflow is not dispatched.

No source-system alert dismissal, release, tag movement or distribution
replacement forms part of this task. The primary checkout's unrelated work
is untouched. No model CLI, paid inference or external security scan was run.
