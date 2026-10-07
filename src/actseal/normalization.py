"""Pure response normalization: identity first, exact schema, bounded tolerance.

This module turns a :class:`CapturedOutcome` into a :class:`ChoiceAnswer` or a
:class:`ProviderFailure` without importing any provider, model or client
library. Replay and assessment call it on recorded data exactly as the live
runner did. It depends only on ``records``, ``errors`` and ``serialization``.

Order of checks (plan/CONTRACTS.md section 4, docs/providers.md):

1. The observed identity must equal the expected identity before any response
   field is trusted. A difference is ``identity_mismatch``.
2. A transport failure code passes through unchanged.
3. The raw body must be strict JSON. Dispatch on ``expected_identity.provider``:
   ``fixture`` bodies are inner answer objects; ``laya`` bodies are the entire
   native envelope whose generic marker, requested answer id and usage
   diagnostics are validated before the inner answer is extracted; ``jev``
   bodies are the entire HTTP response object of the experimental cloud
   adapter (plan/v1/CHANGE_LOG.md V1-011), validated by the frozen profile
   below.
4. The inner answer must be ``type='choice'`` with a string choice. An unknown
   choice is ``unknown_choice``. Probabilities must cover exactly the declared
   labels with finite non-boolean numbers in [0, 1] and a positive total within
   the provider's tolerance. Mass is renormalized by the observed total and the
   gate value is the normalized probability of the provider's *selected* label.

Provider ``confidence`` is preserved as ``provider_confidence``; native
``action`` metadata is accepted only as an object and otherwise ignored. Nothing
here authorizes an action; that is the policy evaluator's job.

Jev profile (PROVISIONAL, frozen before any live collection). The body is
exactly ``{model, answers, usage}``. ``model`` must be a string; ``answers`` must
hold exactly the requested question id; ``usage`` must be exactly
``{input_tokens, output_tokens}`` with nonnegative non-boolean integers. Only
after that shape check is the answering model compared with the pinned
``jev-1.13.0``: a different string is ``identity_mismatch`` (a vendor-reported
version claim that does not match the locked target), never an argmax or
tolerance adjustment. The inner answer is exactly ``{type, choice,
probabilities, confidence}``; its mass tolerance is the Actseal restriction
``1e-12``, which is not a verified vendor rounding claim. Any out-of-profile
field or type is ``malformed_response``. The vendor ``confidence`` is kept as
diagnostic ``provider_confidence`` and never gates an action.

Warnings are bounded codes (``normalize.<check>``) appended after the capture's
own warnings. They never echo body text.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Final

from actseal.errors import SchemaError
from actseal.records import (
    MAX_OPTIONS,
    CapturedOutcome,
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionRequest,
    ModelIdentity,
    Outcome,
    ProviderFailure,
)
from actseal.serialization import canonical_json, sha256_bytes, strict_json_loads, to_data

__all__ = [
    "FIXTURE_MASS_TOLERANCE",
    "LAYA_MASS_TOLERANCE_PER_OPTION",
    "LAYA_MODEL_MARKER",
    "NORMALIZER_VERSION",
    "laya_mass_tolerance",
    "normalize",
    "request_sha256",
]

NORMALIZER_VERSION: Final = "1"
FIXTURE_MASS_TOLERANCE: Final = 1e-12
LAYA_MASS_TOLERANCE_PER_OPTION: Final = 0.00005
LAYA_MODEL_MARKER: Final = "laya-rl-agent"
#: Experimental Jev profile (PROVISIONAL; not part of the stable manifest). The
#: pinned vendor target every Jev response must report, and the explicit
#: Actseal mass restriction for that profile. Shared with ``actseal.faults`` and
#: the experimental adapter so the strings exist exactly once.
_JEV_MODEL: Final = "jev-1.13.0"
_JEV_MASS_TOLERANCE: Final = 1e-12

_ANSWER_REQUIRED: Final[frozenset[str]] = frozenset({"type", "choice", "probabilities"})
_ANSWER_OPTIONAL: Final[frozenset[str]] = frozenset({"confidence", "answer_confidence", "action"})
_JEV_ANSWER_REQUIRED: Final[frozenset[str]] = frozenset(
    {"type", "choice", "probabilities", "confidence"}
)
_JEV_USAGE_KEYS: Final[frozenset[str]] = frozenset({"input_tokens", "output_tokens"})
_ENVELOPE_KEYS: Final[frozenset[str]] = frozenset({"model", "answers", "usage"})
_USAGE_COUNTS: Final[tuple[str, ...]] = (
    "input_tokens",
    "output_tokens",
    "state_tokens",
    "state_tokens_dropped",
)
_USAGE_REQUIRED: Final[frozenset[str]] = frozenset(
    {*_USAGE_COUNTS, "truncated", "truncated_questions"}
)
_USAGE_OPTIONAL: Final[frozenset[str]] = frozenset({"options"})
_OPTIONS_KEYS: Final[frozenset[str]] = frozenset({"total", "distinct", "tokens_per_option"})


def laya_mass_tolerance(option_count: int) -> float:
    """Absolute tolerance on the raw probability total for the pinned Laya adapter.

    Laya serializes four-decimal rounded probabilities, so the total of ``n``
    options may deviate from 1 by up to ``0.00005 * n`` plus floating slack.
    """
    if type(option_count) is not int or not 1 <= option_count <= MAX_OPTIONS:
        raise SchemaError(f"option_count: must be an integer in [1, {MAX_OPTIONS}]")
    return LAYA_MASS_TOLERANCE_PER_OPTION * option_count + FIXTURE_MASS_TOLERANCE


def request_sha256(request: DecisionRequest) -> str:
    """Canonical SHA256 of a serialized request; the value adapters record in captures."""
    return sha256_bytes(canonical_json(to_data(request)))


class _RejectedError(Exception):
    """Internal control flow: the body violates the contract (never escapes ``normalize``)."""

    def __init__(self, code: str, warning: str) -> None:
        super().__init__(code)
        self.code = code
        self.warning = warning


def _malformed(check: str) -> _RejectedError:
    return _RejectedError("malformed_response", f"normalize.{check}")


def _unit_interval(value: object, check: str) -> float:
    if type(value) is bool or not isinstance(value, int | float):
        raise _malformed(check)
    try:
        number = float(value)
    except OverflowError:
        raise _malformed(check) from None
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise _malformed(check)
    return number


def _count(value: object, check: str) -> int:
    if type(value) is not int or value < 0:
        raise _malformed(check)
    return value


def _mapping(value: object, check: str) -> Mapping[str, object]:
    if type(value) is not dict:
        raise _malformed(check)
    return value


# --------------------------------------------------------------------------- #
# Laya envelope
# --------------------------------------------------------------------------- #


def _validate_options(value: object) -> bool:
    """Validate ``usage.options``; return whether it names any collapsed question."""
    options = _mapping(value, "usage.options")
    for question_id, entry in options.items():
        if type(question_id) is not str:
            raise _malformed("usage.options")
        detail = _mapping(entry, "usage.options")
        if set(detail) != _OPTIONS_KEYS:
            raise _malformed("usage.options")
        _count(detail["total"], "usage.options")
        _count(detail["distinct"], "usage.options")
        per_option = detail["tokens_per_option"]
        if per_option is not None:
            _count(per_option, "usage.options")
    return bool(options)


def _validate_usage(value: object) -> bool:
    """Validate the native usage object; return whether it reports any truncation."""
    usage = _mapping(value, "usage")
    keys = set(usage)
    if not keys >= _USAGE_REQUIRED or not keys <= (_USAGE_REQUIRED | _USAGE_OPTIONAL):
        raise _malformed("usage.keys")
    counts = {name: _count(usage[name], f"usage.{name}") for name in _USAGE_COUNTS}
    truncated = usage["truncated"]
    if type(truncated) is not bool:
        raise _malformed("usage.truncated")
    truncated_questions = usage["truncated_questions"]
    if type(truncated_questions) is not list or any(
        type(item) is not str for item in truncated_questions
    ):
        raise _malformed("usage.truncated_questions")
    collapsed = "options" in usage and _validate_options(usage["options"])
    return counts["state_tokens_dropped"] > 0 or truncated or bool(truncated_questions) or collapsed


def _laya_inner_answer(body: object, question_id: str) -> object:
    envelope = _mapping(body, "body_type")
    if set(envelope) != _ENVELOPE_KEYS:
        raise _malformed("envelope_keys")
    if envelope["model"] != LAYA_MODEL_MARKER:
        raise _malformed("model_marker")
    answers = _mapping(envelope["answers"], "answers")
    if set(answers) != {question_id}:
        raise _malformed("answers")
    if _validate_usage(envelope["usage"]):
        raise _RejectedError("input_too_long", "normalize.usage.truncation")
    return answers[question_id]


# --------------------------------------------------------------------------- #
# Jev envelope (experimental profile)
# --------------------------------------------------------------------------- #


def _jev_inner_answer(body: object, question_id: str) -> object:
    """Validate the frozen Jev response shape, then the answering model, then extract."""
    envelope = _mapping(body, "body_type")
    if set(envelope) != _ENVELOPE_KEYS:
        raise _malformed("envelope_keys")
    model = envelope["model"]
    if type(model) is not str:
        raise _malformed("model_type")
    answers = _mapping(envelope["answers"], "answers")
    if set(answers) != {question_id}:
        raise _malformed("answers")
    usage = _mapping(envelope["usage"], "usage")
    if set(usage) != _JEV_USAGE_KEYS:
        raise _malformed("usage.keys")
    for name in sorted(_JEV_USAGE_KEYS):
        _count(usage[name], f"usage.{name}")
    if model != _JEV_MODEL:
        # A well-formed response from a different answering model: the vendor's
        # version claim does not match the locked target. Never repaired.
        raise _RejectedError("identity_mismatch", "normalize.answering_model")
    return answers[question_id]


# --------------------------------------------------------------------------- #
# Inner answer
# --------------------------------------------------------------------------- #


def _answer(
    inner: object,
    question: ChoiceQuestion,
    tolerance: float,
    *,
    required: frozenset[str] = _ANSWER_REQUIRED,
    optional: frozenset[str] = _ANSWER_OPTIONAL,
) -> tuple[str, tuple[tuple[str, float], ...], float | None, bool]:
    """Return ``(choice, ordered normalized probabilities, confidence, renormalized)``."""
    answer = _mapping(inner, "body_type")
    keys = set(answer)
    if not keys >= required or not keys <= (required | optional):
        raise _malformed("answer_keys")
    if answer["type"] != "choice":
        raise _malformed("type")
    choice = answer["choice"]
    if type(choice) is not str:
        raise _malformed("choice_type")
    labels = question.labels
    if choice not in labels:
        raise _RejectedError("unknown_choice", "normalize.unknown_choice")
    raw = _mapping(answer["probabilities"], "probabilities_type")
    if set(raw) != set(labels):
        raise _malformed("probabilities_keys")
    values = [_unit_interval(raw[label], "probability_value") for label in labels]
    total = math.fsum(values)
    if total <= 0.0 or abs(total - 1.0) > tolerance:
        raise _malformed("probability_sum")
    confidence = None
    if "confidence" in answer:
        confidence = _unit_interval(answer["confidence"], "confidence")
    if "answer_confidence" in answer:
        _unit_interval(answer["answer_confidence"], "answer_confidence")
    if "action" in answer:
        _mapping(answer["action"], "action")
    probabilities = tuple(
        (label, value / total if total != 1.0 else value)
        for label, value in zip(labels, values, strict=True)
    )
    return choice, probabilities, confidence, total != 1.0


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def normalize(
    capture: CapturedOutcome, question: ChoiceQuestion, expected_identity: ModelIdentity
) -> Outcome:
    """Normalize one captured provider result against the locked question and identity."""
    if not isinstance(capture, CapturedOutcome):
        raise SchemaError("capture: must be CapturedOutcome")
    if not isinstance(question, ChoiceQuestion):
        raise SchemaError("question: must be ChoiceQuestion")
    if not isinstance(expected_identity, ModelIdentity):
        raise SchemaError("expected_identity: must be ModelIdentity")
    warnings = capture.warnings
    fallback_used = capture.fallback_used
    if capture.identity != expected_identity:
        return ProviderFailure(
            "identity_mismatch", (*warnings, "normalize.identity_mismatch"), fallback_used
        )
    if capture.failure_code is not None:
        return ProviderFailure(capture.failure_code, warnings, fallback_used)
    body_text = capture.body_json
    if body_text is None:  # pragma: no cover - CapturedOutcome enforces exclusivity
        raise SchemaError("capture: body_json or failure_code is required")
    try:
        try:
            body = strict_json_loads(body_text)
        except SchemaError:
            raise _malformed("invalid_json") from None
        if expected_identity.provider == "laya":
            inner = _laya_inner_answer(body, question.question_id)
            choice, probabilities, confidence, renormalized = _answer(
                inner, question, laya_mass_tolerance(len(question.options))
            )
        elif expected_identity.provider == "jev":
            inner = _jev_inner_answer(body, question.question_id)
            choice, probabilities, confidence, renormalized = _answer(
                inner,
                question,
                _JEV_MASS_TOLERANCE,
                required=_JEV_ANSWER_REQUIRED,
                optional=frozenset(),
            )
        else:
            choice, probabilities, confidence, renormalized = _answer(
                body, question, FIXTURE_MASS_TOLERANCE
            )
    except _RejectedError as rejected:
        return ProviderFailure(rejected.code, (*warnings, rejected.warning), fallback_used)
    if renormalized:
        warnings = (*warnings, "normalize.renormalized")
    selected = dict(probabilities)[choice]
    return ChoiceAnswer(choice, probabilities, selected, confidence, warnings, fallback_used)
