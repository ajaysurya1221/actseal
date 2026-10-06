"""Real pinned Laya CPU adapter smoke (marked ``integration``).

Prerequisites are explicit: the optional ``laya`` extra must be installed, the
pinned checkpoint must already be in the local Hugging Face cache, and the
library offline flags must be set. A missing prerequisite FAILS this test with
the reason; it never skips into a claimed pass. Run exactly:

    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya \
        pytest -m integration tests/integration/test_laya.py
"""

from __future__ import annotations

import importlib
import importlib.util
import math
import os
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from actseal.adapters.laya import (
    ADAPTER_VERSION,
    ARTIFACT_HASHES,
    MODEL_ID,
    REVISION,
    THREADS,
    LayaModel,
)
from actseal.normalization import NORMALIZER_VERSION, normalize, request_sha256
from actseal.records import (
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionRequest,
    Option,
    ProviderFailure,
)
from actseal.serialization import strict_json_loads

pytestmark = pytest.mark.integration

# The approved Linux graph is the official CPU build (docs/dependencies.md, ADR 0006/0011);
# macOS keeps the tested PyPI wheel. Observed versions enter identity unchanged.
EXPECTED_TORCH = "2.14.1+cpu" if sys.platform == "linux" else "2.14.1"
EXPECTED_VERSIONS = {
    "laya": "0.3.28",
    "torch": EXPECTED_TORCH,
    "transformers": "5.18.0",
    "huggingface_hub": "1.33.0",
    "safetensors": "0.8.0",
    "numpy": "2.5.3",
}

SMOKE_STATE = (
    "I was charged twice for my monthly subscription. Please refund the duplicate payment."
)
SMOKE_QUESTION = ChoiceQuestion(
    "department",
    "Which department should handle this support request?",
    (
        Option("billing", "Charges, invoices, payments, refunds"),
        Option("technical", "Software errors, bugs, outages"),
        Option("other", "Any other request"),
    ),
)


def _require_prerequisites() -> None:
    missing = [name for name in EXPECTED_VERSIONS if importlib.util.find_spec(name) is None]
    if missing:
        pytest.fail(f"prerequisite missing: optional packages not installed: {missing}")
    for name, expected in EXPECTED_VERSIONS.items():
        version = str(importlib.import_module(name).__version__)
        if version != expected:
            pytest.fail(f"prerequisite mismatch: {name} {version} != pinned {expected}")
    for variable in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        if os.environ.get(variable) != "1":
            pytest.fail(f"prerequisite missing: {variable}=1 must be set for the cached run")
    hub: Any = importlib.import_module("huggingface_hub")
    for name, _ in ARTIFACT_HASHES:
        path = hub.try_to_load_from_cache(MODEL_ID, name, revision=REVISION)
        if not isinstance(path, str) or not os.path.isfile(path):
            pytest.fail(f"prerequisite missing: pinned artifact not cached: {name}")


@pytest.fixture(scope="module")
def model() -> Iterator[LayaModel]:
    _require_prerequisites()
    instance = LayaModel(offline=True)
    try:
        yield instance
    finally:
        instance.close()


def test_loaded_identity_is_the_pinned_model(model: LayaModel) -> None:
    identity = model.identity()
    assert identity.provider == "laya"
    assert identity.model == MODEL_ID
    assert identity.revision == REVISION
    assert identity.artifact_hashes == ARTIFACT_HASHES
    assert identity.adapter_version == ADAPTER_VERSION
    assert identity.normalizer_version == NORMALIZER_VERSION
    runtime = dict(identity.runtime)
    for name, expected in EXPECTED_VERSIONS.items():
        assert runtime[name] == expected
    assert runtime["device"] == "cpu"
    assert runtime["dtype"] == "torch.float32"
    assert runtime["threads"] == str(THREADS)
    assert runtime["backend"] == "eager"
    assert runtime["compile"] == "False"
    assert runtime["fast"] == "False"
    assert runtime["max_len"] == "1024"
    assert runtime["head_max_len"] == "256"


def test_smoke_request_preserves_envelope_and_normalizes(model: LayaModel) -> None:
    request = DecisionRequest("smoke-001", SMOKE_STATE, SMOKE_QUESTION)
    capture = model.decide(request, timeout_s=30.0)
    assert capture.request_sha256 == request_sha256(request)
    assert capture.identity == model.identity()
    assert capture.failure_code is None, capture
    assert capture.fallback_used is False
    assert any("choice:11+" in warning for warning in capture.warnings), capture.warnings
    assert all(warning.startswith("laya.") for warning in capture.warnings)
    assert capture.body_json is not None
    body = strict_json_loads(capture.body_json)
    assert isinstance(body, dict)
    assert set(body) == {"model", "answers", "usage"}
    assert body["model"] == "laya-rl-agent"
    assert set(body["answers"]) == {"department"}
    usage = body["usage"]
    assert usage["state_tokens_dropped"] == 0
    assert usage["truncated"] is False
    assert usage["truncated_questions"] == []
    assert "options" not in usage
    outcome = normalize(capture, SMOKE_QUESTION, model.identity())
    assert isinstance(outcome, ChoiceAnswer), outcome
    assert outcome.choice == "billing"
    assert math.isclose(math.fsum(p for _, p in outcome.probabilities), 1.0, abs_tol=1e-12)
    assert all(0.0 <= p <= 1.0 for _, p in outcome.probabilities)
    assert outcome.selected_probability == dict(outcome.probabilities)["billing"]
    assert outcome.provider_confidence is not None
    assert "choice:11+" in " ".join(outcome.warnings)


def test_second_request_reuses_the_healthy_worker(model: LayaModel) -> None:
    request = DecisionRequest(
        "smoke-002", "The app crashes on launch after the update.", SMOKE_QUESTION
    )
    capture = model.decide(request, timeout_s=30.0)
    assert capture.failure_code is None, capture
    outcome = normalize(capture, SMOKE_QUESTION, model.identity())
    assert isinstance(outcome, ChoiceAnswer), outcome
    assert outcome.choice in SMOKE_QUESTION.labels


def test_oversized_state_is_rejected_before_inference(model: LayaModel) -> None:
    state = " ".join(["refund"] * 3000)
    capture = model.decide(DecisionRequest("smoke-003", state, SMOKE_QUESTION), timeout_s=30.0)
    assert capture.failure_code == "input_too_long"
    assert "laya.preflight.state_tokens" in capture.warnings
    outcome = normalize(capture, SMOKE_QUESTION, model.identity())
    assert isinstance(outcome, ProviderFailure)
    assert outcome.code == "input_too_long"
    healthy = model.decide(
        DecisionRequest("smoke-004", SMOKE_STATE, SMOKE_QUESTION), timeout_s=30.0
    )
    assert healthy.failure_code is None


def test_close_leaves_no_worker_and_is_idempotent(model: LayaModel) -> None:
    child = model._child
    assert child is not None
    assert child.poll() is None
    model.close()
    assert child.poll() is not None
    model.close()
    capture = model.decide(
        DecisionRequest("smoke-005", SMOKE_STATE, SMOKE_QUESTION), timeout_s=30.0
    )
    assert capture.failure_code == "unavailable"
