# REVIEW 09 — active v1 documentation inputs in sdist

Verdict: **ACCEPT, scoped CI/packaging change**.

Exact reviewed commit: c0a183c5fe95e1e7e21e193b64f0e31c2584de66, parent8acbf38add37235a306060cc81ea19d89ba61eed. Codex authored the permitted Task09 glue; a separate reviewer independently inspected and exercised it. Two files only: pyproject.toml and tests/release/test_check_release_distributions.py.

The source distribution now includes the exact plan/v1 files and report/review directories required by accepted Task08 documentation tests. An actual-sdist test compares each required member byte-for-byte against its source. Wheel contents and runtime dependencies remain unchanged. Targeted independent inspection found no credential paths or secret-format matches in the added tracked inputs.

Parent verification: UV_OFFLINE=1 uv run --frozen pytest tests/release/test_check_release_distributions.py —24 passed in2.13s, exit0; Ruff lint/format, strict mypy for the changed test, all pre-commit hooks and git diff --check passed. Independent verification: PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/release/test_check_release_distributions.py::test_sdist_contains_active_v1_documentation_inputs -q -p no:cacheprovider with UV_OFFLINE=1 —1 passed in0.59s, exit0.

No required revisions. Exact-head hosted checks, full release rehearsal, final metadata and supplied-artifact publication acceptance remain separate gates. This is not full Task09 acceptance or a publication receipt.
