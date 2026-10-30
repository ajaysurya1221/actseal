# Task 60 — dependency readiness maintenance

Owner: Codex (packaging/CI dependency lock). Authorized 30 October 2026 by
the final readiness plan.

Update only Virtualenv and Filelock to inspected, non-yanked upstream patched
versions: Virtualenv 21.14.13 and Filelock 4.2.1. Preserve direct package pins,
source, interfaces, assets, frozen evidence and releases. Do not run models or
native inference.

Done when the lock diff is limited to these two dependency records, frozen
setup and required local checks pass, independent review accepts the candidate,
and exact-head hosted checks pass before merge. Report the untested native
integration and distinguish dependency remediation from proof of a reachable
product exploit. No alert dismissal or release/tag action.

Local gates and independent acceptance are recorded in
[review 60](../reviews/60-dependency-readiness.md). The PR records the eventual
hosted-check and merge results; acceptance does not predeclare those outcomes.
