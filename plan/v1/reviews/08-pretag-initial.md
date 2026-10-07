# REVIEW 08F — pre-tag documentation

Verdict: REVISE.
Reviewed source0363124922637b944a2af52230518425e7503e22 and REPORT88a5b30.
Scope:13 authorized docs; no source/tests/assets/registry change. Earlier
reports stay immutable. Findings independently reviewed by Codex and its
receipt reviewer; docs/checker source inspected, checks pending correction.

1. P1: Full implementation SHA256 in RELEASE_NOTES is not a release artifact
   hash and cannot satisfy tools/check_release.py's receipt hash allowlist.
   Abbreviate it and link docs/versioning.md; do not weaken the checker.
2. P2: ADR0016 mislabels ordinary push/PR CI37581140052/37581142565 as a
   publish-workflow rehearsal. ADR0019 says historical checks otherwise
   passed although build/packaging/reproduction/hooks were skipped. Correct
   the descriptions, retaining failed history.
3. P2: Threat-model assertion that a key never enters any evidence exceeds
   adapter metadata protections: arbitrary raw inputs/bodies are unredacted.
   Limit the claim to generated metadata/diagnostics and keep the warning.
4. P2: ADR0020 implies social resized; social remained byte-identical while
   three SVG groups changed. Keep pending recording/final review as explicit
   future gates until supported by actual receipts.

Required changes: above in order, then add the actual final first-screen and
completed rehearsal receipts supplied in the corrective packet. Preserve
original REPORT; append a new correction REPORT. No full release ACCEPT.
Follow-ups: final candidate/hosted checks, tag/publication and genuine recording.
