# REPORT PYPI-04 — PyPI publication complete

Status: **DONE**

Date: 2026-10-06. Workflow commit
`f8d602ecef8af5def808954e229d7cb5fbb7fb7d`.
[Successful publication run](https://github.com/ajaysurya1221/actseal/actions/runs/37485461528).
[Published package](https://pypi.org/project/actseal/0.1.0/).

## Changes (files + summary)

The user reported successful registration of a new pending publisher for
`actseal`. Before retry, the version API still returned404 and the GitHub `pypi`
environment allowed only the `main` branch. Codex dispatched the unchanged,
reviewed workflow with `publish=true`. Validation and publication both passed;
each distribution upload returned HTTP200. The first failed attempt remains
preserved in REPORT/REVIEW PYPI-03.

README, docs/quickstart.md and the unposted plan/LAUNCH.md now use the verified
PyPI package requirement. docs/publishing.md records completion and instructs
maintainers to update all reviewed pins before publishing another version.
STATE, CHANGE_LOG and FINAL_REPORT record this post-release follow-up.
No product, tests, workflow, lockfile, tag or release asset changed.

## Tests (commands + results)

`gh run view 37485461528 --repo ajaysurya1221/actseal --json status,conclusion,headSha,jobs,url`
returned completed/success at the workflow commit above. The root reviewer read
the hosted checks and upload results. Existing full four-job CI at that commit,
[run37485055345](https://github.com/ajaysurya1221/actseal/actions/runs/37485055345),
also passed. The distribution source remains the original reviewed tag
`83fd04a5d340000aed6518109dce666dc208ad70`.

The [PyPI version API](https://pypi.org/pypi/actseal/0.1.0/json) lists exactly
the two expected files. Root and a separate read-only reviewer independently
downloaded and hashed both:

| Distribution | Bytes | SHA-256 |
|---|---:|---|
| actseal-0.1.0-py3-none-any.whl | 84617 | `672b60815394cf9673c6a9f78437750ffc40d44467627604f48c5e1c5f77e906` |
| actseal-0.1.0.tar.gz | 505681 | `1781149ff09a21f14691daf0f6777f29022ec01293463394ac4f569f6897be2a` |

PyPI upload times are 15:13:01.220547 UTC for the wheel and 15:13:02.696541 UTC
for the sdist. These bytes match the original GitHub release exactly.

### Fresh PyPI installation and offline replay

From a fresh temporary directory outside the checkout, with a new empty uv
cache and the canonical PyPI index selected, root executed:

```bash
uvx --python 3.12 --from actseal==0.1.0 actseal demo --out ./actseal-demo
```

Exit0 in **1.483087 seconds**, including fresh package/environment preparation.
Python3.12.13 was already installed on the reference Mac; this is not a cold
Python download measurement or a general performance guarantee. The demo's
internal timer reported0.125s. Only `actseal==0.1.0` was installed in this new
tool environment. Import origin was its site-packages directory; Torch, Laya
and Transformers were absent. Implementation fingerprint matched:

`cd3a0976cf7886616f1fdf565c914f30d0c82cac530e7b9ffc4119e3a90300a7`.

Actual authored-fixture outcomes:

| Case | Verdict / replay exit | Total / accepted / wrong | Risk interval |
|---|---|---|---|
| bad | BLOCK / 1 | 128 / 128 / 32 | [0.1687604663492846, 0.346264539835876] |
| fixed | PASS / 0 | 128 / 128 / 0 | [0, 0.033655210093607835] |

Both coverage intervals were [0.9663447899063922,1]. All six fault outcomes matched.
These are synthetic fixture results, not model-quality or population evidence.

Root separately ran both replays with uv's `--offline` option, `--json` and the
previously reviewed expected lock hashes. Fixed replay returned0 and bad replay1,
with identical counts, bounds and reasons. The complete24-file demo inventory
digest matched the accepted local/GitHub CI release evidence:

`f894beeb06c4053d0965180ea98d229f3870887f3f09473f1599def541798d6d`.

### Published attestation inspection

The independent reviewer fetched both official provenance endpoints:
[wheel](https://pypi.org/integrity/actseal/0.1.0/actseal-0.1.0-py3-none-any.whl/provenance)
and [sdist](https://pypi.org/integrity/actseal/0.1.0/actseal-0.1.0.tar.gz/provenance).
Both identify repository `ajaysurya1221/actseal`, workflow `publish-pypi.yml` and
environment `pypi`. Decoded statements match the filenames and hashes and include
signatures, certificates and transparency entries. This was inspection of
published provenance plus independent artifact hashing, **not independent
cryptographic verification of the attestations**. Attestations concern this
publication identity; they do not prove model inference or supplied labels.

## Deviations from spec (with reason)

PyPI was an optional post-release request after the original GitHub sprint.
The first attempt failed because PyPI found no matching publisher; the user
subsequently completed pending-publisher registration, after which the unchanged
workflow succeeded. No alternate credential, retry of a statistical experiment,
rebuilt distribution or moved tag was used.

## Open issues

No publication blocker remains. Native Linux installation still requires the
repository's locked CPU index; a bare `pip install actseal[laya]` is not the
documented native setup. The immutable wheel/sdist retain their original
GitHub-install documentation snapshot, whose command remains valid. Current
main documentation uses the newly verified PyPI command. Public launch remains
a draft, and future publication requires new reviewed version/identity/hash pins.

## Spend

Incremental paid inference API spend: USD0. No model call, API-token credential
or paid hosting was introduced by this follow-up.
