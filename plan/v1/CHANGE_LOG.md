# Actseal v1 execution amendments

The approved PLAN.md and original task blocks remain immutable. These entries record bounded implementation clarifications and observed defects.

## V1-001 — Full baseline import-isolation repair (6 October 2026)

Evidence: REPORT/REVIEW 01. The exact approved all-tests invocation produced 2300 passes and two module-absence failures after genuine native tests imported Laya/NumPy. Isolated reproduction passes.

Decision: Add Task 01R, a prerequisite to Task 02, owned by manual Claude A. Ownership is temporarily limited to the two named test files and its REPORT; no statistical algorithm, oracle, schema or runtime change is authorized. Preserve the original full-suite Done-when command. This is a necessary repair inside the approved verification scope, not permission to weaken a test.

## V1-002 — Task 10 dependency prerequisite

Task 10's approved `--group assets` commands require an assets dependency group absent from the baseline. Codex Task 09 will add only `fonttools==4.66.1` to a non-runtime `assets` group and regenerate uv.lock using uv 0.12.5, with independent review and hosted CI before integration. Claude V does not own pyproject.toml or uv.lock.

## V1-003 — Approved Task 02 frozen-contract amendment

The approved v1 plan section E explicitly authorizes PlanLock.replay_engine_version, separate format-version constants, schema-2 locks/manifests, versioned CLI receipts and the reviewed compatibility registry. These changes supersede conflicting v0.1 freeze language only for Task 02's owned implementation and schema/identity fixtures. Preserve numeric goldens, policy/statistical semantics, canonical encoding rules and historical evidence. Task 02 remains held until Task 01R is ACCEPT.
