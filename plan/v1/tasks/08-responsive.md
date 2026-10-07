# TASK 08R: Select readable README variants at real GitHub widths

Goal: pair the visual-size correction with the README's actual responsive choice.
Owner: a new terminal Claude Code Fable5.1/high session; estimate20minutes.
Base: retained candidate5e7931a1ec8b0197d87ddc1e01a0835e011b470f in the clean
actseal-v1-docs worktree. Create branchclaude/v1-08-responsive from that base.

Context: original TASK08, V1-049/050/051, and review13-real-readme-sizing.
Do not resume either cancelled provider-removal task; Jev remains in scope.

Interface contract (frozen): preserve exact README opening order, copy, three
quickstart commands, alt text, absolute links and dark/light behavior. Choose
the existing vertical variants for viewport widths below1280px and desktop
variants at1280px and above. The visual lane validates actual rendered labels
at838px desktop and254px mobile; no new image paths or application behavior.

Files to create/modify: README.md; tests/docs/test_readme.py; dated addendum in
docs/decisions/0020-reproducible-visual-assets.md; your own
plan/v1/reports/08-responsive.md. No other source, tests, assets, old reports,
schema, metadata, lockfile, .env/example or planning-state edits.

Acceptance criteria: all three picture blocks preserve dark-before-light source
selection and use the correct breakpoint. Intermediate360/800/1200 windows
select mobile;1280/1366 select desktop. Old880/360 assumptions are explicitly
historical in the ADR; record the measured image widths without claiming a
final browser test on unmerged output. No public release/live-audit claim.

Tests to add: meaningful responsive source-order/breakpoint regressions in the
existing README suite; preserve missing-asset checks. The clean base lacks final
architecture images, so report that existing failure until integration.

Constraints: you are not alone; edit only owned paths, do not revert another
lane. No network/provider/key access, model/account/billing substitution, merge,
push, download or browser interaction. If ANY tool operation is denied, stop
that operation; do not recover its sub-operations with another tool/command.
Return BLOCKED with the denial; do not bypass it.

Done when (separate exact commands, honest exit codes):

```bash
uv run --frozen pytest tests/docs/test_readme.py
uv run --frozen python tools/check_release.py docs
uv run --frozen pre-commit run --all-files
git diff --check
```

Report format: REPORT08R; DONE/PARTIAL/BLOCKED; files/commits; exact tests and
exit codes; deviations; open issues; spend. Do not call missing-image failures
passes or exclusions. Full acceptance follows independent integrated review.
