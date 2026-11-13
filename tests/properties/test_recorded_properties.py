"""Generated raw-score invariants independent of any provider or transport."""

from __future__ import annotations

import json
import math
import random
import struct

from actseal.normalization import normalize
from actseal.policy import evaluate
from actseal.records import (
    CapturedOutcome,
    ChoiceAnswer,
    ChoiceQuestion,
    LockedPolicy,
    ModelIdentity,
    Option,
    ProviderFailure,
)


def outcome(body: object, labels: tuple[str, ...]) -> ChoiceAnswer | ProviderFailure:
    identity = ModelIdentity("recorded", "synthetic", "1", (), "1", "1", ())
    question = ChoiceQuestion("q", "choose", tuple(Option(label, label) for label in labels))
    capture = CapturedOutcome("a" * 64, identity, json.dumps(body), None, (), False)
    return normalize(capture, question, identity)


def test_generated_valid_scores_keep_exact_float_bits_and_threshold_decisions() -> None:
    rng = random.Random(43121)  # noqa: S311 - deterministic synthetic test generation
    scores = [0.0, -0.0, 1.0, 5e-324, math.nextafter(1.0, 0.0)]
    scores += [rng.random() for _ in range(100)]
    for count in range(2, 17):
        labels = tuple(f"label-{i}" for i in range(count))
        choice = labels[-1]
        for score in scores:
            body: dict[str, object] = {"type": "choice", "choice": choice, "score": score}
            remainder = (1.0 - score) / (count - 1)
            probabilities = {label: score if label == choice else remainder for label in labels}
            for has_map in (False, True):
                if has_map:
                    body["probabilities"] = probabilities
                result = outcome(body, labels)
                assert isinstance(result, ChoiceAnswer)
                assert struct.pack("!d", result.selected_probability) == struct.pack("!d", score)
                assert dict(result.probabilities) == (probabilities if has_map else {})
                if score > 0:
                    policy = LockedPolicy(labels, labels, score)
                    assert evaluate(result, policy).action == "ACT"
                    if score < 1:
                        higher = LockedPolicy(labels, labels, math.nextafter(score, 1.0))
                        assert evaluate(result, higher).action == "ABSTAIN"


def test_generated_invalid_or_missing_scores_never_produce_an_answer() -> None:
    rng = random.Random(43122)  # noqa: S311 - deterministic synthetic test generation
    labels = ("a", "b")
    for _ in range(100):
        score = rng.random()
        valid: dict[str, object] = {
            "type": "choice",
            "choice": "a",
            "score": score,
            "probabilities": {"a": score, "b": 1 - score},
        }
        missing = {key: value for key, value in valid.items() if key != "score"}
        assert isinstance(outcome(missing, labels), ProviderFailure)
        invalid: list[object] = [
            None,
            True,
            False,
            str(score),
            [],
            {},
            -rng.random() - 1,
            rng.random() + 2,
        ]
        invalid += [float("nan"), float("inf"), float("-inf"), math.nextafter(score, 1.0)]
        for value in invalid:
            body = {**valid, "score": value}
            assert isinstance(outcome(body, labels), ProviderFailure)
