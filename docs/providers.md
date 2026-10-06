# Providers: native Laya reference and normalization

Status: implementation contract and verified upstream feasibility, 6 October 2026. The upstream smoke described here is complete; it does not imply that Actseal's adapter has been implemented or accepted. [Frozen contracts](../plan/CONTRACTS.md) govern the product boundary.

## Reference runtime

The v1 live-model path uses the optional Laya dependency. The fixture quickstart and evidence replay require no model or credentials. The reference is one categorical question, one explicitly selected checkpoint, CPU FP32, four Torch threads, and eager inference. Automatic model routing, MLX conversion, quantization, compilation, and alternate device promotion are outside this reference.

Verified upstream calls:

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

Keep one resident native model per spawned worker process. Synchronous Torch calls do not provide cancellable request deadlines; a thread timeout leaves inference running. Initialize the model once, signal readiness within the frozen 120-second startup limit, serialize requests over a data-only channel, and let the parent enforce a finite positive request deadline (default 30 seconds). On a timeout the parent terminates, kills if necessary, and joins its own worker before reporting failure; no late answer may satisfy another request. Later calls on that model object return unavailable; recovery requires a new model object. Do not claim this lifecycle has been implemented merely because native inference passed the smoke.

Separate model preparation/download from measured evaluation. Cached execution sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`; these are library settings, **not a network firewall**. Replay never imports or invokes the provider. Model loading is not included in the 60-second fixture quickstart.

## Verification receipt

On 6 October 2026, the planner executed the upstream package through `uv run --no-project --python 3.12 --with 'laya==0.3.28'` from a temporary working directory. No Actseal source was run. The host reported Apple M5 Pro, 24 GiB RAM, macOS 26.6.2 arm64, Python 3.12.13. CPU threads were fixed at four.

| Check | Initial download/load | Fresh subprocess, cache and offline flags |
| --- | ---: | ---: |
| Load elapsed | 24.104 s | 1.235 s |
| One categorical inference | 0.276 s | 0.137 s |
| Process peak RSS, macOS bytes | 1,867,464,704 | 2,915,975,168 |
| Reported device / dtype | CPU / FP32 | CPU / FP32 |
| Exit status and answer | 0 / billing | 0 / identical billing answer |

The peak RSS values are whole-process measurements from `resource.getrusage`, not model weight sizes. One request establishes basic hardware/installation/cache feasibility on this host. It does not establish general accuracy, p95 latency, Linux compatibility, deterministic inference across devices, or memory bounds for arbitrary requests. Only byte-preserving replay of captured evidence has a cross-run determinism requirement. Provider benchmark claims require their own repeated protocol.

## Jev: optional and deferred to v2

No proprietary provider is required in v1. The future TypeSafe/Jev adapter reads **`JEV_API_KEY`**, despite the vendor examples' different variable name. It must never serialize credentials into requests-at-rest, evidence, logs, or locks.

The [official API](https://docs.typesafe.ai/api) uses Bearer authentication and `POST https://api.typesafe.ai/v1/systemone` with `state`, `model`, and `questions`; responses contain `model`, `answers`, and `usage`. [OpenAPI](https://api.typesafe.ai/openapi.json) reports API version 0.2.0. [Model docs](https://docs.typesafe.ai/models) listed `jev-1.13.0`, $0.042 per million input tokens, and free output tokens on 6 October 2026. Account availability was not tested.

Jev's [Choice confidence](https://docs.typesafe.ai/confidence) is `(max(p) - 1/n) / (1 - 1/n)`, while Laya reports a separate top-probability `answer_confidence` and an entropy-derived `confidence`. Provider confidence fields cannot be interchanged under a common threshold. The future adapter must expose explicitly named normalized scores and preserve raw fields.

A Jev-to-Laya fallback cannot inherit certification of Jev alone. Record both attempted identities and the reason, surface fallback use, and ESCALATE unless the entire chain has separately approved evidence. Chain certification is outside v1. The [TypeSafe MCA](https://typesafe.ai/legal/mca), updated 23 September 2026, permits customer application integration but restricts standalone resale and use of service/output to develop similar or competing products. Do not train the local model from Jev outputs or expose pooled credentials.
