# Contributing to Actseal

Use Python 3.12 or 3.13 on macOS or Linux (Windows is unsupported) and
uv 0.12.5. Install the locked development environment:

```bash
uv sync --frozen --group dev
uv run --frozen pre-commit install
```

Before opening a change, run the same core checks as CI:

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy --strict src tests
uv run --frozen pytest -m "not integration and not packaging"
uv run --frozen pre-commit run --all-files
uv build --no-sources
uv run --frozen pytest -m packaging
```

The default tests need neither credentials nor a model download. Network and
model calls belong only in explicitly marked integration tests. Tests must use
independent expectations and cover failure paths; do not regenerate fixtures to
hide a changed result. Documentation examples are executed by `tests/docs`;
keep them runnable.

The public surface is enumerated in the [stability manifest](docs/stability.md)
and may change only as the [versioning policy](docs/versioning.md) allows.
Record shapes and boundaries are specified in [CONTRACTS](plan/CONTRACTS.md).
Propose a documented contract amendment before changing them. State the
problem, the resulting behavior, and the checks you ran in your pull request.
Use small conventional commits such as `fix: reject duplicate evidence records`.

Never submit `.env`, credentials, private datasets, or raw provider records that
you do not have permission to share. Add a license/source entry for new
dependencies or reused code; the runtime core stays dependency-free. Preserve
notices. Report security defects through
[the private reporting channel](SECURITY.md).

During the v0.1.0 sprint, Claude Code implemented product code and tests and
Codex reviewed and gated each task; those records remain under `plan/`. The
v1.0.0 release follows the same ownership under the state in
[plan/v1/STATE.md](plan/v1/STATE.md); see [AGENTS](AGENTS.md) for lane
ownership and release rules. Contributions are licensed under the repository's
Apache-2.0 license.
