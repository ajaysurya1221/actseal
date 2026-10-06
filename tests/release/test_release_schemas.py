"""Published release-receipt schemas agree with the receipts the release helper actually writes.

The three Draft 2020-12 schemas under ``docs/release-schemas`` describe the
promotion profile of the build, post-publication and release receipts. They are
validated here with the dev-only ``jsonschema`` validator over a local,
non-fetching registry, against documents produced by ``tools/check_release.py``
itself (not hand-written copies): a tagged build receipt, the release receipt
emitted by ``release_receipt`` and, in the ``packaging``-marked test, the
post-publication receipt from the real-wheel ``postpublish`` chain. Inspection-only
cases (a rehearsal build, a ``file://`` index, missing attestations) must never
validate. Every strictness boundary from REVIEW 09R4 has a schema negative here
and a helper negative in ``test_strict_receipts.py``; where JSON Schema is weaker
than the helper (``1.0`` satisfies ``const: 1``, cross-field equality) the test
records the helper as the authority.
"""

from __future__ import annotations

import copy
import json
import sys
import types
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from release_support import (
    ALPHA,
    ROOT,
    STABLE,
    build_receipt_document,
    load_tool,
    names,
    postpublish_document,
    release_distributions,
    write_fake_distributions,
    write_fake_index,
    write_json,
    write_sums,
)

SCHEMAS = ROOT / "docs" / "release-schemas"
SCHEMA_FILES = (
    "build-receipt.schema.json",
    "postpublish-receipt.schema.json",
    "release-receipt.schema.json",
)
VERSION = "1.0.0"
SchemaDocument = bool | Mapping[str, Any]
type ObjectPath = tuple[str | int, ...]


def _load(name: str) -> dict[str, Any]:
    document = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _registry() -> Registry[SchemaDocument]:
    """Only the three committed release schemas resolve; nothing is retrieved."""
    registry: Registry[SchemaDocument] = Registry()
    return registry.with_resources(
        (str(schema["$id"]), Resource.from_contents(cast(SchemaDocument, schema)))
        for schema in (_load(name) for name in SCHEMA_FILES)
    )


def _validator(name: str) -> Draft202012Validator:
    schema = _load(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry())


VALIDATORS = {name: _validator(name) for name in SCHEMA_FILES}


def valid(name: str, instance: object) -> None:
    VALIDATORS[name].validate(instance)


def invalid(name: str, instance: object) -> None:
    with pytest.raises(ValidationError):
        VALIDATORS[name].validate(instance)


def error_paths(name: str, instance: object) -> set[tuple[str | int, ...]]:
    return {tuple(error.absolute_path) for error in VALIDATORS[name].iter_errors(instance)}


def at(document: Any, path: ObjectPath) -> dict[str, Any]:
    current: Any = document
    for key in path:
        current = current[key]
    assert isinstance(current, dict)
    return current


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


# --------------------------------------------------------------------------- #
# Schema files and the non-fetching registry
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", SCHEMA_FILES)
def test_schema_files_are_strict_draft_2020_12_documents(name: str) -> None:
    schema = _load(name)
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert str(schema["$id"]).startswith("urn:actseal:schema:")
    assert str(schema["$id"]).endswith(":1")
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == set(schema["required"])
    assert isinstance(schema["title"], str)
    assert isinstance(schema["description"], str)
    assert "cryptographic" not in schema["description"] or (
        "no" in schema["description"].lower() and "not claim" in schema["description"]
    )


def test_cross_schema_references_resolve_locally_and_unknown_ones_fail() -> None:
    release = _load("release-receipt.schema.json")
    refs = json.dumps(release)
    assert "urn:actseal:schema:build-receipt:1#/$defs/" in refs
    assert "urn:actseal:schema:postpublish-receipt:1#/$defs/EmbeddedPostpublish" in refs
    probe = Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": "urn:actseal:schema:missing:1",
        },
        registry=_registry(),
    )
    with pytest.raises(Unresolvable):
        probe.validate({})


def test_schema_index_lists_every_release_schema() -> None:
    readme = (ROOT / "docs" / "schemas" / "README.md").read_text(encoding="utf-8")
    for name in SCHEMA_FILES:
        assert f"[{name}](../release-schemas/{name})" in readme, name
    assert "uv.lock" in readme
    assert sorted(path.name for path in SCHEMAS.iterdir()) == sorted(SCHEMA_FILES)


# --------------------------------------------------------------------------- #
# Receipts the helper actually writes
# --------------------------------------------------------------------------- #


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    directory = tmp_path / "dist"
    write_fake_distributions(directory, VERSION)
    return directory


def generated_build_receipt(
    tool: types.ModuleType, dist: Path, *, ref: str, sha: str | None, run: str | None
) -> dict[str, Any]:
    document = tool.build_receipt(
        ROOT,
        tool.inspect_distributions(dist, VERSION),
        version=VERSION,
        ref=ref,
        sha=sha,
        run_id=run,
        run_attempt="1" if run else None,
    )
    return {str(key): value for key, value in document.items()}


def test_tagged_build_receipt_validates(tool: types.ModuleType, dist: Path, tmp_path: Path) -> None:
    receipt = generated_build_receipt(
        tool, dist, ref=f"refs/tags/v{VERSION}", sha="c" * 40, run="42"
    )
    valid("build-receipt.schema.json", receipt)
    assert receipt["lock_sha256"] == tool.sha256_file(ROOT / "uv.lock")
    tool._write_json(tmp_path / "build-receipt.json", receipt)
    valid("build-receipt.schema.json", tool._read_json(tmp_path / "build-receipt.json", "build"))
    tool.validate_build_receipt(receipt, VERSION, tool.inspect_distributions(dist, VERSION))


def test_rehearsal_build_receipt_is_inspection_only(tool: types.ModuleType, dist: Path) -> None:
    rehearsal = generated_build_receipt(tool, dist, ref="refs/heads/main", sha=None, run=None)
    assert rehearsal["tag"] is None
    assert rehearsal["workflow_run"] is None
    paths = error_paths("build-receipt.schema.json", rehearsal)
    assert {("tag",), ("ref",), ("source_commit",), ("workflow_run",)} <= paths
    with pytest.raises(tool.ReleaseCheckError):
        tool.validate_build_receipt(rehearsal, VERSION, tool.inspect_distributions(dist, VERSION))
    tagged_without_run = generated_build_receipt(
        tool, dist, ref=f"refs/tags/v{VERSION}", sha="c" * 40, run=None
    )
    assert error_paths("build-receipt.schema.json", tagged_without_run) == {("workflow_run",)}


@pytest.fixture
def promotion(tool: types.ModuleType, dist: Path, tmp_path: Path) -> dict[str, Any]:
    """The release receipt as ``release_receipt`` actually emits and writes it."""
    files = {name: dist / name for name in names(VERSION)}
    sums = write_sums(tmp_path / "SHA256SUMS", files)
    out = tmp_path / "release-receipt.json"
    emitted = tool.release_receipt(
        version=VERSION,
        dist=dist,
        sums_path=sums,
        build_receipt_path=write_json(
            tmp_path / "build.json", build_receipt_document(VERSION, files)
        ),
        postpublish_path=write_json(tmp_path / "post.json", postpublish_document(VERSION, files)),
        artifact_id="987654321",
        artifact_digest="b" * 64,
        run_id="42",
        run_attempt="3",
        verify_result="success",
        out=out,
    )
    written = tool._read_json(out, "release receipt")
    assert written == emitted
    return {str(key): value for key, value in written.items()}


def test_emitted_release_receipt_validates(promotion: dict[str, Any]) -> None:
    valid("release-receipt.schema.json", promotion)
    run = promotion["workflow_run"]
    assert (run["build_attempt"], run["verification_attempt"]) == ("1", "3")
    assert promotion["artifact"]["digest"] == "sha256:" + "b" * 64
    # The embedded evidence is the post-publication body under the receipt-level fields.
    valid(
        "postpublish-receipt.schema.json",
        {
            "schema_version": 1,
            "kind": "actseal-postpublish-receipt",
            "version": VERSION,
            "ok": True,
            **promotion["verification"]["postpublish"],
        },
    )


def test_release_fixture_documents_match_the_schemas(dist: Path) -> None:
    files = {name: dist / name for name in names(VERSION)}
    valid("build-receipt.schema.json", build_receipt_document(VERSION, files))
    valid("postpublish-receipt.schema.json", postpublish_document(VERSION, files))


# --------------------------------------------------------------------------- #
# Exact field sets: every object level rejects unknown and missing fields
# --------------------------------------------------------------------------- #

RELEASE_OBJECTS: list[ObjectPath] = [
    (),
    ("workflow_run",),
    ("artifact",),
    ("distributions", 0),
    ("verification",),
    ("verification", "postpublish"),
    ("verification", "postpublish", "published_metadata"),
    ("verification", "postpublish", "files", 0),
    ("verification", "postpublish", "files", 0, "provenance"),
    ("verification", "postpublish", "files", 0, "provenance", "publishers", 0),
    ("verification", "postpublish", "checks"),
]
POSTPUBLISH_OBJECTS: list[ObjectPath] = [
    (),
    ("published_metadata",),
    ("files", 0),
    ("files", 0, "provenance"),
    ("files", 0, "provenance", "publishers", 0),
    ("checks",),
]
BUILD_OBJECTS: list[ObjectPath] = [(), ("workflow_run",), ("distributions", 0)]


@pytest.mark.parametrize("path", RELEASE_OBJECTS)
def test_release_schema_rejects_unknown_and_missing_fields_at_every_level(
    promotion: dict[str, Any], path: ObjectPath
) -> None:
    extended = copy.deepcopy(promotion)
    at(extended, path)["unexpected"] = "unreviewed field"
    invalid("release-receipt.schema.json", extended)
    for key in at(promotion, path):
        reduced = copy.deepcopy(promotion)
        del at(reduced, path)[key]
        invalid("release-receipt.schema.json", reduced)


@pytest.mark.parametrize("path", POSTPUBLISH_OBJECTS)
def test_postpublish_schema_rejects_unknown_and_missing_fields_at_every_level(
    dist: Path, path: ObjectPath
) -> None:
    document = postpublish_document(VERSION, {name: dist / name for name in names(VERSION)})
    extended = copy.deepcopy(document)
    at(extended, path)["unexpected"] = 1
    invalid("postpublish-receipt.schema.json", extended)
    for key in at(document, path):
        reduced = copy.deepcopy(document)
        del at(reduced, path)[key]
        invalid("postpublish-receipt.schema.json", reduced)


@pytest.mark.parametrize("path", BUILD_OBJECTS)
def test_build_schema_rejects_unknown_and_missing_fields_at_every_level(
    tool: types.ModuleType, dist: Path, path: ObjectPath
) -> None:
    document = generated_build_receipt(
        tool, dist, ref=f"refs/tags/v{VERSION}", sha="c" * 40, run="42"
    )
    extended = copy.deepcopy(document)
    at(extended, path)["unexpected"] = None
    invalid("build-receipt.schema.json", extended)
    for key in at(document, path):
        reduced = copy.deepcopy(document)
        del at(reduced, path)[key]
        invalid("build-receipt.schema.json", reduced)


# --------------------------------------------------------------------------- #
# Strictness boundaries from REVIEW 09R4
# --------------------------------------------------------------------------- #


def set_path(document: dict[str, Any], path: ObjectPath, key: str, value: object) -> dict[str, Any]:
    changed = copy.deepcopy(document)
    at(changed, path)[key] = value
    return changed


RUN: ObjectPath = ("workflow_run",)
POST: ObjectPath = ("verification", "postpublish")
META: ObjectPath = (*POST, "published_metadata")
FILE0: ObjectPath = (*POST, "files", 0)
PROV0: ObjectPath = (*FILE0, "provenance")
CHECKS: ObjectPath = (*POST, "checks")


@pytest.mark.parametrize(
    ("path", "key", "value"),
    [
        ((), "schema_version", 2),
        ((), "schema_version", "1"),
        ((), "schema_version", True),
        ((), "kind", "actseal-build-receipt"),
        ((), "version", "1.0"),
        ((), "version", "1.0.0\n"),
        ((), "tag", "1.0.0"),
        ((), "source_commit", "C" * 40),
        ((), "source_commit", "c" * 39),
        ((), "lock_sha256", "D" * 64),
        ((), "lock_sha256", None),
        ((), "note", "Contains credentials."),
        ((), "note", None),
        ((), "distributions", []),
        (RUN, "id", "0"),
        (RUN, "id", "01"),
        (RUN, "id", "١٢"),
        (RUN, "id", 42),
        (RUN, "build_attempt", "1\n"),
        (RUN, "build_url", "https://github.com/other/repo/actions/runs/42/attempts/1"),
        (RUN, "verification_url", "https://github.com/ajaysurya1221/actseal/actions/runs/42"),
        (RUN, "verification_url", None),
        (("artifact",), "digest", "b" * 64),
        (("artifact",), "digest", "sha256:" + "B" * 64),
        (("artifact",), "id", "latest"),
        (("distributions", 0), "size", 0),
        (("distributions", 0), "size", 1.5),
        (("distributions", 0), "size", "1"),
        (("distributions", 0), "sha256", "e" * 63),
        (("distributions", 0), "filename", "actseal-1.0.0-py3-none-win_amd64.whl"),
        (("verification",), "verify_matrix", "failure"),
        (POST, "index", "file:///not-pypi"),
        (POST, "index", "https://test.pypi.org"),
        (POST, "note", "Signatures were cryptographically verified."),
        (META, "yanked", True),
        (META, "yanked", None),
        (META, "classifiers", STABLE),
        (META, "classifiers", []),
        (META, "classifiers", [ALPHA]),
        (META, "summary", ""),
        (META, "name", "actseal2"),
        (FILE0, "url", "https://example.invalid/actseal-1.0.0-py3-none-any.whl"),
        (FILE0, "matches_build", False),
        (FILE0, "declared_sha256", "e" * 65),
        (PROV0, "present", False),
        (PROV0, "attestations", 0),
        (PROV0, "attestations", True),
        (PROV0, "attestations", 1.5),
        (PROV0, "publishers", []),
        (PROV0, "subject_sha256", None),
        ((*PROV0, "publishers", 0), "repository", "someone/else"),
        ((*PROV0, "publishers", 0), "environment", "release"),
        ((*PROV0, "publishers", 0), "workflow", "ci.yml"),
        (CHECKS, "demo_exit", 99),
        (CHECKS, "demo_exit", False),
        (CHECKS, "bad_replay_exit", 0),
        (CHECKS, "fixed_replay_exit", 1),
        (CHECKS, "demo_bad_status", "PASS"),
        (CHECKS, "demo_fixed_status", "BLOCK"),
        (CHECKS, "installed_outside_checkout", False),
        (CHECKS, "version_output", "actseal 1.0.0\n"),
    ],
)
def test_release_schema_rejects_each_strictness_boundary(
    promotion: dict[str, Any], path: ObjectPath, key: str, value: object
) -> None:
    invalid("release-receipt.schema.json", set_path(promotion, path, key, value))


def test_release_schema_requires_exactly_two_unique_distributions(
    promotion: dict[str, Any],
) -> None:
    one = {**promotion, "distributions": promotion["distributions"][:1]}
    invalid("release-receipt.schema.json", one)
    three = {
        **promotion,
        "distributions": [*promotion["distributions"], promotion["distributions"][0]],
    }
    invalid("release-receipt.schema.json", three)
    twice = {**promotion, "distributions": [promotion["distributions"][0]] * 2}
    invalid("release-receipt.schema.json", twice)
    files = promotion["verification"]["postpublish"]["files"]
    doubled = set_path(promotion, POST, "files", [files[0]] * 2)
    invalid("release-receipt.schema.json", doubled)


def test_schema_const_one_admits_1_point_0_but_the_helper_does_not(
    tool: types.ModuleType, promotion: dict[str, Any]
) -> None:
    """JSON Schema treats 1.0 as the integer 1; promotion keeps the exact-integer check."""
    lax = {**promotion, "schema_version": 1.0}
    valid("release-receipt.schema.json", lax)
    with pytest.raises(tool.ReleaseCheckError, match="integer 1"):
        tool.validate_release_receipt(lax, VERSION, None)


def test_cross_field_rules_stay_with_the_helper(
    tool: types.ModuleType, promotion: dict[str, Any]
) -> None:
    """Shapes the schema accepts but promotion rejects: these equalities are not expressible."""
    mismatched_tag = {**promotion, "tag": "v1.0.1"}
    valid("release-receipt.schema.json", mismatched_tag)
    with pytest.raises(tool.ReleaseCheckError, match="tag"):
        tool.validate_release_receipt(mismatched_tag, VERSION, None)
    wrong_attempt_url = set_path(
        promotion,
        RUN,
        "build_url",
        "https://github.com/ajaysurya1221/actseal/actions/runs/42/attempts/2",
    )
    valid("release-receipt.schema.json", wrong_attempt_url)
    with pytest.raises(tool.ReleaseCheckError, match="build_url"):
        tool.validate_release_receipt(wrong_attempt_url, VERSION, None)
    later_build = set_path(promotion, RUN, "build_attempt", "4")
    later_build["workflow_run"]["build_url"] = later_build["workflow_run"]["build_url"][:-1] + "4"
    valid("release-receipt.schema.json", later_build)
    with pytest.raises(tool.ReleaseCheckError, match="later than"):
        tool.validate_release_receipt(later_build, VERSION, None)
    foreign_subject = set_path(promotion, PROV0, "subject_sha256", "0" * 64)
    valid("release-receipt.schema.json", foreign_subject)
    with pytest.raises(tool.ReleaseCheckError, match="subject digest"):
        tool.validate_release_receipt(foreign_subject, VERSION, None)
    understated = set_path(
        promotion,
        PROV0,
        "publishers",
        [promotion["verification"]["postpublish"]["files"][0]["provenance"]["publishers"][0]] * 2,
    )
    valid("release-receipt.schema.json", understated)
    with pytest.raises(tool.ReleaseCheckError, match="below publisher count"):
        tool.validate_release_receipt(understated, VERSION, None)


def test_zero_major_metadata_may_keep_alpha_but_1x_requires_stable(
    dist: Path, tmp_path: Path
) -> None:
    files = {name: dist / name for name in names(VERSION)}
    document = postpublish_document(VERSION, files)
    at(document, ("published_metadata",))["classifiers"] = [ALPHA]
    invalid("postpublish-receipt.schema.json", document)
    legacy_files = write_fake_distributions(tmp_path / "dist-0.9.0", "0.9.0")
    legacy = postpublish_document("0.9.0", legacy_files)
    at(legacy, ("published_metadata",))["classifiers"] = [ALPHA]
    valid("postpublish-receipt.schema.json", legacy)
    at(legacy, ("published_metadata",))["classifiers"] = []
    invalid("postpublish-receipt.schema.json", legacy)


def test_ambiguous_json_never_reaches_the_schemas(tool: types.ModuleType, tmp_path: Path) -> None:
    """Duplicate keys and nonfinite numbers are decoding errors in the helper, by design."""
    path = tmp_path / "receipt.json"
    path.write_text('{"verify_matrix": "failure", "verify_matrix": "success"}', encoding="utf-8")
    with pytest.raises(tool.ReleaseCheckError, match="duplicate"):
        tool._read_json(path, "receipt")
    path.write_text('{"note": NaN}', encoding="utf-8")
    with pytest.raises(tool.ReleaseCheckError, match="nonfinite"):
        tool._read_json(path, "receipt")
    path.write_text('{"size": 1e999}', encoding="utf-8")
    with pytest.raises(tool.ReleaseCheckError, match="nonfinite"):
        tool._read_json(path, "receipt")


# --------------------------------------------------------------------------- #
# The real post-publication receipt (packaging marker)
# --------------------------------------------------------------------------- #


@pytest.mark.packaging
def test_real_postpublish_receipt_matches_the_schema_shape_but_not_the_official_profile(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    files = release_distributions(tmp_path / "dist")
    version = tool.agreed_version(ROOT)
    data = {name: path.read_bytes() for name, path in files.items()}
    sums = write_sums(tmp_path / "SHA256SUMS", files)
    base = write_fake_index(tmp_path / "index", version, data)
    receipt = tool.postpublish(
        version=version,
        sums_path=sums,
        workdir=tmp_path / "work",
        out=tmp_path / "postpublish-receipt.json",
        checkout=ROOT,
        base_url=base,
        wait_seconds=0,
        python=sys.executable,
        allow_missing_attestations=False,
    )
    document = tool._read_json(tmp_path / "postpublish-receipt.json", "post-publication receipt")
    assert document == receipt
    # A local file:// index is inspection-only: the only violations are the index and file URLs.
    assert error_paths("postpublish-receipt.schema.json", document) == {
        ("index",),
        ("files", 0, "url"),
        ("files", 1, "url"),
    }
    official = copy.deepcopy(document)
    official["index"] = "https://pypi.org"
    for entry in official["files"]:
        entry["url"] = f"https://files.pythonhosted.org/packages/{entry['filename']}"
    valid("postpublish-receipt.schema.json", official)
    inventory = tool.inspect_distributions(files[names(version)[0]].parent, version)
    tool.validate_postpublish_receipt(official, version, inventory, official_index=True)
    with pytest.raises(tool.ReleaseCheckError, match="not official"):
        tool.validate_postpublish_receipt(document, version, inventory, official_index=True)

    missing = write_fake_index(tmp_path / "index-unattested", version, data, provenance_for=[])
    tolerated = tool.postpublish(
        version=version,
        sums_path=sums,
        workdir=tmp_path / "work-unattested",
        out=tmp_path / "unattested.json",
        checkout=ROOT,
        base_url=missing,
        wait_seconds=0,
        python=sys.executable,
        allow_missing_attestations=True,
    )
    assert all(entry["provenance"]["present"] is False for entry in tolerated["files"])
    assert ("files", 0, "provenance", "present") in error_paths(
        "postpublish-receipt.schema.json", tolerated
    )
    with pytest.raises(tool.ReleaseCheckError):
        tool.validate_postpublish_receipt(tolerated, version, inventory, official_index=True)
