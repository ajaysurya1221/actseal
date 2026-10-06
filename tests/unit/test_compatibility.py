"""Replay-engine compatibility, the reviewed registry and legacy (schema 1) rejection.

Every lock and bundle here is produced by the real ``create_lock``,
``write_bundle`` and ``assess``; foreign producer fingerprints are modelled by
resealing a real lock with a different ``implementation_sha256`` and, where a
bundle is involved, rewriting the stored verdict to the new seal exactly as a
foreign producer would have written it. Registries are supplied either directly
(``registry=``) or by pointing the loader at a temporary file, never by
monkeypatching fingerprints. ``test_cross_release`` complements this module with
evidence produced by a genuinely different source tree.

The "0.1.0" documents in this module are **synthetic reconstructions** of the
actseal 0.1.0 wire shape (eleven lock fields at ``schema_version`` 1, resealed
with the 0.1.0 digest rule; manifest ``schema_version`` 1). They are not
archived 0.1.0 artifacts; this repository ships none.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
from test_evidence import (
    compact,
    make_bundle,
    make_lock,
    read_files,
    seal_manifest,
    sha256_hex,
    verification_jsonl,
)

import actseal.compatibility as compatibility_module
from actseal.assessment import assess
from actseal.cli import main
from actseal.compatibility import (
    CURRENT_ENGINE,
    LEGACY_GUIDANCE,
    MAX_REGISTRY_BYTES,
    REGISTRY_FILE,
    REGISTRY_SCHEMA_VERSION,
    SUPPORTED_ENGINES,
    CompatibilityRegistry,
    LegacySchemaError,
    check_replay_compatibility,
    is_legacy_lock,
    is_legacy_manifest,
    load_registry,
    parse_registry,
    require_exact_implementation,
)
from actseal.errors import IntegrityError, SchemaError
from actseal.evidence import (
    BUNDLE_SCHEMA_VERSION,
    DATA_FILES,
    LOCK_FILE,
    MANIFEST_FILE,
    VERDICT_FILE,
    read_bundle_files,
    write_bundle,
)
from actseal.locking import create_lock, lock_digest, parse_lock, validate_inputs, validate_lock
from actseal.records import LOCK_SCHEMA_VERSION, Case, DecisionRequest, PlanLock
from actseal.replay import (
    REASON_LEGACY_SCHEMA,
    REASON_LOCK,
    REASON_LOCK_SCHEMA,
    UNKNOWN_LOCK_SHA256,
    UNKNOWN_SCOPE,
    replay,
)
from actseal.runner import collect, verify_run
from actseal.serialization import canonical_json, implementation_fingerprint, to_data
from conftest import make_contract, make_identity

FOREIGN = "2" * 64
OTHER = "3" * 64
PACKAGE = Path(__file__).resolve().parents[2] / "src" / "actseal"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def reseal(lock: PlanLock) -> PlanLock:
    return replace(lock, sha256=lock_digest(lock))


def foreign_lock(lock: PlanLock | None = None, fingerprint: str = FOREIGN) -> PlanLock:
    """A real lock whose producer fingerprint is not the running implementation."""
    return reseal(replace(lock or make_lock(), implementation_sha256=fingerprint))


def registry_text(entries: dict[str, str]) -> str:
    return json.dumps({"schema_version": 1, "implementations": entries})


def registry(entries: dict[str, str]) -> CompatibilityRegistry:
    return parse_registry(registry_text(entries))


def point_registry_at(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, text: str | None) -> Path:
    """Make ``load_registry`` read ``text`` from a temporary file (``None``: a missing file)."""
    path = tmp_path / "registry.json"
    if text is not None:
        path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(compatibility_module, "_REGISTRY_PATH", path)
    return path


def foreign_bundle_dir(tmp_path: Path, approved: CompatibilityRegistry) -> tuple[Path, PlanLock]:
    """Write a real bundle, then make it look produced by a foreign (registered) implementation.

    The lock is resealed with the foreign fingerprint and the stored verdict is
    rewritten to the new seal; every ordinary hash is recomputed. ``approved``
    must register both sides so the rewrite itself validates.
    """
    bundle = make_bundle()
    out = write_bundle(bundle, tmp_path / "run")
    lock = foreign_lock(bundle.lock)
    check_replay_compatibility(lock, registry=approved)
    verdict = replace(bundle.verdict, lock_sha256=lock.sha256)
    (out / LOCK_FILE).write_bytes(canonical_json(to_data(lock)) + b"\n")
    (out / VERDICT_FILE).write_bytes(canonical_json(to_data(verdict)) + b"\n")
    files = {name: (out / name).read_bytes() for name in DATA_FILES}
    inventory = {
        name: {"size": len(data), "sha256": sha256_hex(data)} for name, data in files.items()
    }
    (out / MANIFEST_FILE).write_bytes(
        seal_manifest({"schema_version": BUNDLE_SCHEMA_VERSION, "files": inventory})
    )
    return out, lock


def legacy_lock_bytes(lock: PlanLock) -> bytes:
    """Synthetic 0.1.0 lock: drop the v1.0 field, version 1, reseal with the 0.1.0 rule."""
    data = to_data(lock)
    del data["replay_engine_version"]
    data["schema_version"] = 1
    del data["sha256"]
    data["sha256"] = sha256_hex(compact(data))
    return compact(data) + b"\n"


def legacy_bundle_dir(tmp_path: Path) -> Path:
    """Synthetic 0.1.0 bundle: legacy lock, verdict bound to it, schema-1 manifest."""
    bundle = make_bundle()
    out = write_bundle(bundle, tmp_path / "legacy")
    lock_data = legacy_lock_bytes(bundle.lock)
    legacy_seal = json.loads(lock_data)["sha256"]
    verdict = replace(bundle.verdict, lock_sha256=legacy_seal)
    (out / LOCK_FILE).write_bytes(lock_data)
    (out / VERDICT_FILE).write_bytes(canonical_json(to_data(verdict)) + b"\n")
    files = {name: (out / name).read_bytes() for name in DATA_FILES}
    inventory = {
        name: {"size": len(data), "sha256": sha256_hex(data)} for name, data in files.items()
    }
    (out / MANIFEST_FILE).write_bytes(seal_manifest({"schema_version": 1, "files": inventory}))
    return out


def run_cli(
    capsys: pytest.CaptureFixture[str], argv: list[str]
) -> tuple[int, dict[str, object], str]:
    code = main(argv)
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert isinstance(document, dict)
    return code, document, captured.err


class CountingModel:
    """A DecisionModel that must never be asked to decide."""

    def __init__(self, lock: PlanLock) -> None:
        self._identity = lock.model_identity
        self.calls = 0

    def identity(self) -> object:
        return self._identity

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> object:
        del request, timeout_s
        self.calls += 1
        pytest.fail("decide must not be called for a foreign producer")

    def close(self) -> None:
        return


# --------------------------------------------------------------------------- #
# Constants and the packaged registry
# --------------------------------------------------------------------------- #


def test_engine_constants_are_frozen() -> None:
    assert CURRENT_ENGINE == "actseal-choice-v1"
    assert set(SUPPORTED_ENGINES) == {"actseal-choice-v1"}
    assert REGISTRY_SCHEMA_VERSION == 1
    assert REGISTRY_FILE == "compatibility_registry.json"
    assert "actseal==0.1.0" in LEGACY_GUIDANCE
    assert "docs/migration.md" in LEGACY_GUIDANCE


def test_new_locks_record_schema_2_and_the_current_engine() -> None:
    lock = make_lock()
    assert lock.schema_version == LOCK_SCHEMA_VERSION == 2
    assert lock.replay_engine_version == CURRENT_ENGINE
    assert lock.implementation_sha256 == implementation_fingerprint()
    # The engine is inside the seal: changing it breaks the recorded seal.
    with pytest.raises(IntegrityError, match="sha256: self-seal"):
        validate_lock(replace(lock, replay_engine_version="actseal-choice-v2"))


def test_packaged_registry_is_valid_strict_json_and_currently_empty() -> None:
    path = PACKAGE / REGISTRY_FILE
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document == {"schema_version": 1, "implementations": {}}
    loaded = load_registry()
    assert loaded == CompatibilityRegistry(1, ())
    assert loaded.engine_for(implementation_fingerprint()) is None
    assert parse_registry(path.read_text(encoding="utf-8")) == loaded


def test_registry_file_is_outside_the_implementation_fingerprint() -> None:
    """Only ``*.py`` sources are fingerprinted, so approving a hash never changes the hash."""
    fingerprinted = {
        path.relative_to(PACKAGE).as_posix()
        for path in PACKAGE.rglob("*")
        if path.is_file() and path.suffix == ".py" and "__pycache__" not in path.parts
    }
    assert REGISTRY_FILE not in fingerprinted
    assert (PACKAGE / REGISTRY_FILE).is_file()
    assert PACKAGE.joinpath("compatibility.py").relative_to(PACKAGE).as_posix() in fingerprinted


def test_exact_current_source_validates_with_the_empty_packaged_registry() -> None:
    lock = make_lock()
    check_replay_compatibility(lock)
    check_replay_compatibility(lock, registry=CompatibilityRegistry(1, ()))
    validate_lock(lock)
    require_exact_implementation(lock)


# --------------------------------------------------------------------------- #
# parse_registry
# --------------------------------------------------------------------------- #


def test_parse_registry_accepts_exact_entries_sorted_and_immutable() -> None:
    parsed = registry({OTHER: CURRENT_ENGINE, FOREIGN: CURRENT_ENGINE})
    assert parsed.schema_version == 1
    assert parsed.implementations == ((FOREIGN, CURRENT_ENGINE), (OTHER, CURRENT_ENGINE))
    assert parsed.engine_for(FOREIGN) == CURRENT_ENGINE
    assert parsed.engine_for("4" * 64) is None
    assert registry({}).implementations == ()


REGISTRY_REJECTS: list[tuple[str, object, str]] = [
    ("not text", b"{}", "must be text"),
    ("not object", "[]", "expected object"),
    ("empty object", "{}", "expected exactly"),
    ("extra key", json.dumps({"schema_version": 1, "implementations": {}, "x": 1}), "exactly"),
    ("missing implementations", json.dumps({"schema_version": 1}), "exactly"),
    ("wildcard key form", json.dumps({"schema_version": 1, "implementations": {"*": "x"}}), "hex"),
    (
        "range key form",
        json.dumps({"schema_version": 1, "implementations": {FOREIGN + "-" + OTHER: "x"}}),
        "hex",
    ),
    (
        "uppercase hash",
        json.dumps({"schema_version": 1, "implementations": {"AB" * 32: CURRENT_ENGINE}}),
        "lowercase 64-character SHA256 hex",
    ),
    (
        "short hash",
        json.dumps({"schema_version": 1, "implementations": {"ab" * 31: CURRENT_ENGINE}}),
        "lowercase 64-character SHA256 hex",
    ),
    (
        "unsupported engine",
        json.dumps({"schema_version": 1, "implementations": {FOREIGN: "actseal-choice-v2"}}),
        "unsupported replay engine",
    ),
    (
        "engine not text",
        json.dumps({"schema_version": 1, "implementations": {FOREIGN: 1}}),
        "unsupported replay engine",
    ),
    (
        "engine list",
        json.dumps({"schema_version": 1, "implementations": {FOREIGN: [CURRENT_ENGINE]}}),
        "unsupported replay engine",
    ),
    ("implementations list", json.dumps({"schema_version": 1, "implementations": []}), "object"),
    ("version 0", json.dumps({"schema_version": 0, "implementations": {}}), "unsupported schema"),
    ("version 2", json.dumps({"schema_version": 2, "implementations": {}}), "unsupported schema"),
    ("version bool", json.dumps({"schema_version": True, "implementations": {}}), "integer"),
    ("version text", json.dumps({"schema_version": "1", "implementations": {}}), "integer"),
    ("version float", json.dumps({"schema_version": 1.0, "implementations": {}}), "integer"),
    (
        "duplicate hash key",
        (
            f'{{"schema_version":1,"implementations":{{"{FOREIGN}":"{CURRENT_ENGINE}",'
            f'"{FOREIGN}":"{CURRENT_ENGINE}"}}}}'
        ),
        "duplicate object key",
    ),
    ("duplicate top key", '{"schema_version":1,"schema_version":1,"implementations":{}}', "dup"),
    ("invalid json", "{", "invalid JSON"),
    ("nonfinite", '{"schema_version":NaN,"implementations":{}}', "nonfinite"),
    ("oversized", " " * (MAX_REGISTRY_BYTES + 1), "exceeds"),
]


@pytest.mark.parametrize(
    ("text", "fragment"),
    [(text, fragment) for _, text, fragment in REGISTRY_REJECTS],
    ids=[name for name, _, _ in REGISTRY_REJECTS],
)
def test_parse_registry_rejects_malformed_documents(text: object, fragment: str) -> None:
    with pytest.raises(SchemaError, match=fragment) as info:
        parse_registry(text)  # type: ignore[arg-type]
    # Diagnostics never echo registry keys or values.
    assert FOREIGN not in str(info.value)
    assert "actseal-choice-v2" not in str(info.value)


def test_load_registry_reports_unreadable_or_malformed_files_without_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = point_registry_at(monkeypatch, tmp_path, None)
    with pytest.raises(SchemaError, match="compatibility_registry: unavailable") as info:
        load_registry()
    assert str(missing) not in str(info.value)
    point_registry_at(monkeypatch, tmp_path, "[]")
    with pytest.raises(SchemaError, match="expected object"):
        load_registry()
    point_registry_at(monkeypatch, tmp_path, registry_text({FOREIGN: CURRENT_ENGINE}))
    assert load_registry().engine_for(FOREIGN) == CURRENT_ENGINE


# --------------------------------------------------------------------------- #
# check_replay_compatibility: every combination
# --------------------------------------------------------------------------- #


def _combinations() -> dict[str, tuple[Callable[[], PlanLock], dict[str, str], bool]]:
    current = implementation_fingerprint()
    both = {FOREIGN: CURRENT_ENGINE, current: CURRENT_ENGINE}
    return {
        "exact_current_empty_registry": (make_lock, {}, True),
        "exact_current_both_registered": (make_lock, both, True),
        "exact_current_only_running_registered": (make_lock, {current: CURRENT_ENGINE}, True),
        "foreign_both_registered": (foreign_lock, both, True),
        "foreign_only_producer_registered": (foreign_lock, {FOREIGN: CURRENT_ENGINE}, False),
        "foreign_only_running_registered": (foreign_lock, {current: CURRENT_ENGINE}, False),
        "foreign_neither_registered": (foreign_lock, {}, False),
        "foreign_other_producer_registered": (
            foreign_lock,
            {OTHER: CURRENT_ENGINE, current: CURRENT_ENGINE},
            False,
        ),
    }


@pytest.mark.parametrize("name", sorted(_combinations()))
def test_compatibility_combinations(
    name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    build, entries, accepted = _combinations()[name]
    lock = build()
    approved = registry(entries)
    point_registry_at(monkeypatch, tmp_path, registry_text(entries))
    if accepted:
        check_replay_compatibility(lock, registry=approved)
        check_replay_compatibility(lock)
        validate_lock(lock)
        return
    with pytest.raises(IntegrityError, match="implementation_sha256: does not match the current"):
        check_replay_compatibility(lock, registry=approved)
    with pytest.raises(IntegrityError, match="implementation_sha256"):
        check_replay_compatibility(lock)
    with pytest.raises(IntegrityError, match="implementation_sha256"):
        validate_lock(lock)


@pytest.mark.parametrize(
    "engine", ["actseal-choice-v2", "actseal-choice-v0", "ACTSEAL-CHOICE-V1", " actseal-choice-v1"]
)
def test_unsupported_engine_is_rejected_even_for_exact_current_source(engine: str) -> None:
    lock = reseal(replace(make_lock(), replay_engine_version=engine))
    assert lock_digest(lock) == lock.sha256
    with pytest.raises(IntegrityError, match="replay_engine_version: unsupported replay engine"):
        check_replay_compatibility(lock)
    with pytest.raises(IntegrityError, match="replay_engine_version"):
        validate_lock(lock)
    current = implementation_fingerprint()
    # A registry cannot approve an unsupported engine, and the engine check comes first.
    with pytest.raises(IntegrityError, match="replay_engine_version"):
        check_replay_compatibility(
            foreign_lock(lock),
            registry=registry({FOREIGN: CURRENT_ENGINE, current: CURRENT_ENGINE}),
        )


def test_compatibility_type_misuse_raises_schema_error() -> None:
    with pytest.raises(SchemaError, match="lock: must be PlanLock"):
        check_replay_compatibility(to_data(make_lock()))  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="lock: must be PlanLock"):
        require_exact_implementation(None)  # type: ignore[arg-type]


def test_malformed_packaged_registry_is_a_schema_error_only_when_consulted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    point_registry_at(monkeypatch, tmp_path, '{"schema_version": 1}')
    validate_lock(make_lock())  # exact source never consults the registry
    with pytest.raises(SchemaError, match="compatibility_registry"):
        validate_lock(foreign_lock())


# --------------------------------------------------------------------------- #
# Shared validate_lock: validate_inputs, assess, write_bundle and replay agree
# --------------------------------------------------------------------------- #


def test_approved_foreign_lock_flows_through_validate_inputs_assess_and_replay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    current = implementation_fingerprint()
    entries = {FOREIGN: CURRENT_ENGINE, current: CURRENT_ENGINE}
    both = registry(entries)
    point_registry_at(monkeypatch, tmp_path, registry_text(entries))
    out, lock = foreign_bundle_dir(tmp_path, both)
    files = read_files(out)
    calibration = files["calibration.jsonl"].decode("utf-8")
    verification = files["verification.jsonl"].decode("utf-8")
    cases = validate_inputs(lock, calibration, verification)
    assert cases == lock.verification_cases
    bundle = make_bundle()
    records = bundle.records
    verdict = assess(records, lock, bundle.faults)
    assert verdict.status == "INCONCLUSIVE"
    assert verdict.lock_sha256 == lock.sha256
    replayed = replay(out)
    assert replayed == verdict
    assert replay(out, expected_lock_sha256=lock.sha256) == verdict
    # Without the approval the same bundle is ERROR at the lock stage, reporting the decoded seal.
    point_registry_at(monkeypatch, tmp_path, registry_text({}))
    rejected = replay(out)
    assert rejected.status == "ERROR"
    assert rejected.reasons == (REASON_LOCK,)
    assert rejected.lock_sha256 == lock.sha256
    assert assess(records, lock, bundle.faults).reasons == ("integrity.lock",)
    with pytest.raises(IntegrityError, match="implementation_sha256"):
        validate_inputs(lock, calibration, verification)


def test_one_sided_registration_never_replays(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    current = implementation_fingerprint()
    both = registry({FOREIGN: CURRENT_ENGINE, current: CURRENT_ENGINE})
    out, lock = foreign_bundle_dir(tmp_path, both)
    for entries in ({FOREIGN: CURRENT_ENGINE}, {current: CURRENT_ENGINE}, {}):
        point_registry_at(monkeypatch, tmp_path, registry_text(entries))
        verdict = replay(out)
        assert verdict.status == "ERROR", entries
        assert verdict.reasons == (REASON_LOCK,)
        assert verdict.lock_sha256 == lock.sha256


def test_write_bundle_accepts_an_approved_foreign_lock_but_the_cli_cannot_collect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    current = implementation_fingerprint()
    point_registry_at(
        monkeypatch, tmp_path, registry_text({FOREIGN: CURRENT_ENGINE, current: CURRENT_ENGINE})
    )
    base = make_bundle()
    lock = foreign_lock(base.lock)
    verdict = assess(base.records, lock, base.faults)
    foreign = replace(base, lock=lock, verdict=verdict)
    out = write_bundle(foreign, tmp_path / "foreign")
    assert replay(out) == verdict


# --------------------------------------------------------------------------- #
# Collection stays exact-source
# --------------------------------------------------------------------------- #


def test_direct_collect_against_a_registered_foreign_producer_makes_zero_provider_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    current = implementation_fingerprint()
    point_registry_at(
        monkeypatch, tmp_path, registry_text({FOREIGN: CURRENT_ENGINE, current: CURRENT_ENGINE})
    )
    lock = foreign_lock()
    validate_lock(lock)  # replay-compatible...
    model = CountingModel(lock)
    with pytest.raises(IntegrityError, match="new collection requires the exact current"):
        collect(model, lock, lock.verification_cases)  # type: ignore[arg-type]
    assert model.calls == 0
    with pytest.raises(IntegrityError, match="new collection requires the exact current"):
        collect(model, foreign_lock(fingerprint=OTHER), lock.verification_cases)  # type: ignore[arg-type]
    assert model.calls == 0


def test_verify_run_refuses_a_registered_foreign_lock_before_the_factory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    current = implementation_fingerprint()
    point_registry_at(
        monkeypatch, tmp_path, registry_text({FOREIGN: CURRENT_ENGINE, current: CURRENT_ENGINE})
    )
    bundle = make_bundle()
    lock = foreign_lock(bundle.lock)
    (tmp_path / "lock.json").write_bytes(canonical_json(to_data(lock)) + b"\n")
    (tmp_path / "calibration.jsonl").write_text(bundle.calibration_jsonl, encoding="utf-8")
    (tmp_path / "verification.jsonl").write_text(bundle.verification_jsonl, encoding="utf-8")

    def never_called() -> object:
        pytest.fail("model factory must not be called for a foreign producer")

    with pytest.raises(IntegrityError, match="new collection requires the exact current"):
        verify_run(
            tmp_path / "lock.json",
            tmp_path / "calibration.jsonl",
            tmp_path / "verification.jsonl",
            tmp_path / "run",
            provider="fixture",
            model_factory=never_called,  # type: ignore[arg-type]
        )
    assert not (tmp_path / "run").exists()


# --------------------------------------------------------------------------- #
# Legacy (schema 1) detection and rejection
# --------------------------------------------------------------------------- #


def test_is_legacy_lock_requires_the_exact_zero_point_one_shape() -> None:
    legacy = json.loads(legacy_lock_bytes(make_lock()))
    assert is_legacy_lock(legacy)
    assert not is_legacy_lock(to_data(make_lock()))
    assert not is_legacy_lock({**legacy, "schema_version": 2})
    assert not is_legacy_lock({**legacy, "schema_version": True})
    assert not is_legacy_lock({**legacy, "schema_version": 1.0})
    assert not is_legacy_lock({**legacy, "extra": 1})
    assert not is_legacy_lock({key: value for key, value in legacy.items() if key != "sha256"})
    assert not is_legacy_lock([legacy])
    assert not is_legacy_lock("1")


def test_is_legacy_manifest_requires_the_exact_zero_point_one_shape() -> None:
    files = {name: {"size": 1, "sha256": "0" * 64} for name in DATA_FILES}
    legacy = {"schema_version": 1, "files": files, "sha256": "0" * 64}
    assert is_legacy_manifest(legacy)
    assert not is_legacy_manifest({**legacy, "schema_version": 2})
    assert not is_legacy_manifest({**legacy, "schema_version": True})
    assert not is_legacy_manifest({**legacy, "files": {**files, "extra.json": files[LOCK_FILE]}})
    assert not is_legacy_manifest({**legacy, "files": []})
    assert not is_legacy_manifest({"schema_version": 1, "files": files})
    assert not is_legacy_manifest(None)


def test_parse_lock_reports_a_real_schema_1_lock_with_migration_guidance() -> None:
    data = legacy_lock_bytes(make_lock()).decode("utf-8")
    with pytest.raises(LegacySchemaError, match=r"actseal==0\.1\.0") as info:
        parse_lock(data)
    assert isinstance(info.value, SchemaError)
    assert str(info.value).startswith("lock.schema_version: ")
    assert LEGACY_GUIDANCE in str(info.value)


@pytest.mark.parametrize(
    ("version", "with_engine", "fragment"),
    [
        (1, False, "actseal==0.1.0"),  # the real 0.1.0 shape
        (1, True, "unsupported schema version"),  # version 1 with a v1.0 field: not legacy
        (2, False, "missing fields replay_engine_version"),
        (3, True, "unsupported schema version"),
        (3, False, "missing fields replay_engine_version"),
        (True, True, "expected integer"),
        (True, False, "missing fields replay_engine_version"),
        (0, True, "unsupported schema version"),
    ],
)
def test_lock_schema_versions_1_2_3_and_booleans(
    version: object, with_engine: bool, fragment: str
) -> None:
    data = to_data(make_lock())
    data["schema_version"] = version
    if not with_engine:
        del data["replay_engine_version"]
    with pytest.raises(SchemaError, match=fragment) as info:
        parse_lock(json.dumps(data))
    legacy_shape = type(version) is int and version == 1 and not with_engine
    assert isinstance(info.value, LegacySchemaError) == legacy_shape


def test_read_bundle_files_reports_a_real_schema_1_manifest(tmp_path: Path) -> None:
    out = legacy_bundle_dir(tmp_path)
    with pytest.raises(LegacySchemaError, match=r"actseal==0\.1\.0") as info:
        read_bundle_files(out)
    assert str(info.value).startswith("manifest.schema_version: ")


@pytest.mark.parametrize(
    ("version", "fragment"), [(3, "unsupported"), (True, "unsupported"), (0, "unsupported")]
)
def test_manifest_versions_other_than_2_are_generic_schema_errors(
    tmp_path: Path, version: object, fragment: str
) -> None:
    out = write_bundle(make_bundle(), tmp_path / "run")
    manifest = json.loads((out / MANIFEST_FILE).read_text(encoding="utf-8"))
    (out / MANIFEST_FILE).write_bytes(
        seal_manifest({"schema_version": version, "files": manifest["files"]})
    )
    with pytest.raises(SchemaError, match=fragment) as info:
        read_bundle_files(out)
    assert not isinstance(info.value, LegacySchemaError)


def test_replay_of_a_legacy_bundle_is_error_with_the_legacy_reason_and_sentinel(
    tmp_path: Path,
) -> None:
    out = legacy_bundle_dir(tmp_path)
    before = read_files(out)
    verdict = replay(out)
    assert verdict.status == "ERROR"
    assert verdict.reasons == (REASON_LEGACY_SCHEMA,)
    assert REASON_LEGACY_SCHEMA == "integrity.legacy_schema"
    assert verdict.evidence_scope == UNKNOWN_SCOPE
    assert verdict.lock_sha256 == UNKNOWN_LOCK_SHA256
    assert (verdict.total, verdict.accepted, verdict.errors) == (0, 0, 0)
    assert replay(out, expected_lock_sha256="1" * 64).reasons == (REASON_LEGACY_SCHEMA,)
    assert read_files(out) == before  # legacy bytes are never altered


def test_replay_of_a_schema_2_bundle_holding_a_schema_1_lock_is_also_legacy(
    tmp_path: Path,
) -> None:
    bundle = make_bundle()
    out = write_bundle(bundle, tmp_path / "run")
    lock_data = legacy_lock_bytes(bundle.lock)
    (out / LOCK_FILE).write_bytes(lock_data)
    files = {name: (out / name).read_bytes() for name in DATA_FILES}
    inventory = {
        name: {"size": len(data), "sha256": sha256_hex(data)} for name, data in files.items()
    }
    (out / MANIFEST_FILE).write_bytes(
        seal_manifest({"schema_version": BUNDLE_SCHEMA_VERSION, "files": inventory})
    )
    verdict = replay(out)
    assert verdict.reasons == (REASON_LEGACY_SCHEMA,)
    assert verdict.lock_sha256 == UNKNOWN_LOCK_SHA256
    # An unknown (3) version in the same place stays the generic lock-schema reason.
    broken = json.loads(lock_data)
    broken["schema_version"] = 3
    (out / LOCK_FILE).write_bytes(compact(broken) + b"\n")
    files[LOCK_FILE] = (out / LOCK_FILE).read_bytes()
    inventory[LOCK_FILE] = {"size": len(files[LOCK_FILE]), "sha256": sha256_hex(files[LOCK_FILE])}
    (out / MANIFEST_FILE).write_bytes(
        seal_manifest({"schema_version": BUNDLE_SCHEMA_VERSION, "files": inventory})
    )
    assert replay(out).reasons == (REASON_LOCK_SCHEMA,)


def test_cli_replay_of_a_legacy_bundle_exits_3_with_guidance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = legacy_bundle_dir(tmp_path)
    code, document, err = run_cli(capsys, ["replay", str(out), "--json"])
    assert code == 3
    assert err == ""
    assert document["schema_version"] == 1
    assert document["status"] == "ERROR"
    assert document["reasons"] == [REASON_LEGACY_SCHEMA]
    assert document["lock_sha256"] == UNKNOWN_LOCK_SHA256
    assert document["notes"] == [LEGACY_GUIDANCE]
    code = main(["replay", str(out)])
    captured = capsys.readouterr()
    assert code == 3
    assert "reasons: integrity.legacy_schema" in captured.out
    assert captured.err == f"actseal replay: {LEGACY_GUIDANCE}\n"


def test_cli_verify_against_a_legacy_lock_exits_3_with_guidance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle = make_bundle()
    lock_path = tmp_path / "legacy-lock.json"
    lock_path.write_bytes(legacy_lock_bytes(bundle.lock))
    (tmp_path / "calibration.jsonl").write_text(bundle.calibration_jsonl, encoding="utf-8")
    (tmp_path / "verification.jsonl").write_text(bundle.verification_jsonl, encoding="utf-8")
    (tmp_path / "responses.jsonl").write_text("", encoding="utf-8")
    code, document, _ = run_cli(
        capsys,
        [
            "verify",
            "--lock",
            str(lock_path),
            "--calibration",
            str(tmp_path / "calibration.jsonl"),
            "--verification",
            str(tmp_path / "verification.jsonl"),
            "--provider",
            "fixture",
            "--responses",
            str(tmp_path / "responses.jsonl"),
            "--out",
            str(tmp_path / "run"),
            "--json",
        ],
    )
    assert code == 3
    assert document["schema_version"] == 1
    error = str(document["error"])
    assert error.startswith("LegacySchemaError: lock.schema_version: ")
    assert "actseal==0.1.0" in error
    assert not (tmp_path / "run").exists()


def test_replay_notes_are_empty_for_ordinary_verdicts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = write_bundle(make_bundle(), tmp_path / "run")
    code, document, err = run_cli(capsys, ["replay", str(out), "--json"])
    assert code == 2
    assert err == ""
    assert document["notes"] == []
    assert replay(out).status == "INCONCLUSIVE"


# --------------------------------------------------------------------------- #
# create_lock with the real authorities still rejects stale producers
# --------------------------------------------------------------------------- #


def test_created_lock_round_trips_through_parse_and_validate() -> None:
    calibration = '{"case_id":"c-1","state":"Calibration only.","expected_label":"billing"}\n'
    lock = create_lock(make_contract(), calibration, verification_jsonl(), make_identity())
    parsed = parse_lock(canonical_json(to_data(lock)).decode("utf-8"))
    assert parsed == lock
    validate_lock(parsed)
    assert parsed.replay_engine_version == CURRENT_ENGINE
    assert isinstance(parsed.verification_cases[0], Case)
