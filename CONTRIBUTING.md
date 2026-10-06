# Contributing to Actseal

Use Python 3.12 or 3.13 and uv 0.12.5. Install the locked development environment:

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
hide a changed result.

Public records and boundaries are specified in [CONTRACTS](plan/CONTRACTS.md).
Propose a documented contract amendment before changing them. State the problem,
the resulting behavior, and the checks you ran in your pull request. Use small
conventional commits such as `fix: reject duplicate evidence records`.

Never submit `.env`, credentials, private datasets, or raw provider records that
you do not have permission to share. Add a license/source entry for new
dependencies or reused code. Preserve notices. Report security defects through
[the private reporting channel](SECURITY.md).

For the initial sprint, Claude Code implements product code and tests; Codex
reviews and gates each task. See [AGENTS](AGENTS.md) for lane ownership and
[STATE](plan/STATE.md) for accepted commits. Contributions are licensed under
the repository's Apache-2.0 license.
