# TASK 13R: Meet the label floor at actual GitHub README widths

Goal: correct the demonstrated rendered-size defect in REVIEW13-real-readme-sizing.
Owner: existing Claude13 Fable5.1/high session; estimate45minutes.

Context: original TASK13, V1-036/049/050/051, review13-real-readme-sizing,
current accepted hero/workflow sources, and report13-manual-unblock-completion.

Interface contract (frozen): desktop validation width838CSSpx; mobile254CSSpx.
Every label remains at least14rendered pixels. README's paired task uses mobile
variants below1280viewport pixels. Keep all names, light/dark variants, approved
copy, five-stage workflow, seven architecture groups, actual module map and
evidence limits. Keep the existing font/tool pins and generic diagram font stack.
Wrap or reflow instead of shrinking; dimensions may grow only where necessary.

Files to create/modify: docs/assets/src/actseal_assets/{hero,how_it_works,
architecture,inventory}.py; their three tests/visual/test_*.py files; narrow
related size assertions in tests/visual/test_pipeline.py/test_render_cli.py;
the three figures' generated SVG variants; relevant dimension/readability
paragraphs in docs/assets/src/README.md; your additive
plan/v1/reports/13-readability.md. This explicitly extends13's previous ownership.

Files NOT to touch: runtime product code, root README, docs/decisions, other
tests/renderers, validation algorithms or minimum font floor, dependencies,
tool/font files, social.png, historical reports, locks/bundles, planning state.
Preserve desktop hero and social bytes unless a concrete necessity is reported
before changing them. They already meet the measured desktop floor.

Acceptance criteria: all12SVG variants regenerate; geometry and labels pass at
838/254px; actual light/dark pixel previews at838,294 and254px are readable with
no clipping/overlap. Existing semantic and prerequisite negatives stay intact.
No source hash/registry/product change. Report any changed dimensions and bytes.

Tests to add: regressions measuring effective glyph/text sizes with the actual
display-width constants; keep strict module/edge/geometry and missing-resource
controls. Do not replace the real width model with an asserted pass.

Constraints: you are not alone; edit only owned paths, never revert another
lane. No merge, push, key/network/model call, download or source substitution.
Use already-approved cached tools/fonts. If ANY tool operation is denied, stop
that operation immediately; do not recover its sub-operations through narrower
commands, Read or git show. Return BLOCKED with the exact denial. No bypass.

Done when (run each command separately, preserve its real exit code):

```bash
uv run --frozen --group assets python docs/assets/src/render.py --check
uv run --frozen --group assets pytest tests/visual
uv run --frozen mypy --strict docs/assets/src tests/visual
uv run --frozen pytest -m "not integration and not packaging"
uv run --frozen pre-commit run --all-files
git diff --check
```

Report format: REPORT13R; DONE/PARTIAL/BLOCKED; files/commits; exact commands,
results/exit codes; deviations; actual temporary pixel paths/hashes; open issues;
spend. Preserve the earlier candidate/report. Codex reviews before ACCEPT.
