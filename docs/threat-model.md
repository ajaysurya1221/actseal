# Actseal v1 trust boundaries

**Core accepted through T40; final acceptance and release pending.** [T40's review](../plan/reviews/T40-02.md) records implemented evidence/replay checks and hosted macOS/Linux verification. CLI integration and T60's independent acceptance work remain pending. This document defines the assurance boundary, not a comprehensive security audit. Exact rules are in [CONTRACTS](../plan/CONTRACTS.md); final gates remain in the [release checklist](../plan/RELEASE_CHECKLIST.md).

Actseal's intended protected result is a reproducible decision about a supplied, frozen application policy and its recorded evidence. Its evaluator does not execute application actions. The integrating application must protect the expected policy identity, verify its intended PASS and use the same evaluator/system at runtime. Parsing an arbitrary submitted lock must not make that lock authoritative.

## Inputs and required defenses

| Untrusted or fallible input | Required behavior |
|---|---|
| Contract/dataset JSON or TOML | Strict schema/types, finite numbers, bounded sizes/depth, exact labels and inventories; reject duplicate keys/IDs and literal split overlap. No coercion into a valid policy. |
| Provider response or identity | Validate observed identity first; preserve raw data; reject malformed/unknown/truncated outputs; selected-probability policy remains authoritative. Confidence/action suggestions cannot authorize ACT. |
| Stored outcomes/verdicts | Reconstruct requests, normalize raw captures, evaluate policy, check exact canonical fault captures and recompute assessment. A rewritten checksum does not repair inconsistent semantics. |
| Bundle filesystem | Exactly seven supported regular files; reject symlinks, unexpected files and unsupported names; bounded reads and exclusive atomic publication that refuses an existing destination. Missing native/filesystem support fails explicitly. |
| Worker timeout/death or broken IPC | Terminate/join where applicable, invalidate the worker, retain terminal records and prohibit silent restart. Regular Laya timeout/unavailable makes the experiment infrastructure ERROR. |

The frozen limits are 128 MiB for generic strict JSON, aggregate fixture input and the whole bundle; 32 MiB for the lock; 1 MiB per JSONL row; depth 32; and 10,000 cases per dataset split. A JSONL row excludes its LF separator but counts any CR; whole-file/bundle limits count every byte, including the lock's LF and the manifest. Readers use bounded reads before decoding, and bundle writing accounts incrementally for all seven files. These conventions follow [ADR 0010](decisions/0010-shared-bounded-input-helpers.md) and [ADR 0011](decisions/0011-provider-helpers-and-fixture-bound.md); the fixture file has no invented 10,000-row limit. These are format/resource limits, not OS-level isolation.

[ADR 0012](decisions/0012-replay-errors-and-exclusive-publication.md) uses macOS `renamex_np(RENAME_EXCL)` and Linux `renameat2(RENAME_NOREPLACE)` through stdlib `ctypes` and the system C library. Publication of a completed sibling temporary directory atomically refuses an existing target, including an empty directory created just before publication. Unsupported filesystem/platform/native support and other publication errors fail explicitly, without an overwriting fallback. T40 acceptance includes the native operation on both hosted operating systems, first-overflow write rejection and bounded directory enumeration; it does not establish support for every filesystem.

The caller controls the parent directory. Exclusive publication is not a defense against a hostile process replacing arbitrary ancestors or modifying files during/after replay. Atomic visibility is not a power-loss durability guarantee. v1 adds no recovery service or broader storage abstraction.

## Replay is data processing

Replay must make no network call, import no provider/model module and execute no bundle-supplied code. It must not use pickle, evaluate expressions, restore an environment, dynamically import a named class or extract an archive. Executable-looking strings remain data. The implementation fingerprint hashes installed source bytes without executing them.

Fresh replay checks the lock, manifests, raw inputs, ordered inventories, request hashes, recorded normalizations/actions and the final verdict. Unsupported implementation identity is ERROR. A deliberately captured malformed provider body can be valid failure evidence; damaged outer structure or inconsistent reconstruction is a different ERROR.

Before strict lock decoding succeeds, ERROR diagnostics use `evidence_scope=demo` and a 64-zero `lock_sha256` sentinel for unknown identity. After structural decoding, retain the decoded scope/hash even if later validation fails; retaining these values does not trust them. Never copy an expected external lock digest into the observed-identity field. ERROR counts remain zero and intervals `[0,1]`; reasons identify invariants without echoing payloads. Invalid evidence returns a verdict. Wrong Python argument types, malformed expected digests or NUL-bearing paths may raise `SchemaError` before filesystem effects; the pending CLI integration must map these to exit 3.

Under [ADR 0009](decisions/0009-worker-loss-invalidates-statistical-run.md), a complete infrastructure-invalidated bundle is diagnostic evidence. Replaying it must preserve ERROR; it cannot certify uptime, completion probability or a result conditioned on successful completion.

## Integrity is not authenticity

Anyone able to rewrite a whole bundle can choose new inputs and recompute its internal hashes. Consistent replay does not prove who created the bundle, whether a real provider was called, whether labels are true, whether cases were independently sampled, or whether failed attempts were hidden.

An expected lock digest obtained through a separately trusted channel anchors the expected identity only. A digest stored beside an untrusted bundle is not such a channel. Even a trusted expected lock digest does not authenticate provider responses or prove honest execution: an author can retain the same lock, replace responses and recompute consistent outcomes/verdicts and bundle hashes. v1 has no signatures, remote attestation or tamperproof history. See [ADR 0005](decisions/0005-data-only-replay-and-trust.md).

A model/card license, a selected threshold and a PASS are not general application-safety guarantees. The host remains responsible for action authorization, deployment identity and handling dispositions. Actseal is not a sandbox, permission firewall or defense against an attacker controlling the host/interpreter.

## Sensitive data and local operation

States, labels and raw model bodies may contain sensitive data. Only reviewed synthetic fixtures belong in the public demo; review generated bundles before sharing. The pending [ADR 0013 demo](decisions/0013-prespecified-synthetic-demo.md) uses the same policy against different authored outputs; it makes no model-repair or deployment-performance claim. Captures exclude credentials, authorization headers and arbitrary exception text; bounded errors identify fields/invariants without echoing source values.

Fixture/demo/replay require no key. Optional local-model preparation is separate from offline evaluation; Hugging Face offline flags are library settings, not a network firewall. Jev and actual fallback execution remain outside v1. A recorded fallback flag always removes ACT authority.

Accepted core checks cover rehashed semantic inconsistencies, inventory/fault validation, filesystem bounds, provider-free/network-free replay and diagnostic worker-loss ERROR. T60's independent acceptance, CLI/packaging integration and final release-candidate checks remain required. Passing tests supports their tested boundaries, not an unbounded security claim.
