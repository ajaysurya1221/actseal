# REPORT09 CI integration glue

Status: DONE for this bounded packaging/checker correction; full Task09 remains incomplete. Author: Codex under the approved Task09 CI/packaging ownership, with independent review required before acceptance.

## Changes

- tools/check_release.py now requires all four actual Task12 workflow SVG variants (desktop/mobile, light/dark), matching f712daef51ee005c1b34c9744dbe1d99cf499c33. Required renderer names and the post-PyPI demo exception remain unchanged. Hero/architecture final declarations await their tasks; no hypothetical output is counted as present.
- Release fixtures use the same names. Four negative tests independently remove each workflow variant and require the release gate to reject its absence.
- The sdist allowlist now includes tools/check_release.py and .github/workflows/publish-pypi.yml, both required by the already-included release tests. A packaging test opens the actual built or supplied sdist, verifies those regular-file members and its release_support.py, and compares their bytes against the reviewed checkout. It does not extract or execute an archive member, and does not rebuild when supplied artifacts are configured.

## Checks

- uv run --frozen pytest tests/release:544 passed16.32s, including the new actual-sdist test.
- uv run --frozen python tools/check_release.py workflow:exit0.
- Initial hooks: PT007 required a list rather than tuple in the new parametrization; no test failed. Corrected only that container syntax.
- Final uv run --frozen pre-commit run --all-files:allhooks passed.
- uv run --frozen mypy --strict tools/check_release.py:passed.
- Final targeted four omission tests:4passed0.19s;124deselected.
- git diff --check:passed.

No product implementation, provider, statistical rule, model call, authoring download or actual rendering changed. No permission control was changed. The ordinary-CI pinned authoring setup is still pending the existing scoped download approval and will not be pushed/executed as a workaround. Final README/docs gate integration, additional task-dependent sdist inputs, final assets and hosted publication rehearsal remain outstanding.

Spend: no paid API/Jev calls. No publication or merge performed by this receipt.
