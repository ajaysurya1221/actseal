# ADR 0002: Keep the core small and port only attributed pure statistics

- Status: accepted.
- Date: 2026-10-06.

## Decision

Use Python 3.12+ and the standard library for the policy, statistical, evidence, replay, and CLI core. Optional model adapters must not be imported by the core. Development tooling and optional inference dependencies are pinned in the new repository's lockfile.

Port the Clopper–Pearson implementation from public Apache-2.0 [agent-reliability-ci at `d13dd94124cb71d378a4e76224fc115b750e8133`](https://github.com/ajaysurya1221/agent-reliability-ci/tree/d13dd94124cb71d378a4e76224fc115b750e8133): `src/arci/stats.py` lines 8–10 and 15–120. These units use integer binomial-tail comparisons and a fixed 60-step binary64 bisection. Preserve the supported domain: counts from 0 through `n`, `1 <= n <= 10_000`, and `2.5e-7 <= tail < 0.5`. Reject booleans/non-integer counts at Actseal's public boundary. Do not port Wilson, Newcombe, the ARCI gate, or its process runner.

Adapt the independent oracle and known-answer tests from that same immutable source:

1. `tests/unit/stats/test_cp_reproducibility.py`: Fraction tail oracle, Decimal closed forms, canonical hexadecimal results, boundary and libm-independence tests.
2. `tests/unit/stats/test_stats.py`: reference values, monotonicity, symmetry, supported-tail rejection, and bounded coverage checks.
3. `tests/acceptance/test_stats_gate.py` lines 19–42: the CP golden vectors and their assertions, without ARCI's gate fixtures.

Preserve attribution, license text, applicable NOTICE information, and a record of local modifications. Use Apache-2.0 for Actseal's original code, subject to the complete license inventory before publication. The canonical JSON and self-sealing record pattern may be adapted from MIT [evalopt-graph at `9bbc192443dc713f0f3344939a441c4a66e8a44d`](https://github.com/ajaysurya1221/evalopt-graph/tree/9bbc192443dc713f0f3344939a441c4a66e8a44d); preserve its MIT notice when code is copied.

## Rationale and limits

A runtime dependency on ARCI would add Pydantic/PyYAML, experiment schemas, POSIX subprocess machinery, and an unreleased-to-PyPI installation path. Depending on evalopt-graph would introduce an additional acceptance/evidence vocabulary. Neither is needed for a pure categorical contract.

The port's tail comparisons are exact at their supplied binary64 inputs; returned endpoints are finite-bisection approximations to real roots. Preserve that distinction in documentation. Upstream tests establish a useful reuse baseline, not acceptance of the new package. [VERIFICATION](../../plan/VERIFICATION.md) records the source checks; [CONTRACTS](../../plan/CONTRACTS.md) defines Actseal's public boundary.
