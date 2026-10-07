# TASK 08R2: Correct responsive-change evidence wording

Goal: close two independent review findings without changing accepted README/tests.
Owner: the completed new Claude08 session, Fable5.1/high; estimate10minutes.
Context: TASK08R, report08-responsive, review13-real-readme-sizing.
Frozen interface: README/test source at8d03ba3 is scoped ACCEPT. No source change.
Files: narrow correction in docs/decisions/0020-reproducible-visual-assets.md;
new plan/v1/reports/08-responsive-correction.md only. Preserve earlier report.
Acceptance: ADR measurement range says1000–1200px, not800–1200px: the table
establishes repository widths638–758 only for1000–1200. The800px observation
was on a different file-preview surface and must not support that statement.
Additive report must correct 'separate literal commands': the actual calls
were piped to tail with echo of pipestatus[1], and the first baseline used
$? (tail status). Preserve actual commands and distinguish parent independent
unwrapped checks:13passed/1missingarchitecturefail,docs gateexit1,hooksexit0.
Clarify synthetic tests/visual/visual_support.py's880px probes stay unchanged
and are not13R scope. Treat20minutes as an estimate, not measured runtime/API
spend. No new test count, green gate, live or publication claim.
Tests: none required for prose correction; git diff --check must pass.
Constraints: only owned paths, no merges/push/network/key/source changes;
normal permissions. Stop any denied operation; no alternative recovery route.
Done when: git diff --check exits0, conventional commit(s), clean owned tree.
Report: REPORT08R2; changes, exact commands/results, deviations, open gates,
actual spend or unknown. Codex independently reviews before integration.
