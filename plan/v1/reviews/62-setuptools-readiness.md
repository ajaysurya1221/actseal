# Review 62 — bounded Setuptools lock maintenance

Observed 2 November 2026. **Local diff verdict: ACCEPT.** Merge requires
green hosted checks on the exact candidate commit; release is outside scope.

The independently inspected three-path patch against
`12945e92f28d27a1984af7ee5bad1ae618f8c748` has SHA256
`a27c55dbd9e12dd25b8737d253baf3ab10cec6b8391ffba5f5d487479902754f`.
This review record is added afterward; it does not change executable behavior.

## Scope and primary evidence

Only Setuptools changes, from 84.0.0 to 84.1.0. All other 60 package records
and resolution metadata are identical. The [official advisory](https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w)
names 84.1.0 as patched. Actual non-yanked artifacts match both the lock and
[exact-version PyPI metadata](https://pypi.org/pypi/setuptools/84.1.0/json):

| Artifact | Bytes | SHA256 |
|---|---:|---|
| Wheel | 819380 | `5231689c6ac8156cd155cfb98c3fd6fb252c3e7e9bd3d78b64d3c55f132624c9` |
| Source distribution | 1171783 | `23657205b63d4d31395ab917815247f694aafad28cd21316bf5fd45a51048ea0` |

Package metadata remains MIT, Python >=3.10. Inspection of the upstream
84.0.0-to-84.1.0 changes found namespace/path validation and unsafe archive
member rejection; this includes POSIX forms. The changed exception behavior
is a compatibility consideration, not proof that every installer is safe.

All 35 Actseal package files are unchanged. The 25-Python-file implementation
fingerprint remains `dced01d79e64799a19a75c0957f3684a48249c58ebb27d346336e7420195bcb4`.
The core still uses Hatchling; no configured `setup_requires`, `install_as_egg`
or Setuptools archive invocation was found. Setuptools remains in the optional
Torch/Laya dependency graph. No reproduced Actseal exploit is claimed.

## Fresh local verification

All 13 planned command checks passed: frozen setup/lock, lint, format, strict
types, ordinary tests, build, packaging, fixture demo, fixed/bad replay,
release-receipt checks and hooks. Ordinary tests: 4,210 passed, 2 skipped,
31 deselected. Packaging: 25 passed. The optional assets group was subsequently
installed from the frozen lock: 488 visual tests and strict asset typing passed.
These test groups overlap and must not be summed. Demo/fixed replay exit 0;
bad replay exits 1 with BLOCK, as intended.

Independent inspection rechecked the patch, all package records, actual
artifact metadata/license, source identity and rebuilt wheel contents. It
accepted the local diff and retained the exact-head hosted-CI merge gate.

Native startup/inference, model downloads, live TLS/provider behavior and a
new exploit reproduction were not run. Core tests do not certify native-stack
compatibility. No source/test/schema/provider-identity change, model call,
release, tag movement or replacement of published distributions is authorized
by this maintenance. Main-tree and main-CI verification follow integration
and must not be inferred from this local result.
