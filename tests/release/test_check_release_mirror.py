"""``mirror``: create or update only a draft GitHub release; never clobber or touch a published one.

A fake ``gh`` executable records every invocation and replays a scenario, so the
tests assert the exact mutation commands without network or credentials.
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest
from release_support import (
    load_tool,
    names,
    python_script,
    sha256_hex,
    write_fake_distributions,
    write_sums,
    write_text,
)

VERSION = "1.0.0"
TAG = f"v{VERSION}"
ASSETS = (*names(VERSION), "SHA256SUMS", "release-receipt.json")

_FAKE_GH = """
import json
import pathlib
import sys

SCENARIO = json.loads(pathlib.Path({scenario!r}).read_text(encoding="utf-8"))
LOG = pathlib.Path({log!r})
args = sys.argv[1:]
with LOG.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\\n")
if args[:2] == ["release", "view"]:
    sys.stdout.write(SCENARIO["view_stdout"])
    sys.stderr.write(SCENARIO["view_stderr"])
    sys.exit(SCENARIO["view_code"])
if args[:2] == ["release", "download"]:
    name = args[args.index("--pattern") + 1]
    target = pathlib.Path(args[args.index("--dir") + 1]) / name
    target.write_bytes(bytes.fromhex(SCENARIO["downloads"][name]))
    sys.exit(0)
sys.exit(0)
"""


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


class FakeGitHub:
    def __init__(self, directory: Path) -> None:
        self.scenario = directory / "scenario.json"
        self.log = directory / "gh.log"
        self.binary = python_script(
            directory / "gh", _FAKE_GH.format(scenario=str(self.scenario), log=str(self.log))
        )

    def configure(
        self,
        *,
        view_code: int,
        view_stdout: str = "",
        view_stderr: str = "",
        downloads: dict[str, bytes] | None = None,
    ) -> None:
        document = {
            "view_code": view_code,
            "view_stdout": view_stdout,
            "view_stderr": view_stderr,
            "downloads": {name: data.hex() for name, data in (downloads or {}).items()},
        }
        self.scenario.write_text(json.dumps(document), encoding="utf-8")

    def calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    dist = tmp_path / "dist"
    files = write_fake_distributions(dist, VERSION)
    sums = write_sums(tmp_path / "SHA256SUMS", files)
    receipt = write_text(
        tmp_path / "release-receipt.json",
        json.dumps(
            {"schema_version": 1, "kind": "actseal-release-receipt", "version": VERSION, "tag": TAG}
        ),
    )
    return {"dist": dist, "sums": sums, "receipt": receipt}


@pytest.fixture
def github(tmp_path: Path) -> FakeGitHub:
    directory = tmp_path / "gh-home"
    directory.mkdir()
    return FakeGitHub(directory)


def run_mirror(tool: types.ModuleType, inputs: dict[str, Path], github: FakeGitHub) -> list[str]:
    actions = tool.mirror(
        tag=TAG,
        dist=inputs["dist"],
        sums_path=inputs["sums"],
        receipt_path=inputs["receipt"],
        gh_binary=str(github.binary),
    )
    return [str(action) for action in actions]


def mirror_failure(tool: types.ModuleType, inputs: dict[str, Path], github: FakeGitHub) -> str:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        run_mirror(tool, inputs, github)
    return str(excinfo.value)


def mutations(calls: list[list[str]]) -> list[list[str]]:
    return [call for call in calls if call[:2] in (["release", "create"], ["release", "upload"])]


def test_missing_release_creates_a_draft_and_uploads_every_asset(
    tool: types.ModuleType, inputs: dict[str, Path], github: FakeGitHub
) -> None:
    github.configure(view_code=1, view_stderr="release not found\n")
    actions = run_mirror(tool, inputs, github)
    assert actions[0] == f"created draft release {TAG}"
    assert set(actions[1:]) == {f"uploaded {name}" for name in ASSETS}
    calls = github.calls()
    create = next(call for call in calls if call[:2] == ["release", "create"])
    assert "--draft" in create
    assert "--verify-tag" in create
    assert create[2] == TAG
    notes = Path(create[create.index("--notes-file") + 1]).read_text(encoding="utf-8")
    assert "Draft release for Actseal 1.0.0" in notes
    assert "wait for the real PyPI recording" in notes
    uploads = [call for call in calls if call[:2] == ["release", "upload"]]
    assert len(uploads) == 1
    assert sorted(Path(item).name for item in uploads[0][3:]) == sorted(ASSETS)
    assert not any("--clobber" in call for call in calls)


def test_existing_draft_with_identical_assets_uploads_only_the_missing_ones(
    tool: types.ModuleType, inputs: dict[str, Path], github: FakeGitHub
) -> None:
    wheel = names(VERSION)[0]
    github.configure(
        view_code=0,
        view_stdout=json.dumps({"isDraft": True, "tagName": TAG, "assets": [{"name": wheel}]}),
        downloads={wheel: (inputs["dist"] / wheel).read_bytes()},
    )
    actions = run_mirror(tool, inputs, github)
    assert f"asset {wheel} already identical; skipped" in actions
    assert set(actions) - {f"asset {wheel} already identical; skipped"} == {
        f"uploaded {name}" for name in ASSETS if name != wheel
    }
    calls = github.calls()
    assert not any(call[:2] == ["release", "create"] for call in calls)
    uploads = [call for call in calls if call[:2] == ["release", "upload"]]
    assert len(uploads) == 1
    assert wheel not in {Path(item).name for item in uploads[0][3:]}
    assert not any("--clobber" in call for call in calls)


def test_differing_existing_asset_refuses_to_overwrite(
    tool: types.ModuleType, inputs: dict[str, Path], github: FakeGitHub
) -> None:
    sdist = names(VERSION)[1]
    github.configure(
        view_code=0,
        view_stdout=json.dumps({"isDraft": True, "tagName": TAG, "assets": [{"name": sdist}]}),
        downloads={sdist: b"different bytes"},
    )
    message = mirror_failure(tool, inputs, github)
    assert "refusing to overwrite" in message
    assert mutations(github.calls()) == []


def test_published_release_is_never_modified(
    tool: types.ModuleType, inputs: dict[str, Path], github: FakeGitHub
) -> None:
    github.configure(
        view_code=0, view_stdout=json.dumps({"isDraft": False, "tagName": TAG, "assets": []})
    )
    assert "already published; refusing to modify" in mirror_failure(tool, inputs, github)
    assert mutations(github.calls()) == []


def test_unexpected_gh_error_is_not_treated_as_missing_release(
    tool: types.ModuleType, inputs: dict[str, Path], github: FakeGitHub
) -> None:
    github.configure(view_code=1, view_stderr="HTTP 401: Bad credentials\n")
    assert "gh release view failed" in mirror_failure(tool, inputs, github)
    assert mutations(github.calls()) == []


def test_mirror_requires_matching_receipt_and_verified_distributions(
    tool: types.ModuleType, inputs: dict[str, Path], github: FakeGitHub
) -> None:
    github.configure(view_code=1, view_stderr="release not found\n")
    inputs["receipt"].write_text(json.dumps({"tag": "v1.0.1"}), encoding="utf-8")
    assert "release receipt tag" in mirror_failure(tool, inputs, github)
    inputs["receipt"].write_text(json.dumps({"tag": TAG}), encoding="utf-8")
    wheel = inputs["dist"] / names(VERSION)[0]
    wheel.write_bytes(wheel.read_bytes() + b"\0")
    assert "altered hash" in mirror_failure(tool, inputs, github)
    assert github.calls() == []
    assert sha256_hex(b"") != sha256_hex(b"\0")
