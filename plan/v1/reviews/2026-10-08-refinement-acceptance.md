# Acceptance ledger — post-release refinement session, 8 October 2026

Independent reviews were produced by the session's architect/reviewer and are archived in the
operator's hand-off folder (`handoff-2026-10-08/astra/`). This ledger records what was accepted,
at which commit, and which gates remain. Dates and times are IST.

| Package | Scope | Review verdict | Reviewed head → merged | Remaining gates |
|---|---|---|---|---|
| A1 README first screen, hero, social | `README.md`, hero/social renderers and outputs, presentation guards | ACCEPT-WITH-FIXES (asset notes fix applied) | 491d912 → PR #51 → main 72f4a2f | none |
| A1b figure selection on GitHub | README `<picture>` sources, guards, asset notes, CHANGELOG | ACCEPT-WITH-FIXES (wording + CHANGELOG applied) | 85ea4a5 → PR #52 → main 5e127fe | hero legibility follow-up (V1-057) |
| A3 automation and metadata | Dependabot, CodeQL, dependency review, Gitleaks, `CI / required`, project URLs, CITATION.cff | ACCEPT | 75c0223 (+ merge 2f02927) → PR #54 → main 8dea59d | none; ruleset `main` active |
| A2 + A2b hardening and 1.0.1 bundle | streaming JSONL readers, Laya IPC sequence type, exception docs, version 1.0.1, registry entry, test and documentation amendments (V1-055) | A2 ACCEPT-WITH-FIXES → A2b **ACCEPT**; approved final fingerprint `dced01d79e64799a19a75c0957f3684a48249c58ebb27d346336e7420195bcb4` | d66795a (+ merge 887fa77) → PR #56 | tag `v1.0.1` and publication: human only. Before tagging: date the changelog heading, sync `CITATION.cff` version/date, move applicable Unreleased entries, rewrite the receipts gate paths for 1.0.1 (`tools/check_release.py receipts` still targets 1.0.0 history). |
| D + A4 preregistered Jev audit | collection from snapshot d3edbab (run ec3877960b376021ce4c81110dad353c); 21-file result package; ADR 0018 addendum | collection **ACCEPT**; package ACCEPT-WITH-FIXES (wording + integration applied) | 8912054 (+ merge acbf51b) → PR #55 | hosted CI on the final commit |

Narrow archival exception (accepted at review): the sealed preregistration inputs and the
archived producer source contain historical assistant-name references; they are published
verbatim because editing would break the seals. No assistant identifier appears in newly
authored text.

Verification limits common to all reviews: the reviewer's sandbox could not write temporary
files, so full test suites, packaging rebuilds and native integration were accepted as executor
evidence corroborated by hosted CI on the exact reviewed commits.
