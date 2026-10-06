# REVIEW 05 initial offline preparation

Verdict: REVISE.
Reviewed source:34c62811eb6a14906249611cc4b1e42a386478c6 against212a1d6fae154dff0ea5b3b284174a53ac7f43e0. Report-only head64f9a7f preserves that source.

## Findings ordered by severity

1. High: HTTP200 credential echoes enter evidence. src/actseal/experimental/providers/jev.py:244 retains every bounded UTF-8 success body, including an echo of the current synthetic Authorization credential. Independent in-memory transport reproduction serialized that credential in CapturedOutcome. Reject credential-bearing bodies with no retained body and a fixed nonsecret warning; cover literal and JSON-escaped echoes while preserving ordinary body bytes. No real credential was used.
2. High: premature fixed-length HTTP EOF can produce ACT. Atjev.py:230, HTTPResponse.read(MAX+1) may return fewer bytes than Content-Length without IncompleteRead. A real stdlib HTTPResponse over in-memory bytes declared192 but supplied182 bytes of complete choice JSON; capture succeeded, response.length remained10 and policy returnedACT. Require complete bounded framing before success; classify incomplete transport asunavailable. Add real in-memory fixed-length/chunked/oversized regressions.

3. Medium: offline=True currently constructs an unavailable model instead of rejecting setup. ApprovedPLAN.md:352 explicitly requires rejection before a request. Require ProviderSetupError before reading the environment or constructing transport, and preserve import-only/no-key safety. Shared injected-exchange conformance does not require an offline constructor; correct only the new expectations. The initial core review missed this and is superseded on this point.

Independent scope evidence:80 mocked transport tests passed0.50s but did not cover these probes. Separate core/profile/schema/conformance review passed358 focused tests2.51s and found no material defect in its assigned scope. Five provider enums, six faults, selected-probability gating and transport-free replay remain consistent; old fixture/Laya negative controls remain intact. These partial successes do not waive the transport findings.

Required changes: repair both transport defects and extend meaningful regressions; run exact task checks and hooks; return a newREPORT preserving the original attempt. Resolve the reported offline-setup interpretation against the approvedPLAN before acceptance. No live calls, actualkey access or .env.example access is authorized while its scoped approval is pending.

Follow-ups: fullTask03native dependency, finalTask19registration/compatibility and optionalinclusion gates remain. V1-022 already ratified the four bounded shared-file deviations; REPORT05 did not know that later disposition. The denied shell loop was not rerun: executor continued already-authorized schema edits using earlier evidence. It did not replace the denied .env.example read with another mechanism. Explicitly retain both denials in the final receipt.
