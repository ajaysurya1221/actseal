# REVIEW PYPI-01 — Trusted Publishing workflow

Verdict: **ACCEPT** for merge; actual PyPI publication is not performed.

Date:2026-10-06. Codex CI/docs follow-up requested by the user after v0.1.0.
Candidate `adb97bee7c9ac16d48d03d0ce30e7e922b5340f8`, PR8.
Workflow SHA256 `0cd7538ca0245d67eed437eb566672a05a53f92cc6c645892c47a39eb13766a0`.

## Findings ordered by severity

No blocking findings after independent read-only review. Manual main/repository
scope, validation-only default, pinned release bytes and exact CI receipt, separate
artifact transfer, job-scoped OIDC and pypi environment agree with ADR0014.
Download-artifact8 defaults to failing a digest mismatch. PyPA publishing defaults
to rejecting existing files; no skip-existing bypass. No product or release change.

## Independent validation

Root actionlint1.7.12, existing3hooks and strict Twine7 checks on both audited
release distributions passed. Exact release/tag/CI checks and downloads passed
locally. Wrong commit, extra/missing/draft/prerelease/wrong-version release records,
changed checksum and missing distribution all failed as intended.
macOS sha256sum lacks the Ubuntu GNU flags: local checksum probes used the equivalent
shasum -a256 --check --strict. The exact Ubuntu workflow must receive a validation-only
hosted run after merge; no claim of successful OIDC/PyPI upload is made.

[Push CI](https://github.com/ajaysurya1221/actseal/actions/runs/37481696352) and
[PR CI](https://github.com/ajaysurya1221/actseal/actions/runs/37481888846) each passed
all4Linux/macOS Python3.12/3.13 jobs on this exact candidate. Product files/tests,
uv.lock and the v0.1.0 tag/assets are unchanged. The new workflow itself only triggers
manually onmain; ordinary PR CI does not exercise its publishing path.

## Required changes

None before merge. Complete a publish=false hosted validation run, preserving its
receipt. PyPI publisher/account configuration and upload remain external operations.

## Follow-ups filed

The setup guide contains exact pending-publisher fields and explicit opt-in upload
command. Future releases require reviewed commit/CI/hash pin updates. No token is
stored. No new product dependency or optional-model behavior was introduced.
