# GitHub Action (2.0.0, unreleased)

Use the composite action to run `qualify`, `verify`, or `replay`, append a
static report to the job summary, and upload the evidence. It supports Linux
and macOS. PASS exits 0, BLOCK 1, INCONCLUSIVE 2, and ERROR 3. BLOCK and
INCONCLUSIVE therefore fail the step after retaining diagnostics.

The default installation targets `actseal==2.0.0` from PyPI in an isolated
Python 3.13 environment. Version 2.0.0 is unreleased: until it is published,
use explicit `source: checkout` of the reviewed action commit. The version
input accepts an exact `MAJOR.MINOR.PATCH` release, optionally followed by
`aN`, `bN`, or `rcN`; ranges and package URLs are rejected.

For this repository's checked-out v2 source:

```yaml
permissions:
  contents: read
steps:
  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
    with:
      persist-credentials: false
  - uses: ./
    id: actseal
    with:
      source: checkout
      mode: qualify
      args: >-
        --contract src/actseal/demo_data/qualify.toml
        --calibration src/actseal/demo_data/qualify_calibration.jsonl
        --verification src/actseal/demo_data/qualify_verification.jsonl
        --provider fixture
        --responses src/actseal/demo_data/qualify_responses.jsonl
        --offline --out qualification-output
```

For another repository, reference `ajaysurya1221/actseal` at a reviewed full
commit SHA and pass paths to your contract and inputs. `source: checkout`
installs the action's checkout, not the calling repository. `source: pypi`
installs the exact `version` input with no optional provider dependencies.
Native or external providers require their separately documented setup.

| Input | Default | Meaning |
|---|---|---|
| `mode` | required | `qualify`, `verify`, or `replay` |
| `args` | required | Command arguments; quote paths containing spaces |
| `version` | `2.0.0` | Exact PyPI version; unused for `source: checkout`; requires publication for PyPI installation |
| `python-version` | `3.13` | Interpreter installed through pinned `setup-uv` |
| `report` | `true` | Render the report and append its Markdown summary |
| `upload-evidence` | `true` | Upload the receipt, evidence and available report |
| `source` | `pypi` | `pypi` or explicit `checkout` installation |

Arguments are split into quoted words and passed as a process argument list.
There is no shell expansion: `$VARIABLE`, `~`, command substitutions, pipes,
and redirects are literal argument text. Use paths relative to the caller's
working directory or explicit paths. Line breaks in `args` are rejected; YAML
folded scalars (`>-`, as above) turn the example into one line. The action adds
`--json` to collect the command receipt.

Outputs are `verdict`, `exit-code`, and `evidence-path` (the absolute original
output directory, or the replay directory). The uploaded artifact contains
`receipt.json`, an `evidence/` copy, and `report/` when rendering succeeds.
Only the defined bundle/qualification filenames are copied; unrelated files
and symlinks are excluded. Neither the replay input nor generated evidence
is modified. The report's replay commands are relative to its input evidence
directory; artifact recipients first enter the corresponding `evidence/`
directory. Generated report files live outside the strict evidence bundle.

The action retains the original command exit through reporting and uploading.
If reporting fails, the summary says **Report unavailable**, with an Actions
warning; the command verdict is not replaced by a report result. A no-threshold
qualification retains its calibration diagnostics and exits 2 but has no
verification bundle from which to render a report. Installation or invalid
receipt failures are errors. An evidence-copy failure warns that the artifact
may be incomplete and preserves the original command code. An upload failure
is a workflow failure. Setup failure may leave the action outputs empty.

## Optional artifact attestation

There is no attestation step in the action. To attest a result produced by
your workflow, add a follow-up step using
[`actions/attest` v4.0.0](https://github.com/actions/attest/releases/tag/v4.0.0).
For example, package this run's qualification output and attest those exact
archive bytes:

```yaml
# Add these job permissions only when using the optional follow-up.
permissions:
  contents: read
  id-token: write
  attestations: write

# Steps after the Actseal step with id: actseal:
- name: Package this workflow's evidence
  if: ${{ always() && steps.actseal.outputs.evidence-path != '' }}
  env:
    EVIDENCE_PATH: ${{ steps.actseal.outputs.evidence-path }}
  run: tar -czf actseal-evidence.tar.gz -C "$EVIDENCE_PATH" .
- uses: actions/attest@c32b4b8b198b65d0bd9d63490e847ff7b53989d4 # v4.0.0
  if: ${{ always() && steps.actseal.outputs.evidence-path != '' }}
  with:
    subject-path: actseal-evidence.tar.gz
```

After obtaining that same archive, verify its provenance with the
[GitHub CLI](https://cli.github.com/manual/gh_attestation_verify):

```sh
gh attestation verify actseal-evidence.tar.gz \
  --repo OWNER/REPOSITORY \
  --signer-workflow OWNER/REPOSITORY/.github/workflows/qualification.yml
```

Such an attestation links these archive bytes to the identified workflow run.
It does not prove label truth, IID sampling, model performance in deployment,
or that a downloaded/local input bundle was originally collected by that run.
Attesting a replay archive establishes what the workflow packaged after
replay; it does not authenticate the earlier captures. Keep the workflow,
repository, and subject digest checks in your verification policy.

Actseal itself verifies no signature. Its report says `checksummed, not
attested` unless the caller supplies `--attestation-ref TEXT`. Supply that
reference only after external verification; it remains a caller assertion,
not an Actseal signature check. The composite action never supplies one.

## Self-test and limits

[`action-selftest.yml`](../.github/workflows/action-selftest.yml) uses explicit
checkout installation, replays the retained PASS bundle, and qualifies the
packaged synthetic demo. Both jobs require all three nonempty report files and
a PASS badge, so a reporting failure fails the self-test. These are
authored/archival examples, not new model
measurements. The replay job requires both producer and final running
fingerprints in the reviewed registry; the workflow does not bypass that
gate. A prepared workflow is not evidence of a successful hosted run.

Local tests inspect full-SHA pins and environment-only script inputs through
a strict line-based reader, execute the embedded Python scripts against
controlled process results, and run the real offline fixture qualification
and reporting commands through those scripts. They do not exercise GitHub's composite runner,
Python downloads, PyPI installation, summary rendering, artifact upload,
OIDC signing or remote attestation verification.
