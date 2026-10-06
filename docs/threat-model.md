# Actseal v1 trust boundaries

**Normative boundary; implementation/adversarial verification pending.** This document limits the intended assurance. It is not a completed security audit. Exact validation rules are in [CONTRACTS](../plan/CONTRACTS.md); acceptance evidence belongs in the [release checklist](../plan/RELEASE_CHECKLIST.md).

Actseal's intended protected result is a reproducible decision about a supplied, frozen application policy and its recorded evidence. Its evaluator does not execute application actions. The integrating application must protect the expected policy identity, verify its intended PASS and use the same evaluator/system at runtime. Parsing an arbitrary submitted lock must not make that lock authoritative.

## Inputs and required defenses

| Untrusted or fallible input | Required behavior |
|---|---|
| Contract/dataset JSON or TOML | Strict schema/types, finite numbers, bounded sizes/depth, exact labels and inventories; reject duplicate keys/IDs and literal split overlap. No coercion into a valid policy. |
| Provider response or identity | Validate observed identity first; preserve raw data; reject malformed/unknown/truncated outputs; selected-probability policy remains authoritative. Confidence/action suggestions cannot authorize ACT. |
| Stored outcomes/verdicts | Reconstruct requests, normalize raw captures, evaluate policy, check exact canonical fault captures and recompute assessment. A rewritten checksum does not repair inconsistent semantics. |
| Bundle filesystem | Exactly seven supported regular files; reject symlinks, unexpected files and unsupported names; bounded reads and exclusive atomic publication that refuses an existing destination. Missing native/filesystem support fails explicitly. |
| Worker timeout/death or broken IPC | Terminate/join where applicable, invalidate the worker, retain terminal records and prohibit silent restart. Regular Laya timeout/unavailable makes the experiment infrastructure ERROR. |

The frozen limits include 128 MiB for generic strict JSON and the whole bundle, 32 MiB for the lock, 1 MiB per JSONL row, depth 32 and 10,000 cases per split. Readers must apply the appropriate byte limits before unbounded parsing or provider calls. These limits constrain the supported format; they do not claim OS-level resource isolation.

[ADR 0012](decisions/0012-replay-errors-and-exclusive-publication.md) specifies macOS `renamex_np(RENAME_EXCL)` and Linux `renameat2(RENAME_NOREPLACE)` through stdlib `ctypes` and the system C library. Publishing a completed sibling temporary directory must atomically refuse a target created immediately before publication, including an empty directory; an existence check followed by ordinary rename cannot provide this property. Unsupported filesystem/platform/native support and other publication errors must fail explicitly, without an overwriting fallback. Actual T40 implementation and both hosted operating-system checks remain pending.

The caller controls the parent directory. Exclusive publication is not a defense against a hostile process replacing arbitrary ancestors or modifying files during/after replay. Atomic visibility is not a power-loss durability guarantee. v1 adds no recovery service or broader storage abstraction.

## Replay is data processing

Replay must make no network call, import no provider/model module and execute no bundle-supplied code. It must not use pickle, evaluate expressions, restore an environment, dynamically import a named class or extract an archive. Executable-looking strings remain data. The implementation fingerprint hashes installed source bytes without executing them.

Fresh replay checks the lock, manifests, raw inputs, ordered inventories, request hashes, recorded normalizations/actions and the final verdict. Unsupported implementation identity is ERROR. A deliberately captured malformed provider body can be valid failure evidence; damaged outer structure or inconsistent reconstruction is a different ERROR.

Before strict lock decoding succeeds, ERROR diagnostics use `evidence_scope=demo` and a 64-zero `lock_sha256` sentinel for unknown identity. After structural decoding, retain the decoded scope/hash even if later validation fails; retaining these values does not trust them. Never copy an expected external lock digest into the observed-identity field. ERROR counts remain zero and intervals `[0,1]`; reasons identify invariants without echoing payloads. Invalid evidence returns a verdict, while Python API argument-type misuse may raise `SchemaError`.

Under [ADR 0009](decisions/0009-worker-loss-invalidates-statistical-run.md), a complete infrastructure-invalidated bundle is diagnostic evidence. Replaying it must preserve ERROR; it cannot certify uptime, completion probability or a result conditioned on successful completion.

## Integrity is not authenticity

Anyone able to rewrite a whole bundle can choose new inputs and recompute its internal hashes. Consistent replay does not prove who created the bundle, whether a real provider was called, whether labels are true, whether cases were independently sampled, or whether failed attempts were hidden.

An expected lock digest obtained through a separately trusted channel anchors the expected identity only. A digest stored beside an untrusted bundle is not such a channel. Even a trusted expected lock digest does not authenticate provider responses or prove honest execution: an author can retain the same lock, replace responses and recompute consistent outcomes/verdicts and bundle hashes. v1 has no signatures, remote attestation or tamperproof history. See [ADR 0005](decisions/0005-data-only-replay-and-trust.md).

A model/card license, a selected threshold and a PASS are not general application-safety guarantees. The host remains responsible for action authorization, deployment identity and handling dispositions. Actseal is not a sandbox, permission firewall or defense against an attacker controlling the host/interpreter.

## Sensitive data and local operation

States, labels and raw model bodies may contain sensitive data. Only reviewed synthetic fixtures belong in the public demo; review generated bundles before sharing. Captures must exclude credentials, authorization headers and arbitrary exception text; bounded errors identify fields/invariants without echoing source values.

Fixture/demo/replay require no key. Optional local-model preparation is separate from offline evaluation; Hugging Face offline flags are library settings, not a network firewall. Jev and actual fallback execution remain outside v1. A recorded fallback flag always removes ACT authority.

Required release checks include semantic forgery after rehashing, incomplete/swapped inventories, canonical fault substitution, filesystem/schema boundaries, provider-free/network-free replay and worker-loss invalidation. Passing those tests supports their tested boundaries, not an unbounded security claim.
