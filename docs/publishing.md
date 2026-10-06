# Publish Actseal to PyPI

The workflow is [publish-pypi.yml](../.github/workflows/publish-pypi.yml).
It promotes the exact reviewed GitHub v0.1.0 wheel and source archive. It checks
the tag commit, successful four-job release CI, exact asset inventory, pinned
SHA-256 hashes and strict Twine metadata validation before enabling upload.
It never rebuilds this release from later main commits.

**v0.1.0 is published on [PyPI](https://pypi.org/project/actseal/0.1.0/).**
[Run 37485461528](https://github.com/ajaysurya1221/actseal/actions/runs/37485461528)
completed successfully on 6 October 2026 after pending-publisher registration.
Both distributions match the reviewed GitHub bytes, and a fresh PyPI installation,
demo and offline replays passed. See [REPORT PYPI-04](../plan/reports/PYPI-04.md).
Do not rerun `publish=true` for this already-published version.

## One-time setup

1. Sign in to [PyPI's publishing settings](https://pypi.org/manage/account/publishing/).
   Add a pending GitHub publisher using the fields below. If you already own the
   `actseal` PyPI project, use its Publishing settings instead.
2. Create a GitHub Actions environment named `pypi` in
   [the repository settings](https://github.com/ajaysurya1221/actseal/settings/environments).
   Restrict its deployment branch to `main`. No PyPI token or repository secret is needed.

| PyPI field | Value |
|---|---|
| PyPI project name | `actseal` |
| Owner | `ajaysurya1221` |
| Repository | `actseal` |
| Workflow filename | `publish-pypi.yml` |
| Environment | `pypi` |

PyPI's [pending-publisher documentation](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
explains the first-project setup. Registration does not reserve the project name.
The project was created by the successful first upload. For Actseal, manage the
existing publisher in the project's Publishing settings; do not register another
pending publisher for each release. The GitHub `pypi` environment allows only `main`.

## Validate, then upload a future release

First update the workflow's version, tag, commit, successful CI run, filenames
and checksums together after the new GitHub release passes review. Until those
pins change, this workflow continues to target the already-published v0.1.0.

1. Open [Publish to PyPI](https://github.com/ajaysurya1221/actseal/actions/workflows/publish-pypi.yml),
   choose **Run workflow**, select `main`, and leave **publish unchecked**.
   This validates and retains the two distributions without requesting a PyPI token.
2. Once validation passes and the publisher is configured, run it on `main` again
   with **publish checked** to upload the newly reviewed version. This creates
   a permanent PyPI release.

Equivalent commands:

```bash
gh workflow run publish-pypi.yml --repo ajaysurya1221/actseal --ref main -f publish=false
```

```bash
gh workflow run publish-pypi.yml --repo ajaysurya1221/actseal --ref main -f publish=true
```

Only the separate publish job has `id-token: write`. It downloads the validated
artifact and invokes the pinned PyPA action; it checks out no source and builds
nothing. The action uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
and generates attestations. Existing conflicting PyPI files fail rather than
being silently skipped. A partial upload needs explicit inspection before retry.

This workflow deliberately requires an explicit promotion; publishing a GitHub
release does not automatically upload to PyPI.

The supported Linux native setup still uses the repository's locked CPU index;
see [providers](providers.md). Installing a wheel or the PyPI core package
does not carry `tool.uv.sources` into a consumer's environment. Do not replace the
documented native setup with a bare `pip install actseal[laya]` instruction.
