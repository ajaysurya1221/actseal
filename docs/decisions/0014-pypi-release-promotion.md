# ADR0014: Promote reviewed release bytes to PyPI

Date:2026-10-06. Status:accepted for workflow setup; no PyPI upload performed.

The user requested a PyPI YAML workflow after v0.1.0 shipped on GitHub. This adds
optional distribution automation; the original sprint's PyPI exclusion remains
an accurate historical scope statement. Product interfaces and released files
remain unchanged.

Use a manual main-only workflow, validation-only by default. Pin v0.1.0's already
reviewed tag/CI/artifact identities. Rebuilding current main would produce a
different source archive containing post-release documentation. Promote exactly
the reviewed files instead. Future releases require a reviewed pin update.

Separate the read-only validation job from the environment-bound OIDC publication
job. Grant `id-token: write` only to the publisher; do not provision an API token.
No automatic release-event upload or silent skip of existing distributions.

Additional CI tooling, independently checked6October2026: Twine7.0.0 (Apache-2.0),
upload-artifact7.0.1 and download-artifact8.0.1 (MIT), PyPA publishing action1.14.2
(BSD-3-Clause). All new actions use verified full commit hashes. Twine runs through
uvx as publishing-only tooling; runtime dependencies and uv.lock do not change.
The action's bundled transitive tooling is its upstream responsibility; no claim
of a newly audited complete third-party dependency graph is made.

Primary references: [PyPI setup](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/),
[job-scoped OIDC](https://docs.pypi.org/trusted-publishers/using-a-publisher/),
[PyPA action](https://github.com/pypa/gh-action-pypi-publish/tree/dc37677b2e1c63e2034f94d8a5b11f265b73ba33),
[Twine metadata](https://pypi.org/pypi/twine/7.0.0/json).
