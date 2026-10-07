# TASK 08F: Finalize immutable pre-tag documentation

Goal: ensure the tagged README, changelog, docs and packaged release notes state
the implemented1.0 scope accurately before any publication. Estimate30minutes.
Owner: Claude Code Fable5.1/high documentation lane, after accepted13R integration.
Context: approved Task08/19/21, docs/publishing.md pre-tag finalization gate,
current STATE and accepted reviews, unchanged implementation fingerprint
8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3.

Frozen contract: no change to APIs, statistical semantics, registry, labels,
threat limits, provider behavior, README opening order or quickstart commands.
Experimental Jev remains opt-in and carries mocked-transport evidence only.
No accepted live run exists; the959-case preregistration is not a run receipt.
Original synthetic example archives remain unchanged and separately identified.
Historical REPORT/REVIEW facts stay historical, including failures and denials.

Files to modify: README.md, CHANGELOG.md, plan/v1/RELEASE_NOTES.md;
current-status wording in docs/architecture.md, docs/threat-model.md,
docs/dependencies.md, docs/versioning.md and ADR0004/0015/0016/0017/0019/0020;
new plan/v1/reports/08-pretag.md only. No product code, tests, assets, schemas,
packaging, lockfile, other reports, state or review edits. Ask Codex for a
specific ownership amendment if an additional current-status document is needed.

Acceptance criteria:
- Resolve implementation-level candidate/unreleased/missing-architecture claims
  to the accepted source facts and exact receipts supplied at dispatch. Preserve
  genuinely historical dated statements, labelled as history, without rewriting
  failed runs into success. Add current closure paragraphs where appropriate.
- Fix docs/threat-model.md's stale assertion that Jev is outside v1: experimental
  Jev is included; autonomous fallback is outside1.0. Retain all evidence limits.
- Release notes/changelog describe1.0 implementation without claiming a tag,
  public PyPI install, attestation or final recording already exists. Remove
  DRAFT/candidate top-level implementation markers. Only named pipeline-generated
  build/post-publication receipt placeholders remain in release notes; real
  prepublication tests and reviewed static figures must cite actual receipts.
- Live audit remains not run; no key/call/journal/verdict invented. P2 figures
  remain outside the delivered1.0 scope unless an accepted implementation is
  explicitly supplied. Genuine recording follows approved post-PyPI exception2A.
- Leave README media paths/order/alt text and evidence-boundary wording intact.
  No numerical performance claims or inferred model accuracy.

Tests to add: none for status prose. Existing docs, asset-reference and strict
metadata checks must pass; report failures, never edit their tests to hide them.
Constraints: you are not alone; edit only owned paths, no network/key/provider,
download, merge, push or tag. Normal permissions. Stop any denied operation;
do not recover its suboperations with another tool or narrower command.

Done when (separate unwrapped commands; no tail/head or echo wrappers):
```bash
uv run --frozen pytest tests/docs
uv run --frozen python tools/check_release.py docs
uv run --frozen pre-commit run --all-files
git diff --check
```
REPORT08F: status, files/commits, exact commands and real exit codes, cited
receipts, deviations, remaining release gates, measured spend or unknown.
No automatic publication or full-release ACCEPT follows from this task.
