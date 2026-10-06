# Actseal shared project state

Updated:2026-10-06. Sole writer:Codex. **v0.1.0 SHIPPED.**

## Current objective and authorization

The focused two-day OSS sprint is complete. The user chose Decision Contract,
authorized implementation and public delivery, delegated naming, and approved
routine execution/hooks. Product name: **Actseal — decision contracts you can replay**.
Claude Code Fable5.1/high implemented all product code and behavioral tests;
Codex specified, orchestrated, reviewed, verified and released it.
Public launch messages remain drafts; no further execution approval is pending.

## Publication identity

- [Public release](https://github.com/ajaysurya1221/actseal/releases/tag/v0.1.0) — non-draft, non-prerelease.
- Tag target `83fd04a5d340000aed6518109dce666dc208ad70`; annotation object3bea9261a5157ecaa0f032ec9de52f2dadea12e8.
- [Final CI](https://github.com/ajaysurya1221/actseal/actions/runs/37456279878): all4 Linux/macOS Python3.12/3.13 jobs green.
- Exact public-wheel quickstart passed in6.202398s including uvx preparation;
  both downloaded artifacts match reviewed hashes. Actual fixture badBLOCK/fixedPASS
  and offline replays agree. Native CLI retains real coverageBLOCK with128ABSTAIN.
- Main receives post-publication receipts after the tag. Product/tests, tag and
  release assets are unchanged by that receipt commit. See FINAL_REPORT and REPORT T70.

## Task ledger

| Task | Owner | State | Accepted candidate / integration |
|---|---|---|---|
| Planning package | Codex | COMPLETE | ee99eee plus approved ADR amendments |
| T00 foundation | Claude A | ACCEPT / MERGED | ebe11ff; merge86dbca0 |
| T10 contract/policy | Claude A | ACCEPT / MERGED | 9bdac25; merge28be58d |
| T20 statistics | Claude B | ACCEPT / MERGED | b1eace7; merge6d6d7c4 |
| T30 providers/faults | Claude C | ACCEPT / MERGED | 8b1efd6; merge87d2cd1 |
| T40 evidence/replay | Claude B | ACCEPT / MERGED | 98297d5; merge7a2939e |
| T50 CLI/demo | Claude A | ACCEPT / MERGED | 286ae67; merge7e696c5 |
| T60 acceptance | Claude C | ACCEPT / MERGED | 24d5818; merge3080079 |
| T70 publication | Codex | ACCEPT / PUBLISHED | 83fd04a; tagv0.1.0 |

## Resume pointers

Read FINAL_REPORT, REPORT T70 and REVIEW T70-02 first. For new implementation read
PLAN/CONTRACTS, relevant ADRs and the task spec; frozen shared types/acceptance remain
protected. Preserve all REPORT/REVIEW attempts. Scope/license/proprietary-core,
unverified-load-bearing and incremental-spend>USD100 escalation rules still apply.
No current blocker or required follow-up remains for v0.1.0.

## Verification and limits

Final local2282 default tests and14 packaging tests pass; no selected skips. Default
excludes14 packaging and6 integration tests, with separate accepted native receipts.
T60 also independently passed104 acceptance tests and all8 push/PR jobs. Source
fingerprintcd3a0976cf7886616f1fdf565c914f30d0c82cac530e7b9ffc4119e3a90300a7;
demo inventoryf894beeb06c4053d0965180ea98d229f3870887f3f09473f1599def541798d6d.
Raw responses may be private; .env, original research, local receipts/dispatches,
model weights and private-memory source are not tracked. Do not read/print real keys.

Incremental paid inference API spend USD0. Final cumulative Claude subscription
meters sumUSD115.08465475 estimated usage, not an invoice; repeated/resumed session
meters count once. Existing subscriptions, compute and labour are not claimed free.
Optional Jev, hosted tier, Marketplace Action and PyPI remain out of v0.1.0.

## Next action

No action is required to finish this sprint. The user can run the README's one-command
demo. Future work starts with the three evidence-driven steps in FINAL_REPORT;
no background automation or public promotional post has been scheduled or sent.

## Post-release follow-up — PyPI workflow

On6October the user requested a PyPI YAML workflow. Codex owns this CI/docs-only
follow-up under ADR0014. publish-pypi.yml promotes the pinned reviewed v0.1.0 assets;
manual validation-only dispatch is the default. No product, released asset or tag
change. PyPI account/environment configuration and actual upload remain external
steps; no upload has been performed. See docs/publishing.md.

PyPI workflow follow-up COMPLETE: PR8 merged at2a1ac36b0f9fe9dda52b946ab48c8e833269d40d; independent
REVIEW PYPI-01 and both four-job CI matrices passed. Hosted validation-only run
37482446498 passed on Ubuntu, publish job skipped. REVIEW PYPI-02 records exact scope.
Next optional action: configure the pending publisher using docs/publishing.md;
then explicitly run publish=true to upload. No package has been published to PyPI.
