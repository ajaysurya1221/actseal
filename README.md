# Actseal

**Decision contracts you can replay.**

Actseal is an Apache-2.0 Python package being built to freeze a categorical
decision policy, measure accepted-action error and coverage, test provider
failures, and independently recompute a verdict from captured evidence.

Development is in progress. There is no released package or validated quickstart
yet. The fixture-first CLI, local Laya adapter and offline replay are the v0.1.0
scope. See the [plan](plan/PLAN.md), [frozen contracts](plan/CONTRACTS.md), and
[current state](plan/STATE.md).

Actseal checks its own policy path. It does not establish that labels are true,
that another application follows the policy, or that authored demonstrations
represent deployment populations. Hashes establish consistency; provenance needs
an externally trusted lock hash.
