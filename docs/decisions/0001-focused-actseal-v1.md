# ADR 0001: Actseal is a focused standalone decision-contract tool

- Status: accepted for the authorized implementation sprint.
- Date: 2026-10-06 (Asia/Kolkata).
- Authority: user selected **Decision Contract** and **Focused two-day v1**, then delegated naming and requested implementation.

## Decision

Build **Actseal** in a new repository. Its v1 evaluates one categorical decision against a frozen application policy, measures accepted-case error risk and action coverage, and replays recorded evidence without a provider. The target user owns an application that must decide when a model response may authorize an action. The fixture quickstart is local and keyless; a separate optional Laya path demonstrates a real open-weights model.

The user selected the Decision Contract recommendation after reconciliation. The competing process-wrapper enforcement proposal would require control over execution paths the proposed wrapper cannot establish, plus a broader security boundary than this sprint can validate. Actseal produces decisions for an integrating application; it does not claim to intercept every agent action or provide a sandbox.

The implementation target is two days. Day 3 is an exceptional hardening/release buffer, not permission to expand the IN list. v1 excludes a proxy, hosted service, automatic threshold fitting, general agent orchestration, paired non-inferiority, and certification of mixed-provider fallback chains. The complete scope and frozen interfaces live in [PLAN](../../plan/PLAN.md) and [CONTRACTS](../../plan/CONTRACTS.md).

## Naming and repository boundary

The parent planner chose **Actseal** under the user's naming delegation. Its reported preflight found no exact GitHub/web match and a PyPI 404; this is a dated availability observation, not a reservation or trademark conclusion. Recheck availability immediately before repository/package creation. Package naming changes alone must not expand the feature set.

Preserve all existing repositories and their Git histories. This repository receives only explicitly attributed minimal reuse units. No private shared-brain implementation or evidence is copied into the public product.

## Consequences

The first release demonstrates a narrow, inspectable action-decision contract with replay. The proposed improvement over score dashboards is testable failure behavior and reproducible decisions; **10x** remains a product hypothesis, not a measured speed, accuracy, reliability, or adoption claim.
