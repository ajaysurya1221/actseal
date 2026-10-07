# REPORT 05 (isolated offline preparation)

Status: PARTIAL. Every offline deliverable of Task 05 is implemented and every
check the harness permits is green on the final commit. PARTIAL because the
original Task 05 dependencies and gates still stand: Task 03's native receipt
is permission-blocked, Task 19 registration has not happened, the 14:00 IST
7 October inclusion cut applies, no live Jev request was made, and this is a
claim until Codex reviews it. DONE is not ACCEPT. Nothing here is a shipped-Jev
claim, a compatibility-registry approval or a model-quality statement.

Executor: Claude Code, model `claude-fable-5-1`, effort high, run directly; no
subagents, nested executors, model or billing substitution. Worktree
`/Users/ajay/.codex/worktrees/actseal-v1-jev/not-yet-named`, branch
`claude/v1-05-jev-preparation`, base `212a1d6fae154dff0ea5b3b284174a53ac7f43e0`
(exact, verified with `git rev-parse HEAD` before the first edit). Python
3.12.13, uv 0.12.5, macOS 26.6.2 arm64. Nothing pushed, merged, tagged or
released. No `.env` read, no real key read, no live request, no network in any
test, no runtime dependency added, no personal-memory access, no native
integration, mutation harness, authoring download or visual preview.

## Commits (base..HEAD, oldest first)

| Commit | Subject |
|---|---|
| `f7439f51143cea39c9cbb17e8b24fac8a7ec83a2` | feat(providers): admit experimental jev identity with pure profile and runner guard (V1-011) |
| `7af39829e15e68883dd13275c3647714fed81577` | test(core): replace three further jev-as-unsupported sentinels (outside V1-011's enumerated set) |
| `31b8bdf4169da02e70d807f9fe212f9df3f3d581` | docs(schemas): admit jev in every ModelIdentity provider enum and describe the profile |
| `765e1d8f20ab2df9760b90c8c166ea9d7c22f6d2` | feat(experimental): add stdlib Jev adapter with fixed endpoint, one attempt and bounded capture |
| `34c62811eb6a14906249611cc4b1e42a386478c6` | test(conformance): run the shared provider contract against mocked Jev |

Commit `f7439f5` alone leaves three tests red (the sentinels fixed in
`7af3982`, see Deviations); every later commit is green. No commit routes an
admitted provider to Laya: the `open_model` guard lands in the same commit as
the `PROVIDERS` admission.

Working-tree implementation fingerprint at HEAD:
`6f00a763047146bd0bf13017f6dc4a71e67d1697215a7f6567a7ae4cd78e0c2e` (changed
from the base because new source files exist; the packaged registry is still
empty and no registry approval is requested).

## Changes

### Shared files (exact V1-011 / V1-021 set)

- `src/actseal/records.py`: `PROVIDERS = frozenset({"fixture", "laya", "jev"})`
  with a comment that admission is not runner/CLI registration. No other
  field, validator, constant or signature changed.
- `src/actseal/normalization.py`: pure Jev profile only. Module-private
  `_JEV_MODEL = "jev-1.13.0"` and `_JEV_MASS_TOLERANCE = 1e-12`;
  `_jev_inner_answer` validates, in order: body is an object; keys exactly
  `{model, answers, usage}`; `model` is a string; `answers` holds exactly the
  locked question id; `usage` keys exactly `{input_tokens, output_tokens}`
  with nonnegative non-boolean integers; then `model == "jev-1.13.0"`, else
  `identity_mismatch` with warning `normalize.answering_model`. The shared
  `_answer` gained keyword-only `required`/`optional` key sets (defaults
  unchanged for fixture/Laya); Jev requires exactly `{type, choice,
  probabilities, confidence}` with no optional field. `normalize` dispatches
  `laya` / `jev` / fixture; fixture and Laya behaviour, tolerances, warnings and
  `__all__` are unchanged. Docstring documents the profile.
- `src/actseal/faults.py`: for a `jev` identity the three answer-shaped faults
  add `confidence: 1.0` (the vendor Choice confidence of a one-hot
  distribution) and wrap in `{model: "jev-1.13.0", answers: {qid: answer},
  usage: {input_tokens: 0, output_tokens: 0}}`. Scenario ids, order, state
  literal, transport faults, the `{` body and dispositions are unchanged; the
  `low_confidence` fault therefore carries vendor confidence 1.0 while its
  selected probability is 0.0 and still ABSTAINs. Imports `_JEV_MODEL` from
  normalization; no adapter/transport import.
- `src/actseal/runner.py`: private `_REGISTERED_PROVIDERS = {"fixture",
  "laya"}`; `open_model` raises `SchemaError("provider: unsupported value")`
  for a value outside `PROVIDERS` and `SchemaError("provider: admitted for
  records but not registered with the runner")` for an admitted but
  unregistered provider, before any adapter import. The Laya branch is
  otherwise byte-identical. `verify_run`'s unsupported-provider message
  changed from "must be fixture or laya" to "unsupported value" (wording only;
  it still starts with `provider`). No signature, constant or protocol change.
- `docs/stability.md`: only the `actseal.records` constant row now describes
  `PROVIDERS` as the admitted serialized set `{fixture, laya, jev}` with
  `fixture`/`laya` the stable CLI choices and `jev` the PROVISIONAL adapter's
  identity provider.
- `docs/schemas/{lock,captured-outcome,decision-record,fault-result,cli-receipt}.schema.json`:
  the `ModelIdentity.provider` enum is `["fixture", "laya", "jev"]` in all
  five, changed atomically in one commit. No version, field or other rule
  changed.
- `docs/schemas/README.md`: the CapturedOutcome invariant now names `jev`,
  states the five enums are updated atomically, describes the cloud identity
  (empty artifact hashes, vendor-claimed version, no CLI registration) and
  adds a short "Jev body profile (PROVISIONAL)" paragraph. No other section
  touched. **Integration note:** this base lacks Task 09's release-receipt
  schema-index additions to the same README; those must be preserved when
  integrating (Task 09's shared-file writes have ended; mine touch only the
  CapturedOutcome paragraph and the new paragraph after it).
- `tests/unit/test_stability.py`: only the exact set assertion, now
  `{"fixture", "laya", "jev"}`, with a comment.
- Sentinels (V1-011 enumerated): `tests/unit/test_records.py` ("Identity
  unknown provider" now uses `"unsupported"`), `tests/unit/test_normalization.py`
  (`test_unsupported_expected_provider_is_a_schema_error` uses
  `"unsupported"`), `tests/unit/test_runner.py` (`verify_run(provider=
  "unsupported")`; `open_model("unsupported", ...)` added while the
  `open_model("jev", ...)` rejection is kept and strengthened).

### Owned product files

- `src/actseal/experimental/__init__.py`, `src/actseal/experimental/providers/__init__.py`:
  PROVISIONAL package markers; import nothing.
- `src/actseal/experimental/providers/jev.py` (new, 350 lines): `JevModel(*,
  offline=False)` implementing `DecisionModel`. Constants `MODEL = REVISION =
  "jev-1.13.0"` (bound to the normalizer's `_JEV_MODEL`), `ENDPOINT_HOST =
  "api.typesafe.ai"`, `ENDPOINT_PATH = "/v1/systemone"`, `API_KEY_ENV =
  "JEV_API_KEY"`, `ADAPTER_VERSION = "1"`, `EXECUTION_PROFILE =
  "jev-cloud-single-attempt-v1"`, `MAX_RESPONSE_BYTES = 1 MiB`.
  `request_body(request) -> bytes` builds exactly `{state, model, questions:
  {qid: {type: "choice", instructions, criteria}}}` with `json.dumps` in
  insertion order (criteria in locked option order; never `canonical_json`).
  Transport: `http.client.HTTPSConnection(ENDPOINT_HOST, timeout=timeout_s,
  context=ssl.create_default_context())`, one `POST` per `decide`, headers
  exactly `Authorization: Bearer <key>`, `Content-Type: application/json`,
  `Accept: application/json`; connection closed in `finally` on every path.
  Status mapping: explicit table `{401: provider_error, 422: provider_error,
  429: rate_limit, 529: unavailable}`; otherwise `5xx -> unavailable`, any
  other non-200 (including every 3xx redirect, which is never followed, and
  non-200 2xx) `-> provider_error`; warning `jev.http:<status>`; error bodies
  are never read. `TimeoutError` (socket timeout at any stage) `-> timeout`
  with no warning; `OSError`/`ssl` /`http.client.HTTPException` `->
  unavailable` with `jev.transport:<Class>`; any other `Exception` `->
  provider_error` with `jev.exception:<Class>`; `BaseException` propagates.
  Success: `read(MAX_RESPONSE_BYTES + 1)` bounds actual bytes (not
  Content-Length); more is `malformed_response` + `jev.body_oversized`;
  invalid UTF-8 is `malformed_response` + `jev.body_not_utf8`; otherwise the
  decoded text is the capture's `body_json` byte for byte (invalid JSON,
  duplicate keys, wrong model and extra fields included). Setup: `offline=True`
  reads no environment and every `decide` is `unavailable`
  (`jev.unavailable:offline`); otherwise `JEV_API_KEY` must be a nonempty
  printable ASCII token without whitespace and at most 4096 characters, else
  `ProviderSetupError("JEV_API_KEY: ...")` without echoing the value. The key
  exists only in the exchange's header mapping. Identity is built once at
  construction: `("jev", "jev-1.13.0", "jev-1.13.0", (), "1", "1", runtime)`
  with runtime `endpoint`, `execution_profile`, `python` (interpreter
  version), `transport = stdlib-http.client-tls`, `weights_attested = false`;
  it is never mutated by a response. `close` is idempotent; afterwards
  `decide` is `unavailable` (`jev.unavailable:closed`) with no request. A
  later request after a timeout is a new attempt on a new connection, never
  a retry of the timed-out one. Test seam: `JevModel._with_exchange(exchange)`
  injects the exchange callable; the production `_HttpsExchange(api_key,
  connect)` itself takes an injectable connection factory, so tests drive the
  real request/header/read/close code over a stdlib fake connection.

### Owned tests

- `tests/unit/test_jev.py` (new, 80 collected tests): profile constants;
  identity shape (empty artifact hashes, fixed runtime, round trip, unchanged
  after close and after a wrong-model response); offline setup reads no
  environment and sends nothing; eight missing/malformed key cases raise
  `ProviderSetupError` naming only the variable; the default transport is an
  `HTTPSConnection` to the fixed host/port 443 and, under the conftest socket
  block with a mocked key, the attempt becomes bounded `provider_error` data
  (`jev.exception:_NetworkBlockedError`) rather than an exception; the TLS
  default context verifies certificates; exact request bytes, key order,
  criteria order (non-alphabetical options), inequality with `canonical_json`,
  no `case_id`/`expected_label` on the wire; exactly one POST with the fixed
  headers, the requested timeout, one bounded read and one close; case id
  changes the capture hash but not the HTTP body; gold label changes neither
  the request nor the body while every option's text stays in `criteria`;
  byte-exact preservation of eight raw bodies (non-canonical, whitespace,
  truncated JSON, empty, duplicate keys, Unicode plus NUL, multibyte, exactly
  1 MiB) plus codec round trip; a non-canonical valid body normalizes to the
  selected label with vendor confidence kept diagnostic and ACTs under the
  sample policy; nine captured-body classifications (invalid JSON, duplicate
  keys, wrong question, wrong model -> `identity_mismatch`, unknown choice ->
  DENY, option mismatch, Laya-style rounding rejected, usage shape, extra
  answer field); selected probability 0.0 with vendor confidence 0.99 ->
  ABSTAIN; the sixteen-status mapping with error bodies never read or
  retained; timeout at connect/request/response/read stages followed by a
  healthy second case on a new connection; nine connection/TLS/protocol error
  classes at four stages -> `unavailable`; unexpected `ValueError` ->
  `provider_error`, `KeyboardInterrupt` propagates; oversized body after a
  bounded read; three invalid-UTF-8 bodies; a scripted unknown failure code is
  rejected by the record; every shared invalid timeout and non-request raises
  before any connection; idempotent close; credential hygiene across
  captures, identities, reprs and error text; a mocked "recorded" Jev bundle
  (three records through the real adapter seam, six Jev canonical faults,
  real assessment) validates against every published schema with byte-exact
  bodies in `records.jsonl`; the same bundle replays in a fresh `-I` child
  with sockets blocked and `actseal.experimental`, `actseal.adapters`,
  `http`, `ssl`, `urllib` imports forbidden, reproducing the verdict, and a
  tampered recorded body turns that replay into ERROR; wire-codec round trip
  of recorded captures re-normalizes identically; importing the adapter in a
  fresh child with sockets, `Popen` and `JEV_API_KEY` reads blocked loads no
  native root and constructs an offline model.
- `tests/unit/test_normalization.py` (+22 tests): Jev profile constants are
  private and frozen; envelope normalizes with selected-label gating; wrong
  answering model (five strings) -> `identity_mismatch` with
  `normalize.answering_model`; shape is checked before the model string and
  the model string before the answer; 21 envelope violations and 13 answer
  violations -> `malformed_response` with the named warning; every profile
  field required; 1e-12 boundary inside/outside; unknown choice; identity
  before envelope; the three profiles reject each other's envelopes; capture
  warnings precede normalization warnings; normalization and faults import no
  experimental, adapter, `http.client` or `ssl` module in a fresh `-I` child.
- `tests/unit/test_faults.py`: Jev identity added to the existing provider
  parametrization (all existing campaign assertions now also run for `jev`);
  new tests for the exact Jev envelopes with `confidence: 1.0`, the
  low-confidence ABSTAIN despite confidence 1.0, offline round-trip
  rederivation of all six results, twelve envelope defects (two
  `identity_mismatch`, ten `malformed_response`, all ESCALATE), and mutual
  rejection of Laya/Jev envelopes.
- `tests/unit/test_runner.py`: `jev` against a fixture lock is
  `IntegrityError` before the factory; `open_model("jev", ...)` with every
  `responses`/`offline` combination raises `SchemaError` mentioning
  `provider` and "not registered" with zero Laya constructions (monkeypatched
  recorder) and `_REGISTERED_PROVIDERS == {fixture, laya}`; a fresh `-I`
  child with a meta-path finder that raises on any `actseal.adapters.*` or
  `actseal.experimental*` import rejects `open_model("jev", ...)` for both
  `offline` values and loads no adapter.
- `tests/provider_support.py`: `ProviderProfile.evidence_only_fields`;
  `IGNORED_ANSWER_FIELDS = ("action", "answer_confidence")` declared by the
  fixture and Laya profiles; stdlib fake Jev connection/factory; `JevProfile`
  (`jev-fake`): success bodies travel through the real `_HttpsExchange` and
  bounded reader over the fake connection (byte-verbatim), failure codes are
  injected at the exchange seam (the Laya double does the same at the worker
  reply), `after_close = unavailable`, `after_timeout = usable`,
  `load_warnings = ()`, `evidence_only_fields = ("usage", "input_tokens",
  "output_tokens")`, `requests_sent` counts attempts, `worker_alive` reports
  the open/closed transport (documented stand-in; Jev has no worker).
  `PROFILE_NAMES = ("fixture", "laya-fake", "jev-fake")`.
- `tests/conformance/test_provider_contract.py`: coverage test renamed to
  `test_profiles_cover_fixture_laya_and_experimental_jev` with the
  three-name tuple; the raw-body case asserts every profile-declared
  evidence-only field survives instead of the two literal fixture/Laya field
  names. All other cases unchanged; 85 conformance tests now collect (was 63).
- `tests/conformance/test_provider_isolation.py`: the child blocks sockets
  with a `socket.socket` subclass (a plain function broke `ssl`'s
  `class SSLSocket(socket)` at import), forbids `os.environ.get("JEV_API_KEY")`,
  imports `actseal.experimental(.providers.jev)`, and proves an offline
  `JevModel` captures `unavailable` with `jev.unavailable:offline` and the
  same request digest as the fixture capture; `jev.py` resolves to this
  checkout. Existing assertions kept.
- `tests/conformance/test_provider_doubles.py`: untouched (hash unchanged).

### Not changed

`tests/integration/test_laya.py`, REPORT 03, `docs/providers.md` (Task 08;
still says Jev is deferred), CLI (`--provider` choices remain fixture/laya;
`tests/unit/test_cli.py` and `test_schema_validation.py` still use `jev` as
an invalid CLI choice, which stays correct until Task 19), policy, statistics,
assessment, evidence, replay, compatibility registry, `pyproject.toml`,
`uv.lock`, `.env.example` (see Deviations), any ADR.

### Final owned-file SHA-256

```text
src/actseal/experimental/__init__.py: bf1eeac7e5a0322e74dc06a6b2c30ccad075d8dee364438d46485f206f91ac66
src/actseal/experimental/providers/__init__.py: 279804f9ae6655d7b32a547feec1d15f2f3397f8b637c0e6e3e678561f3039fe
src/actseal/experimental/providers/jev.py: 2ff7affe4976cb721854da7c2c1d09f024d8dd5ff1bf87074d87e02877a2b793
src/actseal/records.py: 0b7e8cb1aab52dc796416fd858e2d39f9f3a41fabd527a4388cb3cb6e85b9818
src/actseal/normalization.py: cc86d019b78544eb52b15d75d29d619d9a062441254a1e6b9748be6222f18445
src/actseal/faults.py: 678d09499931b89957c422a8c2dac43ec41720200c4a71ea295731e5d08ee3ae
src/actseal/runner.py: af8474993373b51db9607f0decc5be29260d04f09a2f920cadf9ad9f4c4fbd52
tests/unit/test_jev.py: 33882189ab63a812bad917741658688113c0f674a5bbffa94d8ecff191470812
tests/unit/test_normalization.py: 158ac9671a799acd52b1a216365d10d47e9b94d1080fa3ae78b0f84f5b9f5ffe
tests/unit/test_faults.py: 80168cc06741b13acb55f69ceee5c01b23d5d8cb7b0ea2ecee8a834ec28a30c4
tests/unit/test_runner.py: 373afa5ade289c5e67746af65f1789b1b9f96f1ad5a97de6ae1944db502f1ca6
tests/unit/test_records.py: ca221235c19d9107155b3ee7fcdcd473367bc8ed057ab6b284679d5d726c1616
tests/unit/test_stability.py: 0716135b4f05fcfa22ed4c997d00f614a210379afa049690e958b4c660952603
tests/unit/test_locking.py: 6c46af8f7b7bf97a4076e89390bd031a7eb30db452b05a0831721737a93f416a
tests/unit/test_replay.py: cf87db05e124cdc3803a9b97485bc02175a346283f411e65c65cb09e10ba14b9
tests/unit/test_serialization.py: 61a29ed50379e18149f0907f3218c9a32dd227f597b50b055b883f8c5b1da3d9
tests/provider_support.py: a112804f7e9be0b43e684fe36ebb9bf4cd68dc627c6a6d009d40fa5b90e5aa6d
tests/conformance/test_provider_contract.py: 209bc166c26f77f7082db1bc899a7301fcf653a7d8a18fdd4a202b3397205ec8
tests/conformance/test_provider_isolation.py: 598d36d0a01c1480225df137a67a8cf7a01d9ac20264cef75c9480ac383108b5
tests/conformance/test_provider_doubles.py: 781b803c378f03e31e48aa473347077399566cdd9a02a9a36214329f17715e95
docs/stability.md: 6f847b9b908f2b9f53e6d8d6c461aac2676989a80e4c0a6def4c564d307445eb
docs/schemas/README.md: 1a62182e6547feb6062451aec35eaeb230d6c20da80252480572dc66658dd3d6
docs/schemas/lock.schema.json: c2a251faf34003e068dc87f1f32d20bfbece5ccafeb4a60e2f621701fb7bc2f7
docs/schemas/captured-outcome.schema.json: b3a7ffe84d3a8b07256c079a14415fc5f23df6a480c022730bb54e6fe8920e41
docs/schemas/decision-record.schema.json: 36c069b8ff00147ba3301b22257a2a68254245265afdf061e418ce2d777a694b
docs/schemas/fault-result.schema.json: 619e628a11a3aacfe38e8b015f83d135da37a3c4a2fc93bfa3bf9b65d96cd505
docs/schemas/cli-receipt.schema.json: 6b5f05017ef268f59af4e56c7cf8a1ce6785d99e33dd869ba15de2c727f448d8
```

## Tests (7 October 2026, from the worktree, on HEAD `34c6281`)

| Command | Exit | Result |
|---|---|---|
| `uv run --frozen pytest tests/conformance tests/unit/test_jev.py tests/unit/test_normalization.py` | 0 | 347 passed in 1.20 s (85 conformance = 67 contract + 17 doubles + 1 isolation; 80 Jev; 182 normalization) |
| `uv run --frozen pre-commit run --all-files` | 0 | ruff check, ruff format --check, mypy --strict all Passed |
| `uv run --frozen pytest -m "not integration and not packaging" -q -p no:cacheprovider` | 0 | 2958 passed, 1 skipped, 20 deselected in 53.49 s (rerun 54.16 s). The skip is the pre-existing visual-lane `tests/visual/test_outline.py` fontTools import skip, unrelated to this task. Baseline before edits for the directly affected files was 622 passed. |
| `uv run --frozen ruff check src tests` | 0 | All checks passed |
| `uv run --frozen ruff format --check src tests` | 0 | 64 files already formatted |
| `uv run --frozen mypy --strict src/actseal tests` | 0 | Success: no issues found |
| `git diff --check` | 0 | clean |
| `uv run --frozen pytest tests/unit/test_jev.py tests/unit/test_normalization.py tests/unit/test_faults.py tests/unit/test_runner.py tests/conformance --co` | 0 | 450 tests collected |

Exit codes above were observed through the tool's success/failure status;
the pytest durations are pytest's own reported times. No other tool-reported
session or elapsed-time figure is available, so none is claimed.

Not run: `uv run --frozen pytest -m packaging` (outside this task's Done-when;
builds distributions), the native integration command (Task 03's
permission-blocked receipt; not retried, not substituted), any live Jev call.

Intermediate failures during development, all fixed before the listed runs:
three sentinel tests outside the enumerated set (see Deviations); E501/UP012/
PT018/SIM300 lint findings and formatter diffs in the new tests; a fresh-child
isolation test initially listed `urllib.parse` as loaded (it is pulled in by
the interpreter, not by actseal; the assertion was narrowed to experimental,
adapters, `http.client` and `ssl`); replacing `socket.socket` with a function
broke `ssl` import under the Jev adapter (fixed with a `socket.socket`
subclass in both isolation children); `monkeypatch.setenv` rejects a NUL byte
(the case became an ESC control character); mypy rejected `Script(**dict)` and
`RemoteDisconnected()` without its argument.

## Deviations

1. **`.env.example` not edited.** The Read tool call on `.env.example` was
   denied by the permission settings ("directory denied"). I did not retry it
   through Bash or any other tool. The `JEV_API_KEY` placeholder line the task
   lists is therefore missing; the name is already documented in
   `docs/providers.md` and ADR 0004. Codex or a permitted session must add the
   line (name and placeholder only).
2. **Three sentinel replacements beyond the enumerated three** (commit
   `7af3982`): `tests/unit/test_locking.py:747`, `tests/unit/test_replay.py:286`
   and `tests/unit/test_serialization.py:706` also used `"jev"` as an
   unsupported provider and fail once it is admitted. Each change is the single
   literal `"jev"` -> `"unsupported"`; expected errors and assertions are
   unchanged. These files belong to the core lane; the commit is separate so
   Codex can ratify or revert it. Without it the suite is red by exactly those
   three tests.
3. **Shared conformance assertion generalized**, not weakened: the two literal
   `'"action"'`/`'"answer_confidence"'` assertions in
   `test_raw_body_is_preserved_without_repair_and_normalizes` became a loop
   over profile-declared `evidence_only_fields` (fixture/Laya declare exactly
   those two; Jev declares `usage`/`input_tokens`/`output_tokens`, which the
   normalizer validates for shape but never uses). The exact Jev answer
   profile has no ignored field, so the literal assertions could not hold for
   it without admitting out-of-profile fields. Every negative double still
   fails the same checks (`test_provider_doubles.py` is byte-identical).
4. **Private profile constants.** `_JEV_MODEL`/`_JEV_MASS_TOLERANCE` live in
   `normalization.py` without `__all__` entries and are imported by
   `faults.py` and the experimental adapter. Exporting them would change the
   frozen `__all__` and the stability manifest's exact export sets, which this
   task does not own; the adapter re-exposes them as `MODEL`/`REVISION`.
5. **Status-mapping fallbacks beyond the supplement's list** (needs review
   before any collection): other `5xx` -> `unavailable`; any other non-200
   status, including every `3xx` and non-200 `2xx`, -> `provider_error`. The
   listed codes (401/422/redirect/429/529/timeout/oversized/invalid UTF-8) are
   implemented exactly as specified.
6. **Missing key raises `ProviderSetupError`; offline returns `unavailable`
   captures.** Both make zero requests as required; I read "reject
   missing-key setup" as a setup error that stops a run, and "offline" as a
   constructible model (identity observable, no transport) so a Jev lock can
   be sealed without a key. Codex may prefer a different split.
7. **Frozen-profile readings that need confirmation against the live API:**
   the inner answer requires `confidence` (the supplement lists it without an
   optional marker) and forbids any other key; `usage` must be exactly
   `{input_tokens, output_tokens}`; the envelope must be exactly
   `{model, answers, usage}` (so a response carrying, for example, an API
   `metadata` field is `malformed_response`). The supplement says
   out-of-profile data is malformed and the profile is frozen before
   collection; if the live shape differs, the profile must be amended and
   reviewed before any call, not adapted afterwards.
8. **Identity runtime includes the interpreter version** (as Laya's does), so
   a Jev lock is bound to the Python minor version that sealed it.
9. **After a socket timeout the model stays usable**: the next case is a new
   attempt on a new connection. The timed-out request itself is never
   retried. (Laya differs because its worker is terminated.)
10. **ADR 0009 interaction, not changed:** `assessment._worker_invalidated`
    applies only to the Laya provider, so a Jev `timeout`/`unavailable`
    capture is an ordinary ESCALATE record and does not make the run ERROR.
    Statistical code is frozen; flagging the semantics for the audit design.
11. **Formatter use:** the project formatter was run once, on the newly
    authored `tests/unit/test_jev.py` only (`uv run --frozen ruff format
    tests/unit/test_jev.py`); every other file was edited with the dedicated
    tools. No other shell editing.
12. **Denied shell command, not retried:** one Bash `for` loop with a variable
    expansion (to grep five schema files) was auto-denied; the earlier
    dedicated-search results were used instead and the schemas were edited one
    by one. The owned-file hashes above were computed with one
    `uv run --frozen python -c` call using `hashlib` as the first and only
    attempt; no hash command was denied and none was rerouted. Codex supplies
    packet hashes independently.

## Unverified live behavior (no live request was made)

- Whether the live `200` body matches the frozen profile exactly: presence of
  `confidence`, exact `usage` keys, no extra envelope fields, `model` echoed
  as `jev-1.13.0`, probability key set equal to the submitted criteria.
- Actual status codes and bodies for authentication, validation, rate-limit
  and overload conditions, and whether the service ever redirects.
- TLS verification with the uv-managed CPython's default certificate store on
  this host; server certificate and hostname.
- Latency relative to the fixed 30.0 s collection deadline, actual rate limits,
  response sizes (chunked or not), token usage and credit consumption.
- Vendor rounding of probabilities; the 1e-12 mass restriction is an Actseal
  choice and may reject live responses, which would be visible as
  `malformed_response`, never adjusted after the fact.
- Account availability and terms interpretation (BYOK customer integration).

## Open issues

- Codex: ratify or revert commit `7af3982` (deviation 2); add the
  `.env.example` line (deviation 1); confirm or amend deviations 5 to 10 before
  any collection; confirm the schema README integration order with Task 09's
  additions.
- Task 19 owns experimental CLI/runner registration
  (`--provider jev --experimental-provider`); until then `open_model("jev")`
  fails loudly and the CLI never offers `jev`.
- `docs/providers.md` and `docs/threat-model.md` still describe Jev as
  deferred; Task 08 must not describe this adapter as shipped before its
  inclusion gate.
- Task 03's native receipt remains permission-blocked; this branch does not
  touch native tests.
- The implementation fingerprint changed; no registry approval is requested
  or implied.

## Spend

API/credits: USD 0 and zero Jev requests (no key read, no connection opened;
every transport test ran over a fake connection or hit the test socket block).
Subscription: Claude Code subscription session only; no meter or elapsed-time
figure was reported by the tooling, so the subscription estimate is unknown
and is not invented. No model download, no native inference, no CI run
triggered.
