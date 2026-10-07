# REVIEW07 strict archive repair

Verdict: ACCEPT for source-only repair at277d8e23f0de161e72a8617c74d3b05e6d75069a. Full Task07 remains PARTIAL; tests and example execution on this head are not authorized or claimed.

Independent source review confirms every active archive must pass core replay, return non-ERROR and match its archived verdict. Example-specific root/bundle locks, frozen contract, fixture identity, raw datasets/input hashes and fresh result agreement are retained. All active archives are checked before any queue operation. Request binding and honest partial-effect limits remain. A separately fresh run cannot repair an unsupported archive left active; guidance and REPORT07R3 now explicitly correct that earlier mistake.

Frozen authored inputs/generator, original e26399c recording and product source/empty registry remain byte-identical. Parent independently ran owned Ruff lint/format, strict mypy (10files), diff and frozen-byte checks, all passing. Reviewer performed read-only inspection; no pytest collection, imports, example execution or temp preparation. Earlier executor tests remain historical claims and do not cover this head.

Follow-ups: pending scoped human permission, full deterministic checks, dependency03 native gate and exact-head hosted CI. Task19 must explicitly review/register original a5fe0902… and final producer before final acceptance. Replace planned-Task19 wording in released example prose/output with the actual completed maintainer compatibility decision; retain historical REPORTs unchanged. No archive exclusion or resealing approved.
