# Publish Actseal to PyPI

The release pipeline is [publish-pypi.yml](../.github/workflows/publish-pypi.yml).
It builds the wheel and source distribution exactly once from a release tag,
verifies those immutable bytes on every supported platform, regenerates the
required static assets with the pinned authoring toolchain, uploads through
PyPI Trusted Publishing after a human approval, verifies the public PyPI copy
in a clean container, and mirrors identical files to a draft GitHub release.
`tools/check_release.py` implements each gate; `tests/release` covers them.

Historical note: v0.1.0 was published on 6 October 2026 by an earlier,
manually dispatched workflow that promoted pre-built GitHub release bytes; its
receipts are under `plan/reports/`. That workflow and its inputs no longer
exist. Do not re-upload any already-published version.

## Two ways to run the workflow

| Trigger | What happens | Uploads? |
|---|---|---|
| **Run workflow** (`workflow_dispatch`) on a branch, no inputs | Rehearsal: validate, build once, verify on the four-platform matrix, regenerate assets. The publish, post-publication and mirror jobs do not run. | Never |
| Push of a tag matching `v*` | Full release: everything above, then the `pypi` environment waits for approval, publishes, verifies the public copy and creates the draft GitHub release. | After approval |

The workflow has no inputs. There is no "publish" switch to set; a tag is the
only path to an upload, and a branch run can never upload.

### Rehearse on a branch

```bash
gh workflow run publish-pypi.yml --repo ajaysurya1221/actseal --ref <branch>
```

Run this from any branch whose source, lock and `pyproject.toml` version
agree. The `build` job validates identity, runs `check_release.py docs`
before building, builds the two distributions into an immutable Actions
artifact and runs `twine check --strict`; `verify` downloads that exact
artifact by ID on Linux and macOS with Python 3.12 and 3.13 and runs the
packaging acceptance against it without rebuilding; `assets` fetches the
pinned fonts and resvg with hash verification and regenerates the required
static assets byte for byte. A rehearsal that stops at the documentation,
asset or verification gate is reporting a real prerequisite; fix the source,
not the gate. Rehearsal results are candidate checks against unpublished
bytes and are never labelled public PyPI receipts.

### Publish from a tag

1. Freeze the release commit: version in `pyproject.toml`, `uv.lock` and
   `actseal.__version__` agree, the `CHANGELOG.md` heading for that version
   exists, every required static asset is committed, and the candidate gate
   `uv run --frozen python tools/check_release.py candidate` passes on a clean
   tree.
   **Pre-tag documentation finalization.** The tagged commit is immutable
   and its README, CHANGELOG and docs become the published sdist and PyPI
   long description. Before tagging, every "unreleased", "candidate",
   "pending implementation" or conditional (Jev, example, benchmark)
   statement in `CHANGELOG.md`, `README.md`, `docs/` **and
   `plan/v1/RELEASE_NOTES.md`** must be resolved to the shipped facts, and
   the ADR status paragraphs must match them. The source distribution
   packages the pre-tag copies of `plan/v1/RELEASE_NOTES.md`,
   `plan/v1/reports/` and `plan/v1/reviews/` as listed in `pyproject.toml`,
   so the release notes at the tag must already state the final
   implementation, scope and inclusion facts (Jev, example, benchmark,
   figures) and may contain **only** named placeholders for publication
   receipts that cannot exist before the upload: the distribution hashes
   and sizes, the workflow run and artifact ids, the attestation inspection,
   the post-publication install and smoke results, and the genuine demo
   recording. No other draft, candidate or pending marker may remain.
   Historical reports and reviews under `plan/v1/` keep their original
   content. After publication those named placeholders are filled, in a
   later documentation commit, in the repository's
   `plan/v1/RELEASE_NOTES.md`, the final report and the GitHub release;
   those additions cannot alter the already-tagged commit or the
   already-uploaded wheel and sdist. A later task cannot change bytes
   already tagged or uploaded.
2. Create and push an annotated tag `vX.Y.Z` on exactly that commit. The
   `build` job rejects a tag whose version does not match the sources.
3. Watch the run. When `build`, all four `verify` jobs and `assets` succeed,
   the `publish` job pauses on the `pypi` environment until the repository
   owner approves it. No PyPI API token is stored in the repository or its
   secrets: the job requests a short-lived GitHub OIDC token for its own run,
   and PyPI's Trusted Publishing exchanges that identity for a project-scoped
   API token that, per the
   [official documentation](https://docs.pypi.org/trusted-publishers/), is
   valid for 15 minutes from creation. The pinned PyPA action performs the
   exchange and generates attestations. Only this job has `id-token: write`;
   it checks out no source
   and builds nothing. It downloads the verified artifact by ID, re-checks the
   bytes against the build checksums with `sha256sum --check --strict`, and
   uploads with `skip-existing: false`.
4. `verify-published` installs the version from the public index in a pinned
   clean container outside the checkout, runs the demo and both replays with
   the expected exits 0, 0 and 1, compares the downloaded files with the
   build checksums and inspects attestation presence and publisher identity.
   That inspection is not independent cryptographic verification and is not
   described as such.
5. `mirror` binds the artifact identity, checksums and post-publication
   results into a release receipt and creates or updates only a **draft**
   GitHub release carrying the identical wheel, sdist, `SHA256SUMS` and
   receipt. Publishing that draft, the release notes and the genuine demo
   recording are separate, later documentation steps.

## One-time setup

| PyPI publisher field | Value |
|---|---|
| PyPI project name | `actseal` |
| Owner | `ajaysurya1221` |
| Repository | `actseal` |
| Workflow filename | `publish-pypi.yml` |
| Environment | `pypi` |

The publisher is managed in the project's
[Publishing settings](https://pypi.org/manage/account/publishing/); do not
register a new pending publisher per release. The GitHub `pypi` environment
must require the repository owner's approval and permit deployment from
`v*` tags (and `main`); the workflow filename and environment name are the
trusted-publisher identity and must not change.

## Failure and partial-publication recovery

PyPI uploads are permanent. The rules below keep every published byte
accounted for:

- **Failure before `publish`** (identity, docs, build, verify or assets):
  nothing was uploaded. Fix the source, run a rehearsal, and tag a new commit.
  Never move or reuse a tag.
- **Approval declined or expired:** nothing was uploaded; the tag stays as a
  record. Tag a new commit if the release is still wanted.
- **`publish` failed part-way** (for example one of the two files is on PyPI):
  do not rerun the job. Inspect the PyPI file list and the run log, record
  which bytes were published, and open the next patch version with a fresh
  tag. The workflow uses `skip-existing: false`, so a retry against existing
  files fails by design rather than silently skipping them, and published
  bytes are never replaced.
- **`verify-published` or `mirror` failed after a successful upload:** the
  version is live. Treat the failure as a release blocker to investigate and
  document in that version's receipts; do not yank or re-upload unless the
  published files are actually wrong. A missing draft release is recreated by
  re-running only the `mirror` job, which still re-downloads the exact
  artifact and re-checks its hashes.

Partial or failed runs remain historical receipts; a later green run does
not erase them.

## Native stack note

The supported Linux native setup still uses the repository's locked CPU
index; see [providers](providers.md). Installing a wheel or the PyPI core
package does not carry `tool.uv.sources` into a consumer's environment. Do
not replace the documented native setup with a bare `pip install actseal[laya]`
instruction.
