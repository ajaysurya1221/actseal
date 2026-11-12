"""User-supplied predictions with an immutable file identity and raw gating score.

The file is LF-delimited JSONL, bounded before decoding, splitting or hashing.
Only the row framing is validated here; answer defects are preserved for the
pure recorded normalizer so collection and offline replay interpret them alike.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from actseal.adapters.fixture import _iter_lines, validate_timeout
from actseal.errors import ProviderSetupError, SchemaError
from actseal.normalization import NORMALIZER_VERSION, RECORDING_WARNING, request_sha256
from actseal.records import FAILURE_CODES, CapturedOutcome, DecisionRequest, ModelIdentity
from actseal.serialization import canonical_json, sha256_bytes, strict_json_loads

ADAPTER_VERSION: Final = "1"
MAX_ROW_BYTES: Final = 1024 * 1024
MAX_RECORDED_BYTES: Final = 128 * 1024 * 1024


def _parse_rows(data: bytes) -> dict[str, tuple[str | None, str | None]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise SchemaError("responses: must be valid UTF-8") from None
    rows: dict[str, tuple[str | None, str | None]] = {}
    for index, line in enumerate(_iter_lines(text)):
        path = f"responses[{index}]"
        if len(line.encode("utf-8")) > MAX_ROW_BYTES:
            raise SchemaError(f"{path}: row exceeds {MAX_ROW_BYTES} bytes")
        try:
            value = strict_json_loads(line)
        except SchemaError as exc:
            raise SchemaError(f"{path}: {exc}") from None
        if type(value) is not dict:
            raise SchemaError(f"{path}: expected object")
        case_id = value.get("case_id")
        if type(case_id) is not str or not case_id:
            raise SchemaError(f"{path}.case_id: must be a nonempty string")
        if case_id in rows:
            raise SchemaError(f"{path}.case_id: duplicate case id")
        if "failure_code" in value:
            if set(value) != {"case_id", "failure_code"}:
                raise SchemaError(f"{path}: expected exactly case_id, failure_code")
            failure = value["failure_code"]
            if type(failure) is not str or failure not in FAILURE_CODES:
                raise SchemaError(f"{path}.failure_code: unsupported value")
            rows[case_id] = (None, failure)
        else:
            required = {"case_id", "choice", "score"}
            if not required <= set(value) <= required | {"probabilities"}:
                raise SchemaError(
                    f"{path}: expected case_id, choice, score, optional probabilities"
                )
            body = {key: item for key, item in value.items() if key != "case_id"}
            body["type"] = "choice"
            rows[case_id] = (canonical_json(body).decode("utf-8"), None)
    if not rows:
        raise SchemaError("responses: must contain at least one row")
    return rows


class RecordedModel:
    """Read deterministic predictions without contacting their claimed source model."""

    def __init__(self, responses: Path, *, model: str, revision: str) -> None:
        if not isinstance(responses, Path):
            raise SchemaError("responses: must be a Path")
        try:
            with responses.open("rb") as handle:
                data = handle.read(MAX_RECORDED_BYTES + 1)
        except OSError:
            raise ProviderSetupError("responses: predictions file could not be read") from None
        if len(data) > MAX_RECORDED_BYTES:
            raise SchemaError(f"responses: file exceeds {MAX_RECORDED_BYTES} bytes")
        self._rows = _parse_rows(data)
        self._identity = ModelIdentity(
            "recorded",
            model,
            revision,
            (("responses", sha256_bytes(data)),),
            ADAPTER_VERSION,
            NORMALIZER_VERSION,
            (),
        )

    def identity(self) -> ModelIdentity:
        return self._identity

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        validate_timeout(timeout_s)
        if not isinstance(request, DecisionRequest):
            raise SchemaError("request: must be DecisionRequest")
        row = self._rows.get(request.case_id)
        if row is None:
            raise ProviderSetupError("responses: requested case id is not recorded")
        body, failure = row
        return CapturedOutcome(
            request_sha256(request),
            self._identity,
            body,
            failure,
            (RECORDING_WARNING,),
            fallback_used=False,
        )

    def close(self) -> None:
        """No provider resources were acquired."""
