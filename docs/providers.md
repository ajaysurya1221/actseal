# Providers: native Laya reference and normalization

Status: full T30 accepted at `8b1efd6314b5b65ecb51f292a5bc767ff8b93ed7` and merged as `87d2cd1`, 6 October 2026. Earlier candidate `17ed0875541ecfa6402991dc90e278beb2f4cc01` passed native product tests on macOS and Linux, and [REVIEW T30-03](../plan/reviews/T30-03.md) confirms those adapter/normalization/native-test bytes are unchanged in the accepted task. Historical upstream and product milestone receipts remain distinct below. The [stability manifest](stability.md) is normative for the 1.x product boundary; [CONTRACTS](../plan/CONTRACTS.md) is the historical v0.1 record of the unchanged provider semantics.

## Reference runtime

The v1 live-model path uses the optional Laya dependency. The fixture quickstart and evidence replay require no model or credentials. The reference is one categorical question, one explicitly selected checkpoint, CPU FP32, four Torch threads, and eager inference. Automatic model routing, MLX conversion, quantization, compilation, and alternate device promotion are outside this reference.

| Reference path | Compatibility and evidence boundary |
|---|---|
| Core fixture/replay | No third-party runtime dependency; ordinary product CI covers macOS/Linux with Python 3.12 and 3.13. Evidence publication requires the supported native filesystem operation. |
| Native macOS | arm64, pinned PyPI Torch wheel tagged macOS 14.0 or later; actual native receipts use Python 3.12.13. The wheel tag is a binary requirement, not proof of testing every macOS version. |
| Native Linux | x86_64, glibc >=2.28, official Torch CPU distribution; actual native receipt uses Ubuntu/Python 3.12.3. Python 3.13 wheel availability was checked, but native inference on 3.13 was not established by that check. |

The native receipts do not establish Intel Mac, Linux ARM, musl, Windows or GPU
support. Windows is unsupported in v1 for the core as well: exclusive bundle
publication depends on macOS/Linux filesystem operations, and no Windows
classifier or partial-support claim is made. There is no automatic device or
model substitution. Exact stack pins:
Laya 0.3.28; Torch 2.14.1 on macOS / 2.14.1+cpu on Linux; Transformers 5.18.0;
huggingface-hub 1.33.0; Safetensors 0.8.0; NumPy 2.5.3. See
[dependencies](dependencies.md) for the full locked graph and notices.

## Prepare the native stack and checkpoint

The supported native installation uses this repository's committed uv lock and
platform-specific CPU source configuration. From a checkout of the reviewed
release commit, with uv 0.12.5 installed, run:

```bash
uv sync --frozen --python 3.12 --group dev --extra laya
```

Do not substitute a bare wheel-extra or PyPI-only installation on Linux:
standard wheel metadata preserves `torch==2.14.1+cpu`, but installers do not
inherit the repository's `tool.uv.sources` CPU-index mapping. Without an explicit
CPU source, installation should fail rather than resolve proprietary CUDA
packages. [The dependency guide](dependencies.md#linux-cpu-selection-and-rejected-cuda-dependencies)
explains this distinction. The fixture [PyPI quickstart](quickstart.md) needs no extra.

Download the five pinned public artifacts once, separately from evaluation:

```bash
uv run --frozen --python 3.12 --extra laya python - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="convaiinnovations/laya-typed-decisions",
    revision="e929ae5cf69bc34259cd2f95c9e91145b818b1f0",
    allow_patterns=[
        "model.safetensors",
        "encoder/config.json",
        "rl_agent_config.json",
        "tokenizer/tokenizer.json",
        "tokenizer/tokenizer_config.json",
    ],
)
PY
```

This preparation accesses the model repository and requires space for the
optional packages, cache and 842,609,220-byte weight file. The adapter verifies
the expected artifact hashes before loading; the complete hash table is in
[dependencies](dependencies.md#weights-and-immutable-artifacts). An existing
offline environment must permit this explicit preparation step; do not confuse
a cache miss with successful offline inference.

## Lock, verify and replay with cached Laya

Root executed these lock/verify/replay operations using T50's committed synthetic
support-triage inputs at candidate `434c682`; the [receipt below](#native-cli-integration-receipt)
records the actual BLOCK outcome. The commands here use a fresh temporary parent
instead of root's receipt directory. Inputs remain `evidence_scope=demo` even
when a real model supplies the answers. The [release report](../plan/FINAL_REPORT.md)
records the final integrated checks.

Create only the parent working directory; the lock file and evidence destination
must be new:

```bash
actseal_native_root=$(mktemp -d "${TMPDIR:-/tmp}/actseal-laya.XXXXXX")
```

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya actseal lock \
  --contract examples/support_triage/fixed.toml \
  --calibration examples/support_triage/fixed_calibration.jsonl \
  --verification examples/support_triage/fixed_verification.jsonl \
  --provider laya --offline --out "$actseal_native_root/lock.json" --json
```

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya actseal verify \
  --lock "$actseal_native_root/lock.json" \
  --calibration examples/support_triage/fixed_calibration.jsonl \
  --verification examples/support_triage/fixed_verification.jsonl \
  --provider laya --offline --out "$actseal_native_root/evidence" --json
```

Inspect the verification status and exit code before continuing. BLOCK (1) and
INCONCLUSIVE (2) are legitimate results; do not adjust the policy or retry until
PASS. ERROR (3) needs investigation. Setup failure may leave no bundle; a complete
worker-loss bundle is diagnostic ERROR. When a bundle exists, replay it as a
separate command even if verification did not return 0:

```bash
uv run --frozen --extra laya actseal replay "$actseal_native_root/evidence" --json
```

Replay needs no native provider or model library and must preserve the original
verdict. Append `--expected-lock-sha256` with a separately trusted lock digest
when checking an externally supplied bundle. That digest anchors lock identity,
not the authenticity of response records or actual execution. Offline library
flags configure cached inference; they are not an OS network firewall.

## Native CLI integration receipt

On 6 October, root independently executed the real CLI at candidate
`434c682352d19e64c6349cb5a7aac44fa7554156`, following T50's
[ACCEPT](../plan/reviews/T50-02.md) at
`286ae67e252ecbb77e9c330ebe1f66cc375bfbab`, merged as `7e696c5`.
Environment: macOS 26.6.2 arm64, Python 3.12.13, uv 0.12.5; CPU FP32/four threads,
eager backend, compile=False, fast=False, max_len=1024/head_max_len=256. Exact
model/runtime pins and all five artifact hashes matched the reference above.
Both `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` were set; model preparation
was already complete and is excluded from these step times.

| Step | Actual outcome | Wall seconds |
|---|---|---:|
| `lock` | exit 0; 12 calibration and 128 verification cases; demo scope | 6.445306 |
| `verify` | BLOCK / exit 1; all 128 ABSTAIN; 0 ACT; 0 provider failures | 13.820518 |
| `replay` with expected lock digest | Same BLOCK / exit 1, counts, reasons and bounds | 0.092522 |

Risk is **[0, 1]**, unestimated because no case ACTed. Coverage is
**[0, 0.033655210093607835]**; its upper bound is below the frozen 0.50 minimum.
Reasons are `coverage.below_minimum` and `risk.no_accepted_cases`. Zero wrong
accepted cases here is not an accuracy result or a risk estimate of zero.
All six fault actions matched their expected dispositions. The warnings summary
preserved 128 occurrences of the upstream calibration warning and 27 occurrences
of `normalize.renormalized`; the former are per-record retained warning counts,
not 128 distinct loads. There was no threshold tuning, restart or retry until PASS.

Implementation fingerprint:
`cd3a0976cf7886616f1fdf565c914f30d0c82cac530e7b9ffc4119e3a90300a7`.
Observed lock digest:
`9abbd4b0ef47bb05efff1df1d4d5deb974b40ee72be49b6afe806665367d4267`.
Public [native CLI receipt](../plan/reports/T70-native.md) records commands and bundle hashes; raw local captures remain ignored.
Root replay supplied that lock digest; callers must use the digest belonging to
their own intended lock, not copy this run's value as a universal expectation.

This is a successful execution/replay check that preserves an unsatisfied
application contract. The authored inputs provide no population guarantee,
model-quality benchmark or general hardware/latency result. It does not replace
T60 or final release-candidate/publication checks. The replay command retains
`--extra laya` to mirror the recorded environment, but replay itself never
imports or invokes the provider and does not require that extra.

## Public Python boundaries

Use the documented submodules; the package root exports records/errors and
serialization helpers, not every callable. The [stability manifest](stability.md)
is the exhaustive inventory and the [Python guide](python-api.md) shows runnable
examples. The provider-facing boundary is:

| Import | Public boundary |
|---|---|
| `from actseal.adapters.base import DecisionModel` | `identity() -> ModelIdentity`; `decide(request, *, timeout_s) -> CapturedOutcome`; `close() -> None`. |
| `from actseal.policy import evaluate` | `evaluate(outcome: Outcome, policy: LockedPolicy) -> PolicyDecision`. The application must supply its trusted frozen policy and honor the result. |
| `from actseal.replay import replay` | `replay(bundle: Path, *, expected_lock_sha256: str \| None = None) -> Verdict`. Invalid evidence returns ERROR; invalid Python arguments may raise `SchemaError`. |

Direct provider calls collect raw captures. They do not by themselves execute
the locked collection/assessment protocol or certify a policy. The CLI/runner
owns the fixed evidence-collection deadlines; arbitrary low-level timeouts are
not equivalent evidence. Full record shapes are in [CONTRACTS](../plan/CONTRACTS.md).

## Upstream reference calls

These historical upstream calls document the native integration. They are not
a replacement for Actseal's preflight, capture, normalization or assessment:

```python
import laya
import torch

torch.set_num_threads(4)
agent = laya.load(
    "convaiinnovations/laya-typed-decisions",
    revision="e929ae5cf69bc34259cd2f95c9e91145b818b1f0",
    device="cpu",
    backend="eager",
    compile=False,
    fast=False,
)
result = agent.predict(
    "I was charged twice for my monthly subscription. Please refund the duplicate payment.",
    {
        "department": {
            "type": "choice",
            "instructions": "Which department should handle this support request?",
            "criteria": {
                "billing": "Charges, invoices, payments, refunds",
                "technical": "Software errors, bugs, outages",
                "other": "Any other request",
            },
        }
    },
)
```

`Agent.predict` aliases `Agent.system_one`; both accept `max_len` and `head_max_len`. The accepted adapter must explicitly use `max_len=1024`, `head_max_len=256`, and the preflight below. These are the pinned checkpoint's native defaults used by the smoke. Do not install model hooks or native `min_confidence` gating: Actseal owns the frozen selector and its threshold. The upstream [agent implementation](https://github.com/NandhaKishorM/laya/blob/v0.3.28/laya/agent.py) accepts an `expected_sha256` mapping in `laya.load`; use the artifact table in [dependencies](dependencies.md) before parsing model weights.

Record the loaded checkpoint revision, artifact hashes, package versions, device, dtype, thread count, runtime options, and preprocessing/normalizer version. The upstream result's `model` string is the generic `laya-rl-agent`; it is not checkpoint identity. Obtain identity from the requested immutable revision, verified artifacts, and `agent.revision`, not that response alias.

## Exact output and normalization

Native output is a dictionary with `model`, `answers`, and `usage`. Answers are keyed by the caller's question id. For Laya, `CapturedOutcome.body_json` must preserve the **complete native response dictionary**, serialized without removing or repairing fields. The adapter must not extract only `answers[question_id]`: doing so would discard the evidence needed to replay answer-id and truncation checks. The fixture adapter retains its separately documented inner-answer format.

The pure normalizer checks the observed `CapturedOutcome.identity` against the expected identity before interpreting the body, then dispatches on the expected provider. For Laya it validates the envelope's generic model marker `laya-rl-agent`, requires exactly the requested answer id, and validates usage before extracting the answer internally. The marker is a wire-shape check, never checkpoint identity. Replay performs these same checks without importing Laya, Torch, a tokenizer, or an adapter. Rejected bodies remain captured in full. Provider-shaped synthetic fault bodies follow the canonical generator in [CONTRACTS](../plan/CONTRACTS.md).

The smoke returned this inner answer identically online and in a fresh offline process:

```json
{
  "type": "choice",
  "choice": "billing",
  "probabilities": {
    "billing": 0.8085,
    "technical": 0.0877,
    "other": 0.1039
  },
  "confidence": 0.4352,
  "answer_confidence": 0.8085,
  "action": {"act_probability": 1.0}
}
```

The probabilities sum to **1.0001** because Laya serializes rounded values. This is an observed provider representation, not a malformed distribution to reject under an exact-sum check.

A separate offline rerun on 6 October 2026 captured the entire native response and verified this exact `usage` object:

```json
{
  "input_tokens": 59,
  "output_tokens": 0,
  "state_tokens": 15,
  "state_tokens_dropped": 0,
  "truncated": false,
  "truncated_questions": []
}
```

The first four fields are integers, `truncated` is a boolean, and `truncated_questions` is a list of question-id strings. Their upstream construction is [agent.py lines 1548-1557](https://github.com/NandhaKishorM/laya/blob/v0.3.28/laya/agent.py#L1548); lines 1567-1571 construct the full envelope. Native usage optionally includes `options`, a **mapping keyed by question id**. Its values contain `total: int`, `distinct: int`, and `tokens_per_option: int | None`. [collapsed_options](https://github.com/NandhaKishorM/laya/blob/v0.3.28/laya/common.py#L486) includes a question only when `options_distinct < options`; agent.py lines 1564-1566 omit `usage.options` entirely when the mapping is empty. The smoke emitted no `options` key. These diagnostics are separate from the answer's optional `action` object.

Pure normalization requires the six ordinary usage fields and validates their types; counts must be nonnegative integers excluding booleans. A missing or malformed required field is a malformed response. Reported dropped tokens, true truncation, nonempty truncated question ids, or well-formed nonempty collapsed-option diagnostics prevent answer acceptance. If `options` is present, validate its mapping and per-question fields rather than treating arbitrary truthy data as a valid diagnostic. The frozen contract determines the resulting failure code. These checks supplement preflight: usage cannot prove that instruction and option text survived their earlier token caps.

1. Require exactly the requested answer id, `type="choice"`, the frozen label inventory, a supported selected label, and finite numeric probabilities in `[0, 1]`. Booleans are not probabilities. Validate loaded identity separately.
2. For this pinned Laya adapter, accept only positive totals satisfying `abs(sum(p) - 1) <= 0.00005 * number_of_options + 1e-12`. This tolerance is specific to four-decimal serialization. Do not reuse it for arbitrary providers.
3. Normalize each probability by the observed total, preserve the complete raw provider answer, and record that normalization occurred. Gate on the normalized probability assigned to the validated selected label, even when another label has a larger probability. Do not silently substitute an argmax choice: the contract deliberately tests low-probability selected answers.
4. Preserve native `confidence` as ChoiceAnswer.provider_confidence; `answer_confidence` remains named in the original captured body. Neither is a safety guarantee. Ignore native `action` as a source of application authority: only Actseal's frozen policy can assign ACT, ABSTAIN, DENY, or ESCALATE.
5. Reject other schema or identity violations instead of coercing or repairing them. Rounded ties retain the validated native choice; the adapter must not introduce a new tie-breaking classifier. Error classification and the final disposition follow the frozen contract.

The normalizer version and rounding policy are part of the frozen system identity. A provider upgrade that changes serialization needs a reviewed normalizer and new evidence.

## Refuse truncation before inference

The pinned checkpoint has a **1,024-token total sequence context**, not 1,024 tokens of state in addition to the question. Its question/option budget is 256 tokens. Upstream can silently shorten state, instruction text, and options; checking string length or `usage.input_tokens <= 1024` cannot detect all three. These rules therefore belong inside the version-pinned Laya adapter.

Use the installed tokenizer and upstream packing helpers from [laya/common.py at v0.3.28](https://github.com/NandhaKishorM/laya/blob/v0.3.28/laya/common.py):

1. Validate the exact provider question with `Agent._check_question(question_id, question)` and convert it using `Agent._to_internal(question)`. These are private upstream APIs: isolate their use in the adapter, require `laya==0.3.28`, and pin behavior with packing-parity tests. `render_options(internal_question)` returns the strings actually presented as options.
2. Count each rendered option without truncation using `encode_text(agent.tok, " " + option.replace(agent.tok.mask_token, " "), add_special_tokens=False, truncation=False)["input_ids"]`. Reject any option above 48 tokens. Include one MASK marker per option; reject a sum above 240 tokens, where the native 256-token head begins further per-option clipping.
3. Count the exact instruction prefix `"%s question: %s" % (q["t"], str(q["ins"]).replace(agent.tok.mask_token, " "))` without truncation. Reject if it exceeds `256 - sum(option_token_count + 1)`. This detects instruction truncation that native usage does not report.
4. Call `build_sequence(agent.tok, state, internal_question, max_len=1024, head_max_len=256, return_stats=True, return_truncation_stats=True)`. It returns sequence ids, markers, option stats, and state stats. Reject any dropped state token, `truncated=true`, missing marker, collapsed option, or non-null `tokens_per_option`. A 1,024-token output sequence alone is not evidence that the original input fit.
5. Only after passing preflight call `predict` with the same state, question order, `max_len=1024`, and `head_max_len=256`. Reject a result if native usage reports truncation, dropped state tokens, or collapsed options. No user hooks may mutate a preflighted request before inference.

A failed preflight is a visible provider/input failure and cannot produce ACT. Do not route it through `predict_long`, drop tokens, reduce options, or increase the checkpoint context behind the user's frozen contract. Unit tests must spy on the inference seam to prove that state, instruction, and option overflow are rejected before a model forward call. Include exact-boundary acceptance cases and Unicode/token-heavy inputs.

## Calibration, lifecycle, and offline behavior

The pinned [model card](https://huggingface.co/convaiinnovations/laya-typed-decisions/blob/e929ae5cf69bc34259cd2f95c9e91145b818b1f0/README.md) says the checkpoint's temperatures were fitted on training examples; the notebook was corrected, but the checkpoint was not refit. It is a specialist for four synthetic workflows. Do not call its output calibrated for a user's workload or describe it as a general security classifier. Actseal's held-out empirical assessment remains necessary.

Both smoke runs emitted this upstream warning: the `choice:11+` temperature is changed from `0.10058280825614929` to `0.5`. Preserve and surface the warning even when the current question has fewer options. Record actual runtime fallback and device state; a warning must not vanish into a successful result.

The accepted adapter keeps one resident native model per spawned worker process. Synchronous Torch calls do not provide cancellable request deadlines; a thread timeout alone would leave inference running. Startup has a fixed 120-second bound. The evidence-collection protocol passes exactly 30.0 seconds for every normal request, with no CLI/environment/runner override; the low-level `DecisionModel.decide` parameter is a separate raw-capture interface. On a timeout the parent terminates, kills if necessary, and joins its worker before reporting failure; no late answer may satisfy another request. Later calls on that model object remain unavailable. The accepted assessment treats a regular Laya timeout/unavailable as `infrastructure.worker_invalidated` after complete integrity checks, retaining scheduled records as diagnostic evidence. Do not restart within an attempt, replace cases or discard failed attempts until one passes. Canonical injected faults are separate from this rule. See [ADR0008](decisions/0008-fixed-collection-deadlines.md) and [ADR0009](decisions/0009-worker-loss-invalidates-statistical-run.md); the native CLI receipt above is distinct from final release acceptance.

Separate model preparation/download from measured evaluation. Cached execution sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`; these are library settings, **not a network firewall**. Replay never imports or invokes the provider. Model loading is not included in the 60-second fixture quickstart.

## Historical upstream feasibility receipt

On 6 October 2026, the planner executed the upstream package through `uv run --no-project --python 3.12 --with 'laya==0.3.28'` from a temporary working directory. No Actseal source was run. The host reported Apple M5 Pro, 24 GiB RAM, macOS 26.6.2 arm64, Python 3.12.13. CPU threads were fixed at four.

| Check | Initial download/load | Fresh subprocess, cache and offline flags |
| --- | ---: | ---: |
| Load elapsed | 24.104 s | 1.235 s |
| One categorical inference | 0.276 s | 0.137 s |
| Process peak RSS, macOS bytes | 1,867,464,704 | 2,915,975,168 |
| Reported device / dtype | CPU / FP32 | CPU / FP32 |
| Exit status and answer | 0 / billing | 0 / identical billing answer |

The peak RSS values are whole-process measurements from `resource.getrusage`, not model weight sizes. One request establishes basic hardware/installation/cache feasibility on this host. It does not establish general accuracy, p95 latency, Linux compatibility, deterministic inference across devices, or memory bounds for arbitrary requests. Only byte-preserving replay of captured evidence has a cross-run determinism requirement. Provider benchmark claims require their own repeated protocol.

## Verified Actseal provider milestone

On **6 October 2026**, root independently reviewed and tested candidate **`17ed0875541ecfa6402991dc90e278beb2f4cc01`**. [REVIEW T30-02](../plan/reviews/T30-02.md) records **ACCEPT for the provider/normalizer milestone only**, with **full T30 PARTIAL at that time**. This is product-adapter evidence, separate from the upstream feasibility probe above.

| Check | Environment | Observed result |
| --- | --- | --- |
| Root provider/normalizer unit rerun | macOS, Python 3.12.13 | 243 passed in 4.12 s. |
| Root cached-native Actseal adapter rerun | macOS, Python 3.12.13, pinned native stack | 5 passed in 4.58 s. |
| [Linux native workflow](https://github.com/ajaysurya1221/actseal/actions/runs/37439327535) | Ubuntu, Python 3.12.3, laya 0.3.28, torch 2.14.1+cpu | 5 cached-offline product tests passed in 10.75 s. |

For Linux, the exact checkpoint revision was downloaded in a separate preparation step. Product tests then ran with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`; those library flags are not an OS network sandbox. The native command was:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya pytest -m integration tests/integration/test_laya.py
```

At the same candidate, all four ordinary Linux/macOS Python 3.12/3.13 jobs passed in [push CI](https://github.com/ajaysurya1221/actseal/actions/runs/37439252390) and [PR CI](https://github.com/ajaysurya1221/actseal/actions/runs/37439282488). These jobs do not extend native inference coverage to Python 3.13. Root also independently checked targeted lint, formatting and strict typing; [VERIFICATION](../plan/VERIFICATION.md#product-adapter-milestone--6-october-2026) preserves the receipt provenance.

The recorded times are whole test-suite elapsed times, not latency benchmarks. The milestone verifies the tested native paths without establishing broader hardware support, model accuracy, calibration or deployment reliability. The canonical fault campaign and full task subsequently passed [REVIEW T30-03](../plan/reviews/T30-03.md) at `8b1efd6314b5b65ecb51f292a5bc767ff8b93ed7`, merged as `87d2cd1`; the review preserves the earlier native receipt because its relevant source/test bytes are unchanged. The native CLI receipt above and [release report](../plan/FINAL_REPORT.md) record later integration and publication checks.

## Jev: PROVISIONAL experimental provider, explicit opt-in only

No proprietary provider is required in 1.x: the stable providers are `fixture`
and `laya`, and the zero-dependency core, assessment and replay work without
any key or account. The source also contains an **experimental** TypeSafe/Jev
cloud adapter, `actseal.experimental.providers.jev.JevModel(*, offline: bool = False)`,
PROVISIONAL under the [stability manifest](stability.md) and
[ADR 0017](decisions/0017-experimental-decision-provider.md). It may change or
be removed in any release; nothing about it is a 1.x promise, and its
inclusion in a published release remains a separate reviewed decision
(plan/v1/PLAN.md sections C and E).

Selection is always explicit; nothing routes to Jev implicitly:

- `lock` and `verify` accept it only as `--provider jev --experimental-provider`.
  Without the flag the command is a usage error (exit 3) raised before any
  provider is built, any environment variable is read or any request is
  made. The flag is rejected with `fixture` or `laya`; `replay` and `demo` do
  not accept it at all.
- `--responses` is rejected with `jev`. `--offline` is rejected by the adapter
  itself with `ProviderSetupError` (exit 3) before it reads `JEV_API_KEY`: the
  adapter has no offline mode, unlike Laya's cached-offline inference.
- From Python, `open_model("jev", responses=None, offline=False)` is the
  opt-in; the experimental module is imported only in that branch. `replay`
  never imports it, and importing `actseal.cli` or `actseal.runner` loads no
  transport.

Execution profile (fixed in the adapter; no endpoint, model, retry or
fallback option exists): `POST https://api.typesafe.ai/v1/systemone` with the
pinned `jev-1.13.0` target, Bearer authentication from **`JEV_API_KEY`**
(bring your own key; the vendor examples use a different variable name), one
attempt per request with the runner's fixed 30-second deadline as the
per-operation socket timeout, no redirect following and no fallback to another
provider. Identity is `provider=jev`, `model` and `revision` both `jev-1.13.0`,
an empty artifact-hash tuple (a cloud target has no weight hash) and a runtime
naming the endpoint and profile; the reported version is a vendor claim, not
a weight attestation, and is weaker than Laya's verified artifact hashes. The
key lives only in the private transport object and is never written into
identity, captures, evidence, locks, warnings or diagnostics. A successful body
that echoes the key, literally or behind up to three levels of JSON string
escapes, is not recorded: it is captured as `malformed_response` with warning
`jev.credential_echo`. That guard detects the key in those encodings only and
is not a general secret sanitizer; raw bodies remain data to review before
sharing.

Capture and normalization: successful bodies are read to the end of their HTTP
framing, capped at 1 MiB, and captured verbatim. The pure normalizer's Jev
profile ([schemas README](schemas/README.md)) accepts exactly
`{model, answers, usage}` with the locked question id, usage
`{input_tokens, output_tokens}` and an inner
`{type: "choice", choice, probabilities, confidence}` whose mass is within
`1e-12` of 1; a well-formed body naming another model is `identity_mismatch`
and any other shape is `malformed_response`. Status mapping: `429` ->
`rate_limit`; `529` and other `5xx` -> `unavailable`; `401`, `422`, redirects
and other statuses -> `provider_error`; a socket timeout -> `timeout`;
connection, TLS and incomplete transfers -> `unavailable`. Gating uses the
normalized selected-option probability from the returned distribution. Jev's
[Choice confidence](https://docs.typesafe.ai/confidence) is
`(max(p) - 1/n) / (1 - 1/n)`, while Laya reports a separate top-probability
`answer_confidence` and an entropy-derived `confidence`; the vendor value is
preserved as `provider_confidence` evidence only, and provider confidence
fields cannot be interchanged under a common threshold.

Verification status: **as of 7 October 2026 no live Jev request has been
accepted as evidence**; the one live audit attempt was stopped by a harness
permission denial before any key was read or request made, and no result,
journal or spend exists. Every Jev test runs over a mocked transport (a stdlib fake
connection or an injected exchange) with the key read and every socket
blocked; the shared provider conformance suite, the canonical fault campaign
and CLI/runner routing are exercised that way. Mocked behaviour is evidence
about the adapter's local handling only, not about the vendor service, its
availability, its accuracy, its cost or its account terms. Jev is not part of
the default quickstart, demo or stable provider set; a bundle collected
through it replays with the same offline normalizer and without the adapter.
Any registry entry for evidence it produces and any live audit remain
separate reviewed decisions. The [official API](https://docs.typesafe.ai/api)
uses Bearer authentication and `POST https://api.typesafe.ai/v1/systemone`
with `state`, `model`, and `questions`; responses contain `model`, `answers`,
and `usage`. [OpenAPI](https://api.typesafe.ai/openapi.json) reports API
version 0.2.0. [Model docs](https://docs.typesafe.ai/models) listed
`jev-1.13.0`, $0.042 per million input tokens, and free output tokens on
6 October 2026. Account availability was not tested.

A Jev-to-Laya fallback cannot inherit certification of Jev alone. Record both attempted identities and the reason, surface fallback use, and ESCALATE unless the entire chain has separately approved evidence. Chain certification is outside the v1.0 scope; v1.0 performs no automatic fallback, and any later certified chain would need its own reviewed sampling rule and error budget. The [TypeSafe MCA](https://typesafe.ai/legal/mca), updated 23 September 2026, permits customer application integration but restricts standalone resale and use of service/output to develop similar or competing products. Do not train the local model from Jev outputs or expose pooled credentials.
