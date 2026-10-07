# REPORT 14 (activation correction)

Status: **DONE** (report-only). Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, same session `241e6a45-571b-4ca9-ad83-243d7c53b003`, branch `claude/v1-14-published-recording`. The activation commit `31c99168a2fe4d2eb8d0fbd07d781fff5d23aa8f` is independently ACCEPT; no source, asset, test or receipt file is changed here. This report is additive and corrects three details in earlier Task 14 reports, which are preserved unchanged as history.

## Changes

Three receipt details are corrected explicitly; the referenced statements remain in their original reports.

1. **Output count in REPORT 14 (activation), Verification table, `render.py --check` row.** It says "all 17 committed outputs … match regeneration". The actual inventory and the check report list **15** outputs: 12 SVG (hero 4, how-it-works 4, architecture 4), 2 GIF (demo light and dark) and 1 PNG (social). The `[ok] … matches regeneration` lines quoted in that report's own summary count 15. The summary line `5 asset(s) checked; 3 planned/not implemented; 0 error(s)` and the `16 image reference(s) checked` figure are unchanged and correct.
2. **agg call count in REPORT 14 (activation), Verification paragraph and Spend.** It says "before each of its two renders per variant" and "Four local agg renders during the regeneration checks". The pipeline renders every implemented asset twice per run for its determinism comparison, and the demo renderer produces two variants per render, so each `--check` run that includes the demo makes **4** agg calls; the two commands run in that phase (`--check --only demo` and the full `--check`) therefore made **8** agg calls in total during activation. This is distinct from the original raw-capture phase in REPORT 14 (capture), where exactly **4** agg renders were made by hand (light a/b, dark a/b) to establish two-render identity. Each of the 12 calls across both phases was preceded by `tools.verified_binary` re-hashing the pinned agg; none of these counts changes any committed byte.
3. **Environment statement in REPORT 14 (capture), Controlled environment section.** It says "Every command from warm-up on ran under the `env -i` prefix". That is too broad. The controlled `env -i` prefix (task-owned uv cache/tool/credential roots, no uv config or `.env` file, official index, keyring disabled, empty netrc, asciinema config/state roots) governed every **package probe and the capture itself**: `uv cache dir`, the warm-up `uvx --python 3.12 actseal --version`, the direct `"$ENV_BIN" --version`, both `uvx --offline … --version` runs, `uv python find 3.12`, the helper's stdlib-import check and the `asciinema rec` capture (whose children received exactly the allowlisted names shown in the cast's first output line). The **payload diffs, wheel extraction and hashing, cast validation and the four agg renders** ran in the separate authoring environment: plain `shasum`, `unzip`, `diff -r`, `find`, `ls -li`, `cat`, and `uv run --frozen --group assets python …` from the checkout, whose only inputs were the already-installed files under the task cache, the Codex-supplied wheel and the recorded cast. Those read-only comparisons and renders do not resolve, install or execute the package, so the binding they establish is unchanged: one environment, same path and inode before and after capture, package and dist-info byte-identical to the verified wheel, both lock fingerprints equal to the accepted source fingerprint. No package binding is weakened by this correction.

## Tests

No reruns were performed for this report-only correction. The results below are the parent's and the independent reviewer's at `31c9916`, not this executor's:

| Who | Check | Result |
|---|---|---|
| Parent | `pytest tests/visual` | 481 passed in 1.91 s |
| Parent | `render.py --check` regeneration | all 15 outputs match; 16 references checked; 0 errors |
| Parent | `mypy --strict` over asset sources and visual tests | 33 files, no issues |
| Parent | pre-commit hooks | all passed |
| Independent reviewer | focused checks | 123 passed in 0.68 s; protected paths unchanged |

This executor's own earlier runs are recorded in REPORT 14 (activation) and are superseded in their two corrected figures by this report.

## Deviations

None in this phase. The only action is the addition of this file and its commit; `git diff --check` was run before committing.

## Open issues

- Exact-head hosted CI regeneration of the committed GIFs with the pinned Linux x86_64 agg remains pending.
- Root README and final-receipt integration belong to Task 21 and remain pending.
- Only the macOS arm64 agg has rendered the committed GIFs so far; the recording remains an illustrative receipt of the public 1.0.0 package, not authenticated model evidence.

## Spend

Actual billing unknown. No service calls, downloads, model inference or tool executions in this phase. Claude subscription session only; CLI elapsed time not exposed and not estimated.
