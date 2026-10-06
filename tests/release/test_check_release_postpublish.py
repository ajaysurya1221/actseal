"""``postpublish`` unit tests: exit codes, hashes, metadata, attestations, partial publication.

No network and no real wheel: the index is served over ``file://`` URLs and the
installed-demo expectations are exercised through the pure ``assert_demo_outcomes``.
"""

from __future__ import annotations

import base64
import json
import sys
import types
from collections.abc import Mapping
from pathlib import Path

import pytest
from release_support import (
    ALPHA,
    PUBLISHER,
    STABLE,
    attestation,
    load_tool,
    names,
    provenance_document,
    sha256_hex,
    statement,
    write_fake_index,
    write_sdist,
    write_sums,
    write_text,
    write_wheel,
)

VERSION = "1.0.0"


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


def result(
    tool: types.ModuleType,
    code: int,
    document: dict[str, object] | None = None,
    stdout: str | None = None,
) -> object:
    text = stdout if stdout is not None else json.dumps(document or {}) + "\n"
    return tool.CommandResult(("actseal",), code, text, "")


def demo_document(bad: str = "BLOCK", fixed: str = "PASS") -> dict[str, object]:
    return {"ok": True, "runs": {"bad": {"status": bad}, "fixed": {"status": fixed}}}


def outcomes(
    tool: types.ModuleType,
    *,
    version_code: int = 0,
    version_text: str = f"actseal {VERSION}\n",
    demo_code: int = 0,
    demo: dict[str, object] | None = None,
    fixed_code: int = 0,
    fixed_status: str = "PASS",
    bad_code: int = 1,
    bad_status: str = "BLOCK",
) -> dict[str, object]:
    checks = tool.assert_demo_outcomes(
        VERSION,
        result(tool, version_code, stdout=version_text),
        result(tool, demo_code, demo or demo_document()),
        result(tool, fixed_code, {"status": fixed_status}),
        result(tool, bad_code, {"status": bad_status}),
    )
    return {str(key): value for key, value in checks.items()}


def test_expected_outcomes_pass(tool: types.ModuleType) -> None:
    checks = outcomes(tool)
    assert checks == {
        "version_output": f"actseal {VERSION}",
        "demo_exit": 0,
        "fixed_replay_exit": 0,
        "bad_replay_exit": 1,
        "demo_bad_status": "BLOCK",
        "demo_fixed_status": "PASS",
    }


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"version_code": 1}, "--version exited 1"),
        ({"version_text": "actseal 0.1.0\n"}, "--version printed"),
        ({"demo_code": 1}, "wrong exit code: demo exited 1"),
        ({"demo_code": 3}, "wrong exit code: demo exited 3"),
        ({"fixed_code": 1}, "wrong exit code: fixed replay exited 1"),
        ({"bad_code": 0}, "wrong exit code: bad replay exited 0"),
        ({"bad_code": 3}, "wrong exit code: bad replay exited 3"),
        ({"demo": demo_document(bad="PASS")}, "demo bad run status is 'PASS'"),
        ({"demo": demo_document(fixed="BLOCK")}, "demo fixed run status is 'BLOCK'"),
        ({"fixed_status": "BLOCK"}, "fixed replay status is not PASS"),
        ({"bad_status": "INCONCLUSIVE"}, "bad replay status is not BLOCK"),
    ],
)
def test_every_wrong_exit_code_or_verdict_fails(
    tool: types.ModuleType, overrides: dict[str, object], fragment: str
) -> None:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        outcomes(tool, **overrides)  # type: ignore[arg-type]
    assert fragment in str(excinfo.value)


def test_non_json_output_fails(tool: types.ModuleType) -> None:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.assert_demo_outcomes(
            VERSION,
            result(tool, 0, stdout=f"actseal {VERSION}\n"),
            result(tool, 0, stdout="not json\n"),
            result(tool, 0, {"status": "PASS"}),
            result(tool, 1, {"status": "BLOCK"}),
        )
    assert "did not print JSON" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Index inspection over file:// (fails before any installation)
# --------------------------------------------------------------------------- #


@pytest.fixture
def published(tmp_path: Path) -> tuple[dict[str, bytes], Path]:
    store = tmp_path / "built"
    store.mkdir()
    paths = (write_wheel(store, VERSION), write_sdist(store, VERSION))
    files = {path.name: path.read_bytes() for path in paths}
    sums = write_sums(tmp_path / "SHA256SUMS", {path.name: path for path in paths})
    return files, sums


def run_postpublish(
    tool: types.ModuleType, base: str, sums: Path, tmp_path: Path, *, allow_missing: bool = False
) -> str:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.postpublish(
            version=VERSION,
            sums_path=sums,
            workdir=tmp_path / "work",
            out=tmp_path / "receipt.json",
            checkout=None,
            base_url=base,
            wait_seconds=0,
            python=sys.executable,
            allow_missing_attestations=allow_missing,
        )
    assert not (tmp_path / "receipt.json").exists()
    assert not (tmp_path / "work" / "venv").exists()
    return str(excinfo.value)


def test_partial_publication_is_a_loud_failure(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    wheel = names(VERSION)[0]
    base = write_fake_index(tmp_path / "index", VERSION, {wheel: files[wheel]})
    message = run_postpublish(tool, base, sums, tmp_path)
    assert "partial publication: PyPI has 1 of 2 expected files" in message
    assert "nothing will be re-uploaded or rebuilt" in message


def test_unexpected_published_file_fails(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    base = write_fake_index(
        tmp_path / "index", VERSION, {**files, "actseal-1.0.0-py3-none-win_amd64.whl": b"x"}
    )
    assert "unexpected files" in run_postpublish(tool, base, sums, tmp_path)


def test_release_not_visible_fails_after_waiting(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    _, sums = published
    base = write_fake_index(tmp_path / "index", "9.9.9", {})
    assert "not visible" in run_postpublish(tool, base, sums, tmp_path)


def test_downloaded_bytes_differing_from_the_build_fail(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    wheel, sdist = names(VERSION)
    base = write_fake_index(tmp_path / "index", VERSION, {wheel: b"tampered", sdist: files[sdist]})
    assert "downloaded sha256" in run_postpublish(tool, base, sums, tmp_path)


def test_declared_digest_differing_from_the_bytes_fails(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    wheel = names(VERSION)[0]
    base = write_fake_index(tmp_path / "index", VERSION, files, declared={wheel: "0" * 64})
    assert "PyPI declares sha256" in run_postpublish(tool, base, sums, tmp_path)


# --------------------------------------------------------------------------- #
# Published metadata
# --------------------------------------------------------------------------- #


def good_info(**overrides: object) -> dict[str, object]:
    info: dict[str, object] = {
        "name": "actseal",
        "version": VERSION,
        "summary": "fixture",
        "classifiers": [STABLE],
        "yanked": False,
    }
    info.update(overrides)
    return info


@pytest.mark.parametrize(
    ("info", "fragment"),
    [
        (good_info(name="actseal2"), "project name"),
        (good_info(version="1.0.1"), "reports version"),
        (good_info(yanked=True), "yanked"),
        (good_info(yanked=None), "yanked"),
        (good_info(classifiers=[ALPHA]), "lacks classifier"),
        (good_info(classifiers=[]), "lacks classifier"),
        (good_info(summary=""), "summary"),
        (good_info(classifiers=[STABLE, "Topic :: Other"]), "differs from wheel METADATA"),
    ],
)
def test_published_metadata_is_validated(
    tool: types.ModuleType,
    published: tuple[dict[str, bytes], Path],
    tmp_path: Path,
    info: Mapping[str, object],
    fragment: str,
) -> None:
    files, sums = published
    base = write_fake_index(tmp_path / "index", VERSION, files, info=info)
    assert fragment in run_postpublish(tool, base, sums, tmp_path)


def test_yanked_file_fails(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    base = write_fake_index(tmp_path / "index", VERSION, files, yanked=[names(VERSION)[1]])
    assert "is yanked" in run_postpublish(tool, base, sums, tmp_path)


def test_missing_info_block_fails(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    base = write_fake_index(tmp_path / "index", VERSION, files)
    release = tmp_path / "index" / "pypi" / "actseal" / VERSION / "json"
    document = json.loads(release.read_text(encoding="utf-8"))
    del document["info"]
    release.write_text(json.dumps(document), encoding="utf-8")
    assert "info must be an object" in run_postpublish(tool, base, sums, tmp_path)


def test_alpha_classifier_is_acceptable_only_below_1_0(tool: types.ModuleType) -> None:
    document = {"info": good_info(version="0.9.0", classifiers=[ALPHA]), "urls": []}
    assert tool._published_metadata(document, "0.9.0")["classifiers"] == [ALPHA]
    with pytest.raises(tool.ReleaseCheckError):
        tool._published_metadata({"info": good_info(classifiers=[ALPHA]), "urls": []}, VERSION)


# --------------------------------------------------------------------------- #
# Attestations: identity and subject inspection, never signature verification
# --------------------------------------------------------------------------- #


def wheel_sha(files: Mapping[str, bytes]) -> str:
    return sha256_hex(files[names(VERSION)[0]])


def test_missing_provenance_fails_unless_explicitly_allowed(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    base = write_fake_index(tmp_path / "index", VERSION, files, provenance_for=[names(VERSION)[1]])
    assert "no provenance/attestations" in run_postpublish(tool, base, sums, tmp_path)
    assert tool._provenance(base, VERSION, names(VERSION)[0], wheel_sha(files)) == {
        "present": False,
        "attestations": 0,
        "publishers": [],
        "subject_sha256": None,
    }
    sdist = names(VERSION)[1]
    present = tool._provenance(base, VERSION, sdist, sha256_hex(files[sdist]))
    assert present == {
        "present": True,
        "attestations": 1,
        "publishers": [PUBLISHER],
        "subject_sha256": sha256_hex(files[sdist]),
    }


def wheel_statement(files: Mapping[str, bytes], **overrides: object) -> str:
    document: dict[str, object] = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": names(VERSION)[0], "digest": {"sha256": wheel_sha(files)}}],
        "predicateType": "https://docs.pypi.org/attestations/publish/v1",
        "predicate": None,
    }
    document.update(overrides)
    return base64.b64encode(json.dumps(document).encode("utf-8")).decode("ascii")


def bad_provenances(files: Mapping[str, bytes]) -> list[tuple[str, dict[str, object], str]]:
    wheel = names(VERSION)[0]
    sha = wheel_sha(files)
    good = statement(wheel, sha)
    return [
        ("empty-bundles", {"attestation_bundles": []}, "has no bundles"),
        ("not-object", {"attestation_bundles": ["x"]}, "must be an object"),
        ("no-attestations", provenance_document(wheel, sha, attestations=[]), "no attestations"),
        (
            "wrong-repository",
            provenance_document(wheel, sha, publisher={**PUBLISHER, "repository": "x/y"}),
            "not the expected trusted publisher",
        ),
        (
            "wrong-environment",
            provenance_document(wheel, sha, publisher={**PUBLISHER, "environment": "release"}),
            "not the expected trusted publisher",
        ),
        (
            "wrong-workflow",
            provenance_document(wheel, sha, publisher={**PUBLISHER, "workflow": "ci.yml"}),
            "not the expected trusted publisher",
        ),
        (
            "missing-publisher-field",
            provenance_document(
                wheel, sha, publisher={k: v for k, v in PUBLISHER.items() if k != "kind"}
            ),
            "not the expected trusted publisher",
        ),
        (
            "malformed-base64",
            provenance_document(wheel, sha, attestations=[attestation("!!not-base64!!")]),
            "not base64 JSON",
        ),
        (
            "base64-not-json",
            provenance_document(
                wheel, sha, attestations=[attestation(base64.b64encode(b"nope").decode())]
            ),
            "not base64 JSON",
        ),
        (
            "wrong-statement-type",
            provenance_document(
                wheel,
                sha,
                attestations=[attestation(wheel_statement(files, _type="https://example/v9"))],
            ),
            "statement type is",
        ),
        (
            "no-subject",
            provenance_document(
                wheel, sha, attestations=[attestation(wheel_statement(files, subject=[]))]
            ),
            "has no subject",
        ),
        (
            "wrong-subject-digest",
            provenance_document(wheel, sha, attestations=[attestation(statement(wheel, "0" * 64))]),
            "do not name",
        ),
        (
            "wrong-subject-name",
            provenance_document(
                wheel, sha, attestations=[attestation(statement("other.whl", sha))]
            ),
            "do not name",
        ),
        (
            "missing-signature",
            provenance_document(
                wheel,
                sha,
                attestations=[{**attestation(good), "envelope": {"statement": good}}],
            ),
            "signature missing",
        ),
        (
            "missing-verification-material",
            provenance_document(
                wheel,
                sha,
                attestations=[
                    {k: v for k, v in attestation(good).items() if k != "verification_material"}
                ],
            ),
            "verification_material missing",
        ),
        (
            "unsupported-version",
            provenance_document(wheel, sha, attestations=[{**attestation(good), "version": 2}]),
            "unsupported attestation version",
        ),
    ]


def test_every_malformed_or_foreign_attestation_fails(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    seen: set[str] = set()
    for name, provenance, fragment in bad_provenances(files):
        base = write_fake_index(
            tmp_path / name,
            VERSION,
            files,
            provenance=provenance,
            provenance_for=[names(VERSION)[0]],
        )
        message = run_postpublish(tool, base, sums, tmp_path / f"run-{name}")
        assert fragment in message, (name, message)
        seen.add(name)
    assert len(seen) == len(bad_provenances(files))


def test_a_second_bundle_from_another_publisher_fails(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    wheel = names(VERSION)[0]
    good = provenance_document(wheel, wheel_sha(files))
    foreign = provenance_document(
        wheel, wheel_sha(files), publisher={**PUBLISHER, "repository": "x/y"}
    )
    first, second = good["attestation_bundles"], foreign["attestation_bundles"]
    assert isinstance(first, list)
    assert isinstance(second, list)
    merged = {"attestation_bundles": [*first, *second]}
    base = write_fake_index(tmp_path / "index", VERSION, files, provenance=merged)
    assert "bundle 1: publisher" in run_postpublish(tool, base, sums, tmp_path)


def test_sums_for_another_version_or_existing_workdir_fail(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, _ = published
    base = write_fake_index(tmp_path / "index", VERSION, files)
    stale = write_text(tmp_path / "stale", f"{sha256_hex(b'x')}  actseal-0.9.0.tar.gz\n")
    assert "does not describe 1.0.0" in run_postpublish(tool, base, stale, tmp_path)
    _, sums = published
    (tmp_path / "work").mkdir()
    assert "already exists" in run_postpublish(tool, base, sums, tmp_path)


def test_workdir_inside_checkout_is_refused(
    tool: types.ModuleType, published: tuple[dict[str, bytes], Path], tmp_path: Path
) -> None:
    files, sums = published
    base = write_fake_index(tmp_path / "index", VERSION, files)
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.postpublish(
            version=VERSION,
            sums_path=sums,
            workdir=tmp_path / "checkout" / "work",
            out=tmp_path / "receipt.json",
            checkout=tmp_path / "checkout",
            base_url=base,
            wait_seconds=0,
            python=sys.executable,
            allow_missing_attestations=False,
        )
    assert "must lie outside the checkout" in str(excinfo.value)
