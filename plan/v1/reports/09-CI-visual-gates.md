# REPORT09 CI visual gates

Status: DONE for bounded CI glue; full Task09 remains incomplete. Author: Codex within approved Task09 ownership.

The release helper requires all four reviewed hero output names, preserving all four workflow variants. Four negative cases remove one hero variant at a time. Ordinary CI now runs the visual test suite in its existing assets job, where fontTools is installed, so font-dependent tests no longer disappear from every CI lane. No font/binary provisioning or download was added; that approval remains pending. Final real inputs, assets, rendering and exact publication rehearsal remain prerequisites.

Checks:132 release-receipt/asset checks passed4.35s;204 current visual tests passed1.14s with the assets group; repository hooks, helper strict typing and diff checks passed. These are source/mock tests, not real-image acceptance. No product source, permission, upload or artifact flow was changed. No paid API call, key read, download or publication occurred.
