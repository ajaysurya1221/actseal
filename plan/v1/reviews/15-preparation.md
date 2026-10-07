# REVIEW 15 preparation

Verdict: REVISE for shared CLI tests; no material source defect found in the bounded social-renderer review.

Reviewed source/test commits: b11bbbefaccbab07559f31847ee9068dd33a7310 and efcea002a248f530ce8446690a452e3f2f56937b. Report-only head: d489fa4f222919a4ee50ed8bbfc412ace29c80ef. Independent read-only review covered the complete renderer, tests and social-only inventory change; its file hashes match the report.

The source reuses approved hero copy/palette/helpers, fixes a1280×640 composition and fails on missing inputs or glyph overflow. Rasterization uses existing verified binary loading, fixed command construction and bounded execution. Explicit outline/process/header-only PNG doubles test wiring and failures; they do not establish authentic glyph fit, complete PNG output, raster determinism or readability.

Parent full visual suite:245 passed,3 failed in1.24s. All failures are stale bootstrap assertions in test_render_cli.py: social is now implemented and must report missing font/resvg, rather than being counted as planned. The command chain stopped at pytest, so later parent lint/type checks in that chain did not run. Executor-owned checks remain separately reported claims.

V1-027 authorizes only the shared CLI test repair and a new REPORT. Preserve explicit prerequisite diagnostics, no checked/written output, fontTools-free import/help and existing hero assertions. Isolate the tool cache to an empty temporary fixture; shared tests must not depend on the operator's global cache. No product fix, font/tool download, actual renderer/preview or placeholder deliverable is authorized. Preserve Task12's shared assertions during final integration.

Full Task15 remains PARTIAL pending Task11 acceptance, authentic licensed inputs, actual PNG generation, repeated byte comparison and readable rendered review. No image has been delivered or uploaded.
