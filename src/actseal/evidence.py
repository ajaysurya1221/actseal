"""Atomic data-only evidence bundles (plan/CONTRACTS.md section 6, ADR 0005/0012).

A bundle is a directory holding EXACTLY seven regular files: ``manifest.json``,
``lock.json``, ``calibration.jsonl``, ``verification.jsonl``, ``records.jsonl``,
``faults.jsonl`` and ``verdict.json``. Every file is UTF-8 text. The lock,
verdict and manifest are one canonical JSON object plus one LF; records and
faults are one canonical JSON object plus one LF per row; both datasets are the
exact raw bytes that the lock hashed (CRLF and other line endings preserved,
nothing appended). The manifest is ``{schema_version: 1, files: {name: {size,
sha256}}, sha256}`` over the other six files; its own ``sha256`` is the
canonical hash of the manifest with only that field omitted. No timestamps,
durations, host paths, PIDs or credentials enter any file, so the same bundle
written to independent destinations is byte-identical.

Limits (plan/CONTRACTS.md section 2): each JSONL row at most 1 MiB measured
after LF-only splitting and excluding the terminator (a preceding CR counts);
``lock.json`` at most 32 MiB including its LF; every other file at most 128 MiB;
the seven files together, every LF included, at most 128 MiB; at most 10,000
rows per JSONL file.

Writing validates the evidence with the accepted authorities first
(``validate_inputs`` and a fresh ``assess`` that must equal the recorded
verdict), rejects a destination path containing NUL before any filesystem
effect, refuses an existing destination, encodes the seven files under one
running aggregate budget that stops at the first overflowing row or file,
writes into a sibling temporary directory and publishes it with an OS rename
that atomically refuses an existing destination: ``renamex_np(RENAME_EXCL)`` on macOS, ``renameat2
(RENAME_NOREPLACE)`` on Linux, through ``ctypes`` and the system C library.
Other platforms, missing symbols and unsupported filesystems fail explicitly;
there is no overwriting fallback. A failed write leaves no partial bundle.

Reading is bounded before any content is read: the directory listing is
rejected at the first entry outside the seven-name inventory (an arbitrarily
long malformed tail is never traversed), every entry is inspected with
``lstat`` (symlinks, nonregular files and missing entries are rejected),
every size is checked against its ceiling and the
aggregate ceiling, and only then is the manifest read and each file read with
the accepted bounded reader and compared with the manifest. Nothing here
executes bundle content, extracts archives, unpickles, imports user modules or
restores an environment.
"""

from __future__ import annotations

import ctypes
import errno
import os
import re
import shutil
import stat
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, TypeVar

from actseal.assessment import REASON_INTEGRITY_PREFIX, assess
from actseal.contract import MAX_ROW_BYTES, read_input_text
from actseal.errors import IntegrityError, SchemaError
from actseal.locking import MAX_LOCK_BYTES, validate_inputs
from actseal.records import (
    MAX_CASES_PER_SPLIT,
    SCHEMA_VERSION,
    DecisionRecord,
    EvidenceBundle,
    FaultResult,
    PlanLock,
    Verdict,
)
from actseal.serialization import (
    MAX_JSON_BYTES,
    canonical_json,
    from_data,
    sha256_bytes,
    strict_json_loads,
    to_data,
)

__all__ = [
    "BUNDLE_FILES",
    "CALIBRATION_FILE",
    "DATA_FILES",
    "FAULTS_FILE",
    "LOCK_FILE",
    "MANIFEST_FILE",
    "MAX_BUNDLE_BYTES",
    "RECORDS_FILE",
    "VERDICT_FILE",
    "VERIFICATION_FILE",
    "decode_document",
    "decode_rows",
    "read_bundle_files",
    "write_bundle",
]

MANIFEST_FILE: Final = "manifest.json"
LOCK_FILE: Final = "lock.json"
CALIBRATION_FILE: Final = "calibration.jsonl"
VERIFICATION_FILE: Final = "verification.jsonl"
RECORDS_FILE: Final = "records.jsonl"
FAULTS_FILE: Final = "faults.jsonl"
VERDICT_FILE: Final = "verdict.json"

#: The six files inventoried by the manifest, in bundle order.
DATA_FILES: Final[tuple[str, ...]] = (
    LOCK_FILE,
    CALIBRATION_FILE,
    VERIFICATION_FILE,
    RECORDS_FILE,
    FAULTS_FILE,
    VERDICT_FILE,
)
#: All seven bundle files, in bundle order.
BUNDLE_FILES: Final[tuple[str, ...]] = (MANIFEST_FILE, *DATA_FILES)
MAX_BUNDLE_BYTES: Final = 128 * 1024 * 1024

_LF: Final = b"\n"
_SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")
_MANIFEST_KEYS: Final[frozenset[str]] = frozenset({"schema_version", "files", "sha256"})
_ENTRY_KEYS: Final[frozenset[str]] = frozenset({"size", "sha256"})
_TEMP_PREFIX: Final = ".actseal-bundle-"
_FILE_MODE: Final = 0o644

# System API constants (ADR 0012). Values are fixed by the public headers:
# macOS sys/stdio.h RENAME_EXCL, Linux include/uapi/linux/fs.h RENAME_NOREPLACE
# and fcntl.h AT_FDCWD. No native implementation is vendored.
_RENAME_EXCL: Final = 4
_RENAME_NOREPLACE: Final = 1
_AT_FDCWD: Final = -100

_D = TypeVar("_D", bound=DecisionRecord | FaultResult | Verdict | PlanLock)


# --------------------------------------------------------------------------- #
# Canonical encoding
# --------------------------------------------------------------------------- #


class _Budget:
    """Running wire-byte budget for one bundle: every file byte and every LF is charged.

    Charging happens before bytes are retained, so encoding stops at the first
    row or file that would push the seven-file total past ``limit``; later rows
    and files are never serialized and no oversized join is made.
    """

    __slots__ = ("limit", "used")

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    @property
    def remaining(self) -> int:
        return self.limit - self.used

    def charge(self, size: int) -> None:
        if size > self.remaining:
            raise SchemaError(f"bundle: aggregate size exceeds {self.limit} bytes")
        self.used += size


def _document(record: object, budget: _Budget) -> bytes:
    """One canonical JSON object plus one LF, charged to the budget."""
    data = canonical_json(to_data(record)) + _LF
    budget.charge(len(data))
    return data


def _encode_rows(name: str, records: Sequence[object], budget: _Budget) -> bytes:
    """Canonical rows plus LF each; the budget stops encoding at the first overflow."""
    rows: list[bytes] = []
    for index, record in enumerate(records):
        row = canonical_json(to_data(record))
        if len(row) > MAX_ROW_BYTES:
            raise SchemaError(f"{name}[{index}]: row exceeds {MAX_ROW_BYTES} bytes")
        budget.charge(len(row) + len(_LF))
        rows.append(row + _LF)
    return b"".join(rows)


def _encode_dataset(name: str, text: str, budget: _Budget) -> bytes:
    """The exact raw bytes of a locked JSONL split; nothing is added or repaired.

    The character count is a lower bound on the UTF-8 byte count, so text that
    cannot fit the remaining budget is rejected before any encoding is allocated.
    """
    if len(text) > budget.remaining:
        raise SchemaError(f"bundle: aggregate size exceeds {budget.limit} bytes")
    data = text.encode("utf-8")
    if len(data) > MAX_JSON_BYTES:
        raise SchemaError(f"{name}: document exceeds {MAX_JSON_BYTES} bytes")
    budget.charge(len(data))
    return data


def _manifest(files: Mapping[str, bytes], budget: _Budget) -> bytes:
    inventory: dict[str, object] = {
        name: {"size": len(data), "sha256": sha256_bytes(data)} for name, data in files.items()
    }
    unsealed: dict[str, object] = {"schema_version": SCHEMA_VERSION, "files": inventory}
    sealed: dict[str, object] = {**unsealed, "sha256": sha256_bytes(canonical_json(unsealed))}
    data = canonical_json(sealed) + _LF
    budget.charge(len(data))
    return data


def _encode_files(bundle: EvidenceBundle, limit: int) -> dict[str, bytes]:
    """Serialize all seven files in bundle order under one running aggregate budget.

    Per-file and per-row ceilings are enforced as each unit is produced; the
    aggregate ceiling ``limit`` (manifest and every LF included) is enforced
    incrementally, so the first overflowing row or file ends encoding.
    """
    budget = _Budget(limit)
    lock = _document(bundle.lock, budget)
    if len(lock) > MAX_LOCK_BYTES:
        raise SchemaError(f"{LOCK_FILE}: document exceeds {MAX_LOCK_BYTES} bytes")
    data: dict[str, bytes] = {LOCK_FILE: lock}
    data[CALIBRATION_FILE] = _encode_dataset(CALIBRATION_FILE, bundle.calibration_jsonl, budget)
    data[VERIFICATION_FILE] = _encode_dataset(VERIFICATION_FILE, bundle.verification_jsonl, budget)
    data[RECORDS_FILE] = _encode_rows(RECORDS_FILE, bundle.records, budget)
    data[FAULTS_FILE] = _encode_rows(FAULTS_FILE, bundle.faults, budget)
    data[VERDICT_FILE] = _document(bundle.verdict, budget)
    manifest = _manifest(data, budget)
    return {MANIFEST_FILE: manifest, **data}


# --------------------------------------------------------------------------- #
# Semantic validation before writing
# --------------------------------------------------------------------------- #


def _check_semantics(bundle: EvidenceBundle) -> None:
    """The recorded verdict must be exactly what the accepted authorities recompute.

    A complete ADR 0009 infrastructure ERROR is valid diagnostic evidence and is
    written as is. Evidence whose records or faults do not reproduce from their
    captures, or whose verdict differs from a fresh assessment, is refused.
    """
    validate_inputs(bundle.lock, bundle.calibration_jsonl, bundle.verification_jsonl)
    recomputed = assess(bundle.records, bundle.lock, bundle.faults)
    if any(reason.startswith(REASON_INTEGRITY_PREFIX) for reason in recomputed.reasons):
        raise IntegrityError("evidence: records or faults do not reproduce from their captures")
    if recomputed != bundle.verdict:
        raise IntegrityError("verdict: does not equal a fresh assessment of the evidence")


# --------------------------------------------------------------------------- #
# Exclusive publication (ADR 0012)
# --------------------------------------------------------------------------- #


def _load_libc() -> ctypes.CDLL:
    """The system C library already linked into the interpreter.

    ``CDLL(None)`` is ``dlopen(NULL)``: the global symbol namespace of the
    running process, where ``renamex_np``/``renameat2`` resolve to the system
    libc. No library name lookup (and no ``ctypes.util``/``subprocess`` import)
    is needed.
    """
    return ctypes.CDLL(None, use_errno=True)


def _symbol(libc: object, name: str) -> object:
    try:
        return getattr(libc, name)
    except AttributeError:
        raise NotImplementedError(f"exclusive rename: {name} is not available") from None


def _check_path_text(field: str, path: Path) -> None:
    """Reject a path that cannot be passed intact to the operating system.

    An embedded NUL terminates C string arguments, so the native call would act
    on a silently truncated path while Python-level checks saw the full one.
    """
    if not isinstance(path, Path):
        raise SchemaError(f"{field}: must be a Path")
    if "\x00" in os.fspath(path):
        raise SchemaError(f"{field}: must not contain NUL")


def _c_path(field: str, path: Path) -> bytes:
    """Filesystem-encode ``path`` for a C string argument, rejecting embedded NUL."""
    _check_path_text(field, path)
    encoded = os.fsencode(os.fspath(path))
    if b"\x00" in encoded:
        raise SchemaError(f"{field}: must not contain NUL")
    return encoded


def _exclusive_rename(source: Path, destination: Path) -> None:
    """Atomically rename ``source`` to ``destination``, refusing any existing destination.

    macOS: ``renamex_np(from, to, RENAME_EXCL)``. Linux: ``renameat2(AT_FDCWD,
    old, AT_FDCWD, new, RENAME_NOREPLACE)``. Any other platform or a missing
    symbol is :class:`NotImplementedError`; a nonzero result raises
    :class:`OSError` with the reported errno (``EEXIST`` becomes
    :class:`FileExistsError`; ``EINVAL``/``ENOSYS``/``ENOTSUP`` mean the
    filesystem or kernel does not support the operation). Paths containing NUL
    are :class:`SchemaError` before any native call. Never falls back.
    """
    old = _c_path("source", source)
    new = _c_path("destination", destination)
    result: int
    if sys.platform == "darwin":
        renamex_np = _symbol(_load_libc(), "renamex_np")
        renamex_np.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]  # type: ignore[attr-defined]
        renamex_np.restype = ctypes.c_int  # type: ignore[attr-defined]
        result = renamex_np(old, new, _RENAME_EXCL)  # type: ignore[operator]
    elif sys.platform.startswith("linux"):
        renameat2 = _symbol(_load_libc(), "renameat2")
        renameat2.argtypes = [  # type: ignore[attr-defined]
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int  # type: ignore[attr-defined]
        result = renameat2(_AT_FDCWD, old, _AT_FDCWD, new, _RENAME_NOREPLACE)  # type: ignore[operator]
    else:
        raise NotImplementedError("exclusive rename: unsupported platform")
    if result != 0:
        code = ctypes.get_errno()
        raise OSError(code, f"exclusive rename failed: {os.strerror(code)}")


def _write_file(path: Path, data: bytes) -> None:
    """Create a new regular file (never following or replacing anything) and write ``data``."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(path, flags, _FILE_MODE)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def write_bundle(bundle: EvidenceBundle, destination: Path) -> Path:
    """Validate ``bundle`` and publish it atomically as the NEW directory ``destination``.

    Raises :class:`SchemaError` for argument misuse or exceeded limits,
    :class:`IntegrityError` when the evidence does not reproduce under the
    accepted authorities, :class:`FileExistsError` when the destination exists
    (before or at publication), :class:`NotImplementedError` when exclusive
    publication is unavailable on this platform and other :class:`OSError`
    for filesystem failures. On any failure the temporary directory is removed
    and nothing appears at ``destination``.
    """
    if not isinstance(bundle, EvidenceBundle):
        raise SchemaError("bundle: must be EvidenceBundle")
    _check_path_text("destination", destination)
    if os.path.lexists(destination):
        raise FileExistsError(errno.EEXIST, "destination: already exists")
    _check_semantics(bundle)
    files = _encode_files(bundle, MAX_BUNDLE_BYTES)
    temporary = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX, dir=destination.parent))
    try:
        for name in BUNDLE_FILES:
            _write_file(temporary / name, files[name])
        _exclusive_rename(temporary, destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


# --------------------------------------------------------------------------- #
# Bounded reading
# --------------------------------------------------------------------------- #


def _size_limit(name: str) -> int:
    return MAX_LOCK_BYTES if name == LOCK_FILE else MAX_JSON_BYTES


def _inventory(bundle: Path) -> dict[str, os.DirEntry[str]]:
    """Enumerate the directory, stopping at the first entry that breaks the seven-name inventory.

    An unexpected or repeated name ends enumeration immediately, so a malformed
    directory with an arbitrarily long tail is never traversed or retained.
    Missing names are reported after the (at most seven) valid entries.
    """
    expected = frozenset(BUNDLE_FILES)
    found: dict[str, os.DirEntry[str]] = {}
    with os.scandir(bundle) as entries:
        for entry in entries:
            if entry.name not in expected or entry.name in found:
                raise SchemaError("bundle: must contain exactly the seven bundle files")
            found[entry.name] = entry
    if len(found) != len(BUNDLE_FILES):
        raise SchemaError("bundle: must contain exactly the seven bundle files")
    return found


def _inspect(bundle: Path) -> dict[str, int]:
    """Check the directory shape with ``lstat`` and return every file size, reading nothing."""
    info = os.lstat(bundle)
    if stat.S_ISLNK(info.st_mode):
        raise SchemaError("bundle: must not be a symlink")
    if not stat.S_ISDIR(info.st_mode):
        raise SchemaError("bundle: must be a directory")
    found = _inventory(bundle)
    sizes: dict[str, int] = {}
    for name in BUNDLE_FILES:
        info = found[name].stat(follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            raise SchemaError(f"{name}: must not be a symlink")
        if not stat.S_ISREG(info.st_mode):
            raise SchemaError(f"{name}: must be a regular file")
        size = info.st_size
        if size < 1:
            raise SchemaError(f"{name}: must not be empty")
        if size > _size_limit(name):
            raise SchemaError(f"{name}: file exceeds {_size_limit(name)} bytes")
        sizes[name] = size
    if sum(sizes.values()) > MAX_BUNDLE_BYTES:
        raise SchemaError(f"bundle: aggregate size exceeds {MAX_BUNDLE_BYTES} bytes")
    return sizes


def _read_exact(path: Path, name: str, size: int) -> bytes:
    """Read a file whose size was inspected, through the accepted bounded UTF-8 reader."""
    data = read_input_text(path, limit=size).encode("utf-8")
    if len(data) != size:
        raise SchemaError(f"{name}: size changed while reading")
    return data


def _utf8(name: str, data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise SchemaError(f"{name}: must be valid UTF-8") from None


def _decode_manifest(data: bytes) -> dict[str, tuple[int, str]]:
    """Strictly decode the manifest; return ``{name: (size, sha256)}`` for the six files."""
    value = strict_json_loads(_utf8(MANIFEST_FILE, data))
    if type(value) is not dict or set(value) != _MANIFEST_KEYS:
        raise SchemaError("manifest: expected exactly schema_version, files, sha256")
    version = value["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        raise SchemaError("manifest.schema_version: unsupported schema version")
    files = value["files"]
    if type(files) is not dict or set(files) != set(DATA_FILES):
        raise SchemaError("manifest.files: must inventory exactly the six data files")
    entries: dict[str, tuple[int, str]] = {}
    for name in DATA_FILES:
        entry = files[name]
        if type(entry) is not dict or set(entry) != _ENTRY_KEYS:
            raise SchemaError(f"manifest.files.{name}: expected exactly size, sha256")
        size = entry["size"]
        if type(size) is not int or not 1 <= size <= _size_limit(name):
            raise SchemaError(f"manifest.files.{name}.size: must be an integer in [1, limit]")
        digest = entry["sha256"]
        if type(digest) is not str or _SHA256_HEX.fullmatch(digest) is None:
            raise SchemaError(f"manifest.files.{name}.sha256: must be lowercase SHA256 hex")
        entries[name] = (size, digest)
    recorded = value["sha256"]
    if type(recorded) is not str or _SHA256_HEX.fullmatch(recorded) is None:
        raise SchemaError("manifest.sha256: must be lowercase SHA256 hex")
    unsealed: dict[str, object] = {"schema_version": version, "files": files}
    if sha256_bytes(canonical_json(unsealed)) != recorded:
        raise IntegrityError("manifest.sha256: self-hash does not match the manifest contents")
    if canonical_json(value) + _LF != data:
        raise SchemaError("manifest: must be canonical JSON with one terminal LF")
    return entries


def read_bundle_files(bundle: Path) -> dict[str, bytes]:
    """Inspect, size-check, read and hash-verify all seven files; return their exact bytes.

    Structural problems (not a directory, symlinks, nonregular or extra/missing
    files, sizes over any ceiling, malformed or non-canonical manifest, invalid
    UTF-8) are :class:`SchemaError`; manifest self-hash, size or file-hash
    mismatches are :class:`IntegrityError`; operating-system errors propagate.
    Nothing is decoded beyond the manifest.
    """
    _check_path_text("bundle", bundle)
    sizes = _inspect(bundle)
    manifest_data = _read_exact(bundle / MANIFEST_FILE, MANIFEST_FILE, sizes[MANIFEST_FILE])
    entries = _decode_manifest(manifest_data)
    for name, (size, _) in entries.items():
        if size != sizes[name]:
            raise IntegrityError(f"manifest.files.{name}.size: does not match the file")
    files: dict[str, bytes] = {MANIFEST_FILE: manifest_data}
    for name, (size, digest) in entries.items():
        data = _read_exact(bundle / name, name, size)
        if sha256_bytes(data) != digest:
            raise IntegrityError(f"manifest.files.{name}.sha256: does not match the file")
        files[name] = data
    return files


# --------------------------------------------------------------------------- #
# Strict decoding of canonical documents and rows
# --------------------------------------------------------------------------- #


def _decode_canonical(path: str, data: bytes, record_type: type[_D]) -> _D:
    """Decode one canonical JSON object; the record must re-encode to exactly ``data``."""
    try:
        record = from_data(record_type, strict_json_loads(_utf8(path, data)))
    except SchemaError as exc:
        raise SchemaError(f"{path}: {exc}") from None
    if canonical_json(to_data(record)) != data:
        raise SchemaError(f"{path}: must be canonical JSON")
    return record


def decode_document(name: str, data: bytes, record_type: type[_D]) -> _D:
    """Decode a one-object file (``verdict.json`` style): canonical JSON plus one LF."""
    if not data.endswith(_LF):
        raise SchemaError(f"{name}: must end with one LF")
    return _decode_canonical(name, data[:-1], record_type)


def decode_rows(name: str, data: bytes, record_type: type[_D]) -> tuple[_D, ...]:
    """Decode a JSONL file of canonical rows, each at most 1 MiB excluding its LF."""
    if not data.endswith(_LF):
        raise SchemaError(f"{name}: must end with one LF")
    rows = data.split(_LF)
    rows.pop()
    if not rows:
        raise SchemaError(f"{name}: must contain at least one row")
    if len(rows) > MAX_CASES_PER_SPLIT:
        raise SchemaError(f"{name}: must contain at most {MAX_CASES_PER_SPLIT} rows")
    decoded: list[_D] = []
    for index, row in enumerate(rows):
        if len(row) > MAX_ROW_BYTES:
            raise SchemaError(f"{name}[{index}]: row exceeds {MAX_ROW_BYTES} bytes")
        decoded.append(_decode_canonical(f"{name}[{index}]", row, record_type))
    return tuple(decoded)
