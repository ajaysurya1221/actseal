# ADR 0012: Unreadable-lock diagnostics and exclusive bundle publication

- Status: accepted before T40 implementation.
- Date: 2026-10-06.

## Decision

Replay always returns a Verdict for invalid bundle evidence. Before a lock has
successfully passed strict structural decoding, an ERROR uses evidence_scope=demo
and lock_sha256 equal to 64 zero characters. This sentinel is explicitly an
unknown identity, never a valid certification. After structural decoding, retain
the decoded scope/hash for diagnostics even if subsequent seal/integrity checks
fail. Never substitute the expected external digest for the observed digest.
All ERROR counts remain zero and intervals [0,1]; reasons identify invariants
without echoing payloads. Python API argument-type misuse may raise SchemaError.

Publish a completed sibling temporary directory using an OS operation that
atomically refuses an existing destination. An exists check followed by ordinary
os.rename is insufficient: it can replace an empty destination created meanwhile.
On supported macOS use renamex_np with RENAME_EXCL (4); on Linux use renameat2
with RENAME_NOREPLACE (1), through stdlib ctypes and the system C library. Keep
this a private evidence.py helper with explicit signatures/errno handling and
filesystem-encoded paths. Missing symbols, unsupported filesystems/platforms or
other errors fail explicitly; never fall back to an overwriting rename. No new
Python dependency, bundled C library or copied implementation is introduced.

This enforces the already frozen new-destination requirement. It is not a
sandbox against a hostile process replacing arbitrary ancestor directories or
modifying files during/after replay. Callers control the parent directory; input
reads still reject symlinks/nonregular files and remain bounded. Atomic visibility
is not a power-loss durability guarantee. Do not add signing, filesystem recovery
or a cross-platform storage abstraction.

## Evidence and validation

Observed 2026-10-06: the installed Apple SDK rename(2) manual specifies EEXIST for
RENAME_EXCL; sys/stdio.h fixes its value at4. The matching public
[Apple header](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/stdio.h)
exposes renamex_np from macOS10.12. Root's temporary macOS probe refused an
existing empty directory without changing either directory, then successfully
published to an absent destination. No source implementation was ported.

The [Linux manual](https://man7.org/linux/man-pages/man2/rename.2.html) specifies
RENAME_NOREPLACE, glibc2.28/kernel3.15 availability and filesystem support. The
[Linux UAPI header](https://github.com/torvalds/linux/blob/master/include/uapi/linux/fs.h)
fixes its value at1. These are system API facts; no upstream code is vendored.
Actual Linux execution remains a required T40 hosted-CI gate, not an inferred
result. Unsupported environments receive an explicit error.

T40 tests must create an empty target immediately before the real publish call,
prove it remains untouched, exercise missing-lock sentinels and invalid-lock
identity diagnostics, and cover publication failure cleanup. Ordinary tests on
both supported CI operating systems must execute the native exclusive operation.
