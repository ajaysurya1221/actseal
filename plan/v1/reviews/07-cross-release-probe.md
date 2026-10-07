# REVIEW 07 — controlled cross-release probe

Verdict: **PASS for this pre-integration probe only**. Task19, committed registry approval and final-release compatibility remain pending. PR35's integration failure is not waived.

Reviewed verifier commit: `8acbf38add37235a306060cc81ea19d89ba61eed`. Its package Git tree `72e530dad60eae86f3a6b3273d0f299976eb3a27` is identical to main `23ea1b502e7b2eea815f599e6d39a09506fe60ea` and planning-only descendant `20b996917c25111bc9b043f22db000be0ff8fcdc`. Actual verifier fingerprint: `70fa95939f5992935678e0cd6edb709db9110659723f323fa681bebaf117deba`.

Original example archive is unchanged at source `277d8e23f0de161e72a8617c74d3b05e6d75069a`, producer `a5fe090202f75b07510407937a86ae35a7653a75eab3f4daa2d0ace2e7641642`, externally retained lock seal `cb009be0039afefd995f6eac3a8bd9767d6bf026a73273b47e87a51fc9fbd715`.

## Method and results

An isolated Python process redirected only `compatibility._REGISTRY_PATH` to explicit temporary registry fixtures, using the existing strict loader. No fingerprint, validator, assessment rule, source file or evidence byte was altered. Import/network guards were installed before importing Actseal. All Actseal import origins were checked against the pinned release worktree.

- Both exact fingerprints mapped to `actseal-choice-v1`: shared lock/input validation, assessment and replay matched the entire original PASS verdict, including both intervals; CLI JSON exited0.
- Empty, producer-only and verifier-only mappings: ERROR with `integrity.lock`, CLI3.
- Wrong engine: strict registry rejection and ERROR, CLI3.
- Wrong external lock seal: ERROR with `integrity.expected_lock`, CLI3.
- Historical-lock collection: rejected before either `decide` or the model factory; both counters0; no output destination created.

The positive verdict retained160 total cases,136 accepted,1 error; risk interval `[0.00009248676847378344, 0.046001047099948664]`, coverage interval `[0.7754989626187914, 0.9075527563470258]`. These are authored demo evidence, not population or provider-performance claims.

Both full archive and package byte inventories matched before/after. The real packaged registry remained unchanged at SHA256 `0fcef28be291e8a96039ad354eda6d76390ea5c5081458a085aade24c15eb6fd`. No prohibited provider/native/transport import or network attempt occurred. No keys or providers were accessed; no cleanup was attempted.

## Reproduction receipts

Independent verifier executed `/Users/ajay/.codex/worktrees/actseal-v1-release/not-yet-named/.venv/bin/python -I -B /tmp/actseal-task07-cross-release.ZkiLe8/probe.py`: exit0,0.176s. Receipt SHA256 `e6885488f4bd4e1d22b79d85847995fd60a698a4e29111c50b724b1b66a1502b`.

Codex read the complete238-line temporary harness, checked its SHA256 `e30d39ecddc6821d69441171194acd84a9d7092b1f7d86df3b420ed899232205`, verified both source heads, then reran identical bytes in a separate owned directory: `/Users/ajay/.codex/worktrees/actseal-v1-release/not-yet-named/.venv/bin/python -I -B /tmp/actseal-parent-cross-release-323xk4kz/probe.py`. Exit0,0.173s, empty stderr; receipt SHA256 `12e349240aa6cc4edc7c83d923997bb06d266090f5c5ae3e0ece6b6c11298720`. Both directories retain the harness, strict registry fixtures, full receipts and logs.

## Required follow-up

Claude Task19 must implement the approved explicit registry integration and permanent regression coverage against final product bytes; preserve the original archive. Re-run against the actual supplied wheel and final fingerprint. This probe neither adds approved registry entries nor proves general cross-release compatibility. The example's hardcoded exact-replay wording still needs the previously specified truthful integration repair.
