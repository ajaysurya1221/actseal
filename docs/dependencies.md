# Dependency and model provenance

Verification date: **6 October 2026**. Versions below are explicit sprint pins, not promises that they remain the newest releases. The committed `uv.lock` must record the complete resolved graph and hashes. This document separates a tested native stack from registry/license metadata checks and pending product verification.

## Core and development tooling

Actseal's core uses Python standard-library facilities; the live Laya runtime is an optional extra. Do not make replay or the fixture quickstart import Torch, Transformers, or a provider SDK. The project's license choice is Apache-2.0; attributed reuse must retain upstream notices independently of package licensing.

| Component | Pin | License | Evidence and purpose |
| --- | --- | --- | --- |
| CPython | 3.12.13 | PSF License Agreement | Version executed in the native smoke; [Python license](https://docs.python.org/3/license.html). Python 3.12 is the sprint's reference interpreter. |
| uv | 0.12.5 | MIT OR Apache-2.0 | [Version metadata](https://pypi.org/pypi/uv/0.12.5/json), [license](https://github.com/astral-sh/uv/blob/main/LICENSE-MIT). Lockfile, isolated environments, and reproducible commands. |
| Ruff | 0.16.10 | MIT | [Version metadata](https://pypi.org/pypi/ruff/0.16.10/json), [license](https://github.com/astral-sh/ruff/blob/main/LICENSE). Lint and format checks required by the user. |
| mypy | 2.4.0 | MIT | [Version metadata](https://pypi.org/pypi/mypy/2.4.0/json), [license](https://github.com/python/mypy/blob/master/LICENSE). Typed lane contracts; the user's mypy requirement supersedes a research suggestion to use another checker. |
| pytest | 9.1.1 | MIT | [Version metadata](https://pypi.org/pypi/pytest/9.1.1/json), [license](https://github.com/pytest-dev/pytest/blob/main/LICENSE). Deterministic tests and separately marked integration tests. |
| pre-commit | 4.6.2 | MIT | [Version metadata](https://pypi.org/pypi/pre-commit/4.6.2/json), [license](https://github.com/pre-commit/pre-commit/blob/main/LICENSE). Required local/CI check entrypoint. |
| Hatchling | 1.32.4 | MIT | [Version metadata](https://pypi.org/pypi/hatchling/1.32.4/json), [license](https://github.com/pypa/hatch/blob/master/LICENSE.txt). Minimal wheel/sdist build backend; justified packaging glue, not a runtime abstraction. |

The six Python tool-package versions and license metadata were fetched from their exact version endpoints. That confirms availability and declared licenses; it does not by itself prove all product checks pass. CPython and the native model stack ran successfully; Actseal's own lint, type, test, build, and pre-commit results belong in task reports and CI.

GitHub Actions use immutable commit pins selected and license-checked by the planner:

| Action | Release reference | Commit | License |
| --- | --- | --- | --- |
| [actions/checkout](https://github.com/actions/checkout) | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | [MIT](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/LICENSE) |
| [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv) | v10.2.0 | `c18668ad3cf93ea998bef934396af7bb5c839dc7` | [MIT](https://github.com/astral-sh/setup-uv/blob/c18668ad3cf93ea998bef934396af7bb5c839dc7/LICENSE) |

These source pins are not evidence that a hosted workflow has run. Hosted Linux/macOS green checks remain release acceptance conditions.

## Tested optional Laya stack

The following versions resolved together and completed the CPU and cached-offline native smoke in [providers](providers.md). Freeze this tested combination when generating the product lockfile.

| Package | Version | License evidence |
| --- | --- | --- |
| Laya | 0.3.28 | [Apache-2.0 source LICENSE](https://github.com/NandhaKishorM/laya/blob/v0.3.28/LICENSE); [exact PyPI metadata](https://pypi.org/pypi/laya/0.3.28/json). |
| Torch | 2.14.1 | Installed wheel license files and metadata: Apache-2.0, Apache-2.0 WITH LLVM-exception, BSD-2-Clause, BSD-3-Clause, BSL-1.0, MIT; [version metadata](https://pypi.org/pypi/torch/2.14.1/json). Do not label the entire distribution with just one of these licenses. |
| Transformers | 5.18.0 | Installed Apache-2.0 LICENSE; [version metadata](https://pypi.org/pypi/transformers/5.18.0/json), [upstream license](https://github.com/huggingface/transformers/blob/main/LICENSE). |
| huggingface-hub | 1.33.0 | Installed Apache-2.0 LICENSE; [version metadata](https://pypi.org/pypi/huggingface-hub/1.33.0/json), [upstream license](https://github.com/huggingface/huggingface_hub/blob/main/LICENSE). The resolver selected this compatible version; registry-latest 2.1.1 was not used. |
| Safetensors | 0.8.0 | Apache-2.0 verified by reading `safetensors-0.8.0.dist-info/licenses/LICENSE` in the installed wheel. The PyPI `license` field was null; the Apache classifier alone was not the final check. [Version metadata](https://pypi.org/pypi/safetensors/0.8.0/json). |
| NumPy | 2.5.3 | Installed LICENSE and bundled notice files read; metadata declares BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0. [Version metadata](https://pypi.org/pypi/numpy/2.5.3/json). |

The [Laya project manifest](https://github.com/NandhaKishorM/laya/blob/v0.3.28/pyproject.toml) declares Torch/Transformers/Safetensors/HF Hub/NumPy dependencies and Python >=3.10. It does not require MLX. The native compatibility check used Python 3.12.13 on macOS arm64; Linux native compatibility remains an integration check.

Laya 0.3.28 was uploaded to PyPI on **5 October 2026 at 18:05:12 UTC**. Its wheel SHA256 is `a1493cff474c0a5d84861db55c0c5c9b17f1db8561e458764da9a322dc542a88`. The research's 0.3.24 recommendation is superseded deliberately: 0.3.28 fixes published-wheel packaging and additional calibration/runtime defects. See the [release](https://github.com/NandhaKishorM/laya/releases/tag/v0.3.28).

## Weights and immutable artifacts

Model: **`convaiinnovations/laya-typed-decisions`**. Revision: **`e929ae5cf69bc34259cd2f95c9e91145b818b1f0`**, last modified 3 October 2026. The [pinned model card](https://huggingface.co/convaiinnovations/laya-typed-decisions/blob/e929ae5cf69bc34259cd2f95c9e91145b818b1f0/README.md) declares Apache-2.0. The repository is public and ungated; [HF metadata](https://huggingface.co/api/models/convaiinnovations/laya-typed-decisions) lists 421,293,830 F16 parameters. There is no separate LICENSE file in the model repository: the card is the explicit weights-license declaration.

Locally downloaded artifacts were SHA256-hashed after successful loading:

| Relative artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `model.safetensors` | 842,609,220 | `4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e` |
| `encoder/config.json` | 2,084 | `5268d24ad3b77c8151de5dcb0762ba4391619aad9ab0bda33e36fb083cfeae6d` |
| `rl_agent_config.json` | 847 | `ebf0cd524d92342a6be5e48e9fca3d7c2babfb5a56ccd79d2171ef5d8c7f7be8` |
| `tokenizer/tokenizer.json` | 3,583,228 | `6c8aaa9a542084f2457eab775d4eeb51f92a70c0fd9de28d5edb0ddec3c08d30` |
| `tokenizer/tokenizer_config.json` | 337 | `08d4cf3ac4dca381759441b85b91a6d40e688471dcd33d15d6649eb0a9a854d1` |

These are download/runtime artifacts, not files to commit into the product repository. Verify hashes on preparation/loading. Preserve the checkpoint card's calibration and specialization limitations in user-facing model documentation. The 843 MB weight file does not mean a process uses less than 1 GB: the observed peak process RSS reached approximately 2.72 GiB in the cached smoke.

## Transitive-license inventory

The native smoke resolved 35 distributions. Installed metadata was inspected for every distribution, and relevant direct-dependency license files were read. This is a dated dependency inventory, not an exhaustive legal audit of every bundled file. The committed lockfile remains authoritative for the final shipped graph.

| License family / declared expression | Observed distributions and versions |
| --- | --- |
| MIT | annotated-doc 0.0.5; anyio 4.15.1; filelock 4.0.12; h11 0.16.0; markdown-it-py 4.2.0; mdurl 0.1.2; pip 26.1.2; PyYAML 6.0.3; rich 15.0.0; setuptools 84.0.0; typer 0.27.2 |
| BSD variants | click 8.5.0; fsspec 2026.9.0; httpcore 1.0.9; httpx 0.28.1; idna 3.20; Jinja2 3.1.6; MarkupSafe 3.0.4; mpmath 1.3.0; networkx 3.7; Pygments 2.21.0; sympy 1.14.0 |
| Apache variants | hf-xet 1.6.0; tokenizers 0.23.2; packaging 26.3 (Apache-2.0 OR BSD-2-Clause); regex 2026.9.29 (Apache-2.0 AND CNRI-Python) |
| MPL / MIT, ISC, PSF | certifi 2026.7.22 (MPL-2.0); tqdm 4.70.1 (MPL-2.0 AND MIT); shellingham 1.5.4 (ISC); typing_extensions 4.16.0 (PSF-2.0) |
| Direct native packages | Laya, Torch, Transformers, HF Hub, Safetensors, and NumPy: versions and compound license expressions above |

Jinja2, mpmath, and SymPy installed license files were also inspected where package metadata used a generic BSD label. Retain upstream notices when redistribution requires them; install-time use of an optional dependency does not transfer its full codebase into Actseal. No proprietary runtime appeared in the resolved native stack.

## Changes and release gate

Record dependency updates as explicit changes to the frozen provider identity when they can affect predictions or normalization. Re-run the native reference smoke and associated fixtures before accepting such an update; then regenerate the committed lockfile using the pinned uv version. Do not float package or model aliases in published evidence.

Jev is an optional v2 service adapter, not a dependency or substitute for the open local path. Its [customer agreement](https://typesafe.ai/legal/mca) is proprietary service terms, not an OSI license. No vendor SDK, hosted tier, access key, or paid API call is required by the v1 reference stack.

Before release, CI must verify the final lockfile, build, tests, lint, formatting, types, and pre-commit commands. A successful upstream smoke does not replace those product checks. Include all attributed copied-code notices in the repository and distribution, and report any newly introduced dependency/license before merging it.
