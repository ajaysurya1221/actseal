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
| REL-1 1.0.1 release preparation | dated `v1.0.1` changelog and synchronised `CITATION.cff`; README and ADR 0019 corrections; version-aware receipt and release-document paths in `tools/check_release.py` with tests (1.0.0 history unchanged); `plan/v1/releases/1.0.1/RELEASE_NOTES.md` and `FINAL_REPORT.md` with named placeholders, shipped in the sdist; cached-native receipts for the changed Laya path (macOS and hosted run 37719743745) in `2026-10-08-release-preparation-1.0.1.md`; pre-tag wording resolved (V1-059) | R-REL1 REJECT (receipt routing and 1.0.1 notes belong before the tag; fixes applied) → R-REL1b REJECT (native receipt required; receipts collected, record added) → R-REL1c **ACCEPT** (one wording note, applied in the ledger commit) | 3c01ac9 + ledger commit ba2aed4 → PR #61 → main 758c65d (annotated tag `v1.0.1`) | met: hosted CI success on the PR head ba2aed4 (CI 37720993498 and 37720996351, CodeQL 37720996344, dependency review 37720996342, Gitleaks 37720996392) and on main 758c65d (CI 37721460739, CodeQL 37721460761, Gitleaks 37721460725); `check_release.py candidate` exit 0 on the clean merged `main` checkout at 758c65d before the tag (orchestrator re-run) and again on a clean clone of 758c65d after the tag (executor report); tag `v1.0.1` CI 37721934872 success; `publish-pypi.yml` run 37721934891 attempt 1, `pypi` approval recorded, all nine jobs success; receipts committed and placeholders filled under `plan/v1/releases/1.0.1/`, `check_release.py receipts` passes (V1-059 closing note); post-publication package R-REL1d **ACCEPT**, 2afacd7 → PR #62 → main 810bf8c; GitHub release `v1.0.1` published with the filled notes as its body (release id 406401019). Nothing remaining |

Narrow archival exception (accepted at review): the sealed preregistration inputs and the
archived producer source contain historical assistant-name references; they are published
verbatim because editing would break the seals. No assistant identifier appears in newly
authored text.

Verification limits common to all reviews: the reviewer's sandbox could not write temporary
files, so full test suites, packaging rebuilds and native integration were accepted as executor
evidence corroborated by hosted CI on the exact reviewed commits.
