"""Release promotion rejects ambiguous JSON and incomplete or extensible receipts.

These are CI-glue regressions, authored by Codex within Task09 ownership.
Fixtures are synthetic; no provider, GitHub or PyPI connection is made.
"""

from __future__ import annotations

import copy
import json
import types
from pathlib import Path
from typing import Any

import pytest
from release_support import (
    build_receipt_document,
    load_tool,
    postpublish_document,
    release_receipt_document,
    write_fake_distributions,
    write_sums,
)

VERSION = "1.0.0"
type ObjectPath = tuple[str | int, ...]


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


@pytest.fixture
def documents(tmp_path: Path) -> dict[str, Any]:
    files = write_fake_distributions(tmp_path / "dist", VERSION)
    return {
        "build": build_receipt_document(VERSION, files),
        "post": postpublish_document(VERSION, files),
        "release": release_receipt_document(VERSION, files),
    }


def validate(tool: types.ModuleType, documents: dict[str, Any], kind: str) -> None:
    reference = "release" if kind == "build" else "build"
    inventory = tool._distribution_inventory(documents[reference]["distributions"], "test")
    if kind == "build":
        tool.validate_build_receipt(documents[kind], VERSION, inventory)
    elif kind == "post":
        tool.validate_postpublish_receipt(documents[kind], VERSION, inventory, official_index=True)
    else:
        tool.validate_release_receipt(documents[kind], VERSION, inventory)


def at(document: dict[str, Any], path: ObjectPath) -> dict[str, Any]:
    current: Any = document
    for key in path:
        current = current[key]
    assert isinstance(current, dict)
    return current


STRICT_OBJECTS: list[tuple[str, ObjectPath]] = [
    ("build", ()),
    ("build", ("workflow_run",)),
    ("build", ("distributions", 0)),
    ("post", ()),
    ("post", ("published_metadata",)),
    ("post", ("files", 0)),
    ("post", ("files", 0, "provenance")),
    ("post", ("files", 0, "provenance", "publishers", 0)),
    ("post", ("checks",)),
    ("release", ()),
    ("release", ("workflow_run",)),
    ("release", ("artifact",)),
    ("release", ("distributions", 0)),
    ("release", ("verification",)),
    ("release", ("verification", "postpublish")),
    ("release", ("verification", "postpublish", "published_metadata")),
    ("release", ("verification", "postpublish", "files", 0)),
    ("release", ("verification", "postpublish", "files", 0, "provenance")),
    ("release", ("verification", "postpublish", "files", 0, "provenance", "publishers", 0)),
    ("release", ("verification", "postpublish", "checks")),
]


@pytest.mark.parametrize("kind", ["build", "post", "release"])
def test_complete_receipts_are_promotable(
    tool: types.ModuleType, documents: dict[str, Any], kind: str
) -> None:
    validate(tool, documents, kind)


@pytest.mark.parametrize(("kind", "path"), STRICT_OBJECTS)
def test_every_receipt_object_rejects_extensions(
    tool: types.ModuleType, documents: dict[str, Any], kind: str, path: ObjectPath
) -> None:
    at(documents[kind], path)["unexpected"] = "unreviewed field"
    with pytest.raises(tool.ReleaseCheckError):
        validate(tool, documents, kind)


@pytest.mark.parametrize(("kind", "path"), STRICT_OBJECTS)
def test_every_receipt_field_is_required(
    tool: types.ModuleType, documents: dict[str, Any], kind: str, path: ObjectPath
) -> None:
    for key in at(documents[kind], path):
        changed = copy.deepcopy(documents)
        del at(changed[kind], path)[key]
        with pytest.raises(tool.ReleaseCheckError):
            validate(tool, changed, kind)


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity", "1e999", "-1e999"])
@pytest.mark.parametrize("nested", [False, True])
def test_nonfinite_json_is_rejected_before_validation(
    tool: types.ModuleType, tmp_path: Path, raw: str, nested: bool
) -> None:
    path = tmp_path / "receipt.json"
    value = '{"items": [' + raw + "]}" if nested else raw
    path.write_text('{"value": ' + value + "}", encoding="utf-8")
    with pytest.raises(tool.ReleaseCheckError, match="nonfinite"):
        tool._read_json(path, "receipt")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_serialization_leaves_existing_receipt_untouched(
    tool: types.ModuleType, tmp_path: Path, value: float
) -> None:
    path = tmp_path / "receipt.json"
    path.write_bytes(b"original receipt\n")
    with pytest.raises(tool.ReleaseCheckError, match="finite JSON"):
        tool._write_json(path, {"checks": {"unknown": [value]}})
    assert path.read_bytes() == b"original receipt\n"


@pytest.mark.parametrize(
    "raw",
    [
        '{"ok": false, "ok": true}',
        '{"checks": {"demo_exit": 1, "demo_exit": 0}}',
        '{"checks": [{"key": 1, "key": 2}]}',
        '{"key": 1, "\\u006bey": 2}',
    ],
)
def test_duplicate_keys_are_rejected_at_every_depth(
    tool: types.ModuleType, tmp_path: Path, raw: str
) -> None:
    path = tmp_path / "receipt.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(tool.ReleaseCheckError, match="duplicate"):
        tool._read_json(path, "receipt")


@pytest.mark.parametrize("bad", ["0", "00", "01", "²", "\u0661", "-1", "+1", "1\n", 1, 1.0, True])
@pytest.mark.parametrize(
    ("kind", "path", "key"),
    [
        ("build", ("workflow_run",), "id"),
        ("build", ("workflow_run",), "attempt"),
        ("release", ("workflow_run",), "id"),
        ("release", ("workflow_run",), "build_attempt"),
        ("release", ("workflow_run",), "verification_attempt"),
        ("release", ("artifact",), "id"),
    ],
)
def test_identifiers_are_positive_ascii_decimal_strings(
    tool: types.ModuleType,
    documents: dict[str, Any],
    *,
    kind: str,
    path: ObjectPath,
    key: str,
    bad: object,
) -> None:
    at(documents[kind], path)[key] = bad
    with pytest.raises(tool.ReleaseCheckError, match="positive ASCII numeric"):
        validate(tool, documents, kind)


@pytest.mark.parametrize("kind", ["build", "post", "release"])
@pytest.mark.parametrize("bad", [0, -1, True, 1.0, "1"])
def test_file_sizes_must_be_positive_exact_integers(
    tool: types.ModuleType, documents: dict[str, Any], kind: str, bad: object
) -> None:
    inventory_key = "files" if kind == "post" else "distributions"
    documents[kind][inventory_key][0]["size"] = bad
    with pytest.raises(tool.ReleaseCheckError, match="positive integer"):
        validate(tool, documents, kind)


@pytest.mark.parametrize("kind", ["build", "post", "release"])
@pytest.mark.parametrize("bad", [True, 1.0, "1"])
def test_schema_versions_are_exact_integers(
    tool: types.ModuleType, documents: dict[str, Any], kind: str, bad: object
) -> None:
    documents[kind]["schema_version"] = bad
    with pytest.raises(tool.ReleaseCheckError, match="integer 1"):
        validate(tool, documents, kind)


def test_attestation_count_cannot_understate_publisher_bundles(
    tool: types.ModuleType, documents: dict[str, Any]
) -> None:
    provenance = documents["post"]["files"][0]["provenance"]
    provenance["publishers"].append(dict(provenance["publishers"][0]))
    with pytest.raises(tool.ReleaseCheckError, match="below publisher count"):
        validate(tool, documents, "post")
    provenance["attestations"] = 2
    validate(tool, documents, "post")


@pytest.mark.parametrize("bad", [None, False, 0, "", "Cryptographically verified", float("nan")])
def test_final_note_is_the_literal_credential_statement(
    tool: types.ModuleType, documents: dict[str, Any], bad: object
) -> None:
    documents["release"]["note"] = bad
    with pytest.raises(tool.ReleaseCheckError, match="note is not verbatim"):
        validate(tool, documents, "release")


def test_duplicate_success_cannot_trigger_any_github_command(
    tool: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = write_fake_distributions(tmp_path / "dist", VERSION)
    sums = write_sums(tmp_path / "SHA256SUMS", files)
    receipt = tmp_path / "release-receipt.json"
    raw = json.dumps(release_receipt_document(VERSION, files))
    raw = raw.replace(
        '"verify_matrix": "success"',
        '"verify_matrix": "failure", "verify_matrix": "success"',
    )
    receipt.write_text(raw, encoding="utf-8")

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("invalid receipt reached GitHub")

    monkeypatch.setattr(tool, "_gh", forbidden)
    with pytest.raises(tool.ReleaseCheckError, match="duplicate"):
        tool.mirror(
            tag=f"v{VERSION}",
            dist=tmp_path / "dist",
            sums_path=sums,
            receipt_path=receipt,
            gh_binary="must-not-run",
        )
