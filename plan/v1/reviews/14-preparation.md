# REVIEW 14 preparation

Verdict: REVISE.
Reviewed commit: `fc868ebe7cc826a1cb122a015370631f4766cad7`.

## Required changes

1. Installed-byte provenance: the global uv cache search and METADATA comparison do not identify the executed environment or verify its code/data. Use task-owned cache/tool roots, propagate official-index and no-config settings consistently, and compare the actual resolved installation's payload to the verified Task20 wheel before and after capture. Unrelated cached0.1 installs must not affect the check. Preserve HOME; do not repurpose it.
2. Recorder configuration: the pinned CLI does have capture-input, append and overwrite flags; document them as prohibited. Environment filtering alone does not disable system/user configuration. Use task-owned configuration/state paths, explicit input-capture-off and notifications-off settings, an environment capture allowlist, and verify zero input events in the raw cast. Correct the unsupported claim that no other configuration can be read.
3. Measure GIF duration: pinned agg transforms output frames and timestamps, so cast-duration-plus-three is not an exact GIF duration formula. Measure encoded frame-delay totals and enforce20–40seconds independently for raw cast and each final GIF. Keep speed1 and the no-trimming requirements.

Parent verification:38 unit checks passed0.15s; owned lint, formatting (including recording.md), strict typing and diff checks passed. These checks establish helper behavior, not actual capture, installed-artifact provenance, rendering or Task14 acceptance. Independent source review confirmed all three findings against the pinned asciinema/agg source. No real recorder/renderer/package/provider was executed.

The executor used fixed standard-library Python children in a few unit checks to verify inherited stdout/stderr and refusal before commands. This is a bounded deviation from V1-023's process-double-only wording. No uvx, model, recorder, network or denied action was involved; Codex accepts these harmless subprocess unit checks as stronger output-inheritance evidence. Historical REPORT14 remains unchanged; record the correction in the next report.

Follow-ups: preserve failed attempts; final genuine PyPI capture remains postpublication under Decision2. Task20 and all download/preview permissions remain unchanged. The original preparation CLI reported779896ms elapsed; this is not a subscription-spend measurement.
