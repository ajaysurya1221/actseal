# REVIEW 09 — ordinary asset CI glue

Verdict: ACCEPT, scoped to Codex-authored commit `a09b69f000c908a82f4b15c850f758c66aa911e0` over `ca3d6bc6d598966c6ef976b188e9193607a3e75f`.

Exactly24 lines add an unconditional push/PR job in `.github/workflows/ci.yml`. It installs locked authoring/development Python dependencies, type-checks asset sources and checks committed output regeneration plus README image references. It contains no font/binary fetch step, permission changes or ignored failures. Required authoring inputs must be provisioned through an authorized path before dependent renderers merge.

The independent reviewer confirmed missing/stale implemented outputs and unresolved referenced assets fail. Planned renderers remain informational; zero implemented/eight planned is not publication readiness. The separate publication gate still requires all static P1 assets and remains a prerequisite of publishing.

Parent checks after integrating accepted main: **284 release tests passed in12.01s**, release workflow validation passed, strict asset typing passed and bootstrap regeneration/reference validation passed with zero implemented assets. Separate reviewer performed source/YAML inspection without rerunning denied native, mutation or rasterizer operations.

Required changes for this isolated CI patch: none. Task09 overall remains incomplete:09R4 receipt repairs, real static assets, authoring setup, final asset filenames and hosted rehearsal are still required. No release or upload is authorized by this scoped review.
