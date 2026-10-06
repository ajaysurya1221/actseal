# ADR 0009: Permanent worker loss invalidates the statistical run

- Status: accepted; correctness amendment before parallel lane dispatch.
- Date: 2026-10-06.

## Evidence and problem

The native adapter terminates its resident worker after a timeout. Later
unavailable results depend on an earlier case. IID inputs alone cannot justify
binomial bounds on persistent-process availability. NIST's [binomial reference](https://www.itl.nist.gov/div898/handbook/eda/section3/eda366i.htm)
requires a fixed trial success probability (checked 2026-10-06).

Independent counterexample calculated by Codex: for 100 cases and healthy-call
timeout probability 0.01, permanent shutdown gives expected run coverage
sum(0.99**k for k in 1..100)/100 = 0.6276279821395025. All 100 accept with
probability 0.3660323412732292, producing CP coverage lower bound
0.0125**(1/100) = 0.9571259697615615. This cannot bound persistent-process coverage.

## Decision

After complete integrity checks, a regular Laya capture with timeout or unavailable
forces ERROR, reason `infrastructure.worker_invalidated`, zero counts and [0,1]
intervals. Retain all scheduled terminal records as diagnostic evidence. Synthetic
fault captures are excluded. Nonfatal provider failures remain in a valid
experiment's denominator. No public record or callable signature changes.

Timeout terminates/joins the worker and returns timeout. Unexpected death, EOF or
unusable IPC returns unavailable and invalidates the instance. Later calls remain
unavailable. A recoverable inference error may return provider_error only if the
worker remains healthy and request/reply synchronization is intact. No restart,
replacement sample, post-failure resealing or automatic retry is allowed.

The statistical target is independent case outcomes under a fixed operating
regime and selector. It supplies no bound on persistent-process uptime or run
completion probability. The guarantee is unconditional over one prespecified
attempt: requiring completion only removes outcomes from the original fixed-sample
PASS event. It does not justify confidence claims conditioned on completion.
Never discard ERROR attempts and retry until PASS; retain all attempted runs.
ERROR bundles are diagnostic, not completed statistical certification. Sampling
and honest history cannot be proved by hashes.

## Consequences

T20 assessment, T30 lifecycle tests and T40/T50 replay/integration enforce this
reason and precedence. T10 and the numerical kernel are unchanged. This tightens
failure semantics for statistical correctness; it adds no feature. Broader
availability implications in the research are not adopted.
