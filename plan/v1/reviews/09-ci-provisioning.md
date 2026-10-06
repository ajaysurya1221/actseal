# REVIEW 09 ordinary-CI provisioning preparation

Verdict: ACCEPT for local CI/packaging glue only. Full Task09 remains PARTIAL.

Exact reviewed commit: `bdedc1e428fb31983fac6e057602220f1b9ddc35`, base `1b5207664e3214ca43ae31765381e2ab70b12cdc`, local branch `codex/v1-09-ci-provisioning-preparation` in the managed release worktree. Codex authored these four files under Task09's explicit CI/packaging ownership; an independent read-only reviewer accepted the exact commit.

The ordinary assets job now declares the same pinned JetBrains Mono/resvg setup commands as publication CI, after mocked visual tests and before regeneration. Static YAML checks require both exact commands, ordering, immutable action pins, uv0.12.5 and unconditional failure handling. The sdist explicitly includes ci.yml, with a byte-comparison test, because its release tests now read that file. No product implementation, publication workflow, release-helper gate, tool pin, lockfile or runtime dependency changed.

Parent checks:64 focused workflow/distribution tests passed in2.25s, including the sdist-content check; Ruff lint and formatting passed on256 files; strict owned-test typing passed; all pre-commit hooks and diff checks passed. The initial attempt passed64 tests but stopped at three Ruff PT-style findings, corrected before the successful rerun. Independent verification reran41 workflow tests successfully with bytecode/cache writes disabled. No setup, download, actual renderer or hosted rehearsal was executed.

**Keep this branch local and unpushed.** Its new CI step would execute downloads covered by the unresolved scoped permission request. Ordinary CI and final regeneration remain unverified for these new bytes. Existing PR18's ten green jobs apply only to its older1b52076 head. The full gate still requires approved authentic inputs, actual P1 assets, final source/version/registry alignment, hosted rehearsal and publication acceptance.

Follow-up: the current agg manifest covers darwin-arm64 only. Post-publication GIF CI needs a separately verified Linux pin or an explicitly reviewed compatible runner decision. Do not add an unsupported agg setup command or skip its regeneration.
