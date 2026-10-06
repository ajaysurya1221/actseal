"""Write and check orchestration for the asset inventory.

``run(mode="check")`` regenerates every implemented asset twice into temporary
storage, rejects nondeterministic renderers, validates the bytes, and compares
them with the committed files. ``run(mode="write")`` does the same and then
writes validated bytes. Planned assets without a renderer are reported as not
implemented and never counted as passed. Global checks cover the tool
manifest, the uv.lock pin, font attribution, README references and orphans.

Invalid declarations abort the run before any renderer is called, and every
write destination is re-resolved and confined to ``docs/assets`` (symlinks
are refused) immediately before the bytes are written.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from . import checks, references, tools
from .inventory import (
    ASSET_DIR,
    ASSETS,
    SOURCE_DIR,
    Asset,
    Output,
    RenderContext,
    Source,
    is_plain_filename,
    validate_inventory,
)

ERROR = "error"
INFO = "info"
OK = "ok"
# Errors in these scopes describe the declarations themselves; no renderer may
# run and nothing may be written while they stand.
BLOCKING_SCOPES = frozenset({"inventory", "arguments"})


@dataclass(frozen=True, slots=True)
class Finding:
    scope: str
    level: str
    message: str

    def line(self) -> str:
        return f"[{self.level}] {self.scope}: {self.message}"


@dataclass(slots=True)
class Report:
    mode: str
    findings: list[Finding] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    planned: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.level == ERROR]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, scope: str, level: str, message: str) -> None:
        self.findings.append(Finding(scope, level, message))

    def summary(self) -> str:
        parts = [
            f"{self.mode}:",
            f"{len(self.checked)} asset(s) checked",
            f"{len(self.planned)} planned/not implemented",
            f"{len(self.errors)} error(s)",
        ]
        if self.mode == "write":
            parts.append(f"{len(self.written)} file(s) written")
        return " ".join(parts[:1]) + " " + "; ".join(parts[1:])

    def lines(self) -> list[str]:
        return [*(finding.line() for finding in self.findings), self.summary()]


def _first_difference(expected: bytes, actual: bytes) -> str:
    limit = min(len(expected), len(actual))
    offset = next((i for i in range(limit) if expected[i] != actual[i]), limit)
    line = expected[:offset].count(b"\n") + 1
    return (
        f"differs at byte {offset} (line {line}); committed {len(expected)} bytes, "
        f"regenerated {len(actual)} bytes"
    )


def _render_twice(asset: Asset, context: RenderContext) -> tuple[Mapping[str, bytes], list[str]]:
    assert asset.renderer is not None  # noqa: S101 - caller guarantees implemented
    first = dict(asset.renderer(context))
    second = dict(asset.renderer(context))
    errors: list[str] = []
    if first.keys() != second.keys():
        errors.append("nondeterministic renderer: output set changed between runs")
    errors.extend(
        f"nondeterministic renderer: {path} changed between runs"
        for path in sorted(first)
        if path in second and first[path] != second[path]
    )
    declared = {output.path for output in asset.outputs}
    errors.extend(
        f"renderer produced undeclared output {path}" for path in sorted(first.keys() - declared)
    )
    errors.extend(
        f"renderer did not produce declared output {path}"
        for path in sorted(declared - first.keys())
    )
    return first, errors


def _check_sources(root: Path, asset: Asset, report: Report) -> None:
    for source in asset.sources:
        path = root / SOURCE_DIR / source.path
        label = f"{SOURCE_DIR}/{source.path}"
        if not path.is_file():
            level = ERROR if asset.implemented else INFO
            report.add(asset.name, level, f"source {label} is not present")
            continue
        problems = _check_source(path.read_bytes(), source)
        for problem in problems:
            report.add(asset.name, ERROR, f"{label}: {problem}")
        if not problems:
            report.add(asset.name, OK, f"source {label} validated")


def _check_source(data: bytes, source: Source) -> list[str]:
    if source.kind == "cast":
        return checks.check_cast(
            data, min_seconds=source.min_seconds, max_seconds=source.max_seconds
        )
    return [f"unsupported source kind {source.kind!r}"]


def _check_needs(
    root: Path, asset: Asset, manifest: Mapping[str, tools.Tool], report: Report
) -> None:
    for need in asset.needs:
        tool = manifest.get(need)
        if tool is None:
            report.add(asset.name, ERROR, f"requires unknown tool {need!r}")
            continue
        problem = _tool_availability(root, tool)
        if problem is None:
            continue
        level = ERROR if asset.implemented else INFO
        report.add(asset.name, level, problem)


def _tool_availability(root: Path, tool: tools.Tool) -> str | None:
    if tool.kind == "python":
        return None
    if tool.kind == "font":
        missing = [path.name for path in tools.font_paths(root, tool) if not path.is_file()]
        if missing:
            return f"requires {tool.name} {tool.version}; not fetched: {', '.join(missing)}"
        return None
    try:
        tools.verified_binary(root, tool)
    except tools.ToolError as exc:
        return f"requires {tool.name} {tool.version}: {exc}"
    return None


def _process_asset(
    root: Path,
    asset: Asset,
    manifest: Mapping[str, tools.Tool],
    report: Report,
    *,
    write: bool,
    requested: bool,
) -> None:
    _check_needs(root, asset, manifest, report)
    _check_sources(root, asset, report)
    if not asset.implemented:
        report.planned.append(asset.name)
        level = ERROR if requested else INFO
        report.add(asset.name, level, f"not implemented (planned in Task {asset.task})")
        return
    if any(f.scope == asset.name and f.level == ERROR for f in report.findings):
        report.add(asset.name, ERROR, "skipped rendering because prerequisites failed")
        return
    with tempfile.TemporaryDirectory(prefix="actseal-assets-") as temp:
        context = RenderContext(root=root, work=Path(temp))
        try:
            rendered, problems = _render_twice(asset, context)
        except (tools.ToolError, OSError, ValueError, RuntimeError) as exc:
            report.add(asset.name, ERROR, f"render failed: {exc}")
            return
    for problem in problems:
        report.add(asset.name, ERROR, problem)
    if problems:
        return
    report.checked.append(asset.name)
    for output in asset.outputs:
        _process_output(root, asset, output, rendered[output.path], report, write=write)


def _asset_dir_problem(root: Path, *, create: bool) -> str | None:
    """Reject a ``docs/assets`` directory that resolves outside the repository."""
    asset_dir = root / ASSET_DIR
    if create:
        asset_dir.mkdir(parents=True, exist_ok=True)
    if not asset_dir.is_dir():
        return None
    expected = root.resolve(strict=True) / ASSET_DIR
    actual = asset_dir.resolve(strict=True)
    if actual != expected or asset_dir.is_symlink():
        return f"{ASSET_DIR} resolves to {actual}, outside the repository; refusing to continue"
    return None


def _contained_target(root: Path, filename: str) -> tuple[Path | None, str | None]:
    """Resolve ``docs/assets/<filename>`` and refuse anything that escapes it.

    Returns ``(path, None)`` when ``path`` is a regular file or does not exist,
    and ``(None, reason)`` for a symlink or any resolution that leaves the
    asset directory.
    """
    if not is_plain_filename(filename):
        return None, f"{filename!r} is not a plain filename"
    asset_dir = (root / ASSET_DIR).resolve(strict=True)
    target = root / ASSET_DIR / filename
    if target.is_symlink():
        return None, f"{ASSET_DIR}/{filename} is a symlink; refusing to follow it"
    if target.exists():
        resolved = target.resolve(strict=True)
        if resolved.parent != asset_dir or resolved.name != filename:
            return None, f"{ASSET_DIR}/{filename} resolves outside {ASSET_DIR}"
        if not resolved.is_file():
            return None, f"{ASSET_DIR}/{filename} is not a regular file"
    return target, None


def _process_output(
    root: Path,
    asset: Asset,
    output: Output,
    data: bytes,
    report: Report,
    *,
    write: bool,
) -> None:
    label = f"{ASSET_DIR}/{output.path}"
    problems = checks.check_output(data, output)
    for problem in problems:
        report.add(asset.name, ERROR, f"{label}: {problem}")
    if problems:
        if write:
            report.add(asset.name, ERROR, f"{label}: refusing to write an invalid output")
        return
    if write:
        _write_output(root, asset, output, data, report)
    else:
        _compare_output(root, asset, output, data, report)


def _write_output(root: Path, asset: Asset, output: Output, data: bytes, report: Report) -> None:
    label = f"{ASSET_DIR}/{output.path}"
    dir_problem = _asset_dir_problem(root, create=True)
    if dir_problem is not None:
        report.add(asset.name, ERROR, dir_problem)
        return
    target, reason = _contained_target(root, output.path)
    if target is None:
        report.add(asset.name, ERROR, f"{reason}; nothing written")
        return
    target.write_bytes(data)
    report.written.append(output.path)
    report.add(asset.name, OK, f"wrote {label} ({len(data)} bytes)")


def _compare_output(root: Path, asset: Asset, output: Output, data: bytes, report: Report) -> None:
    label = f"{ASSET_DIR}/{output.path}"
    missing = f"{label} is not committed; run render.py --write"
    if not (root / ASSET_DIR).is_dir():
        report.add(asset.name, ERROR, missing)
        return
    target, reason = _contained_target(root, output.path)
    if target is None:
        report.add(asset.name, ERROR, f"{reason}; not compared")
        return
    if not target.is_file():
        report.add(asset.name, ERROR, missing)
        return
    committed = target.read_bytes()
    if committed != data:
        report.add(asset.name, ERROR, f"{label} {_first_difference(committed, data)}")
        return
    report.add(asset.name, OK, f"{label} matches regeneration ({len(data)} bytes)")


def _global_checks(
    root: Path, assets: tuple[Asset, ...], manifest: Mapping[str, tools.Tool], report: Report
) -> None:
    for problem in validate_inventory(assets):
        report.add("inventory", ERROR, problem)
    dir_problem = _asset_dir_problem(root, create=False)
    if dir_problem is not None:
        report.add("inventory", ERROR, dir_problem)
    for problem in tools.validate_manifest(dict(manifest)):
        report.add("manifest", ERROR, problem)
    for tool in manifest.values():
        if tool.kind == "python":
            for problem in tools.check_lock_pin(root, tool):
                report.add("manifest", ERROR, f"{tool.name}: {problem}")
        elif tool.kind == "font":
            problems, present = tools.check_fonts(root, tool)
            for problem in problems:
                report.add("fonts", ERROR, problem)
            if not present:
                report.add(
                    "fonts", INFO, f"{tool.name} {tool.version} not fetched; run setup_tools.py"
                )
            elif not problems:
                report.add("fonts", OK, f"{tool.name} {tool.version} present with upstream notice")
    problems, checked = references.check_references(root, assets)
    for problem in problems:
        report.add("references", ERROR, problem)
    if not problems:
        report.add("references", OK, f"{checked} image reference(s) checked")
    for problem in references.check_orphans(root, assets):
        report.add("orphans", ERROR, problem)


def run(
    root: Path,
    *,
    mode: str,
    only: tuple[str, ...] = (),
    assets: tuple[Asset, ...] = ASSETS,
    manifest_path: Path | None = None,
) -> Report:
    """Execute ``--write`` or ``--check`` for ``only`` (or every) asset under ``root``."""
    if mode not in {"write", "check"}:
        msg = f"mode must be 'write' or 'check', got {mode!r}"
        raise ValueError(msg)
    report = Report(mode=mode)
    names = {asset.name for asset in assets}
    unknown = sorted(set(only) - names)
    if unknown:
        report.add("arguments", ERROR, f"unknown asset(s): {', '.join(unknown)}")
        return report
    try:
        manifest = tools.load_manifest(manifest_path or tools.default_manifest_path(root))
    except tools.ToolError as exc:
        report.add("manifest", ERROR, str(exc))
        return report
    _global_checks(root, assets, manifest, report)
    blocking = [f for f in report.findings if f.level == ERROR and f.scope in BLOCKING_SCOPES]
    if blocking:
        report.add(
            "inventory",
            ERROR,
            f"aborting before any renderer runs: {len(blocking)} declaration error(s) above",
        )
        return report
    selected = [asset for asset in assets if not only or asset.name in only]
    for asset in selected:
        _process_asset(
            root,
            asset,
            manifest,
            report,
            write=mode == "write",
            requested=asset.name in only,
        )
    return report
