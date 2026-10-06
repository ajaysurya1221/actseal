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

Source pins alone are not execution evidence. The provider milestone below has green hosted Linux/macOS jobs at its exact candidate; green checks on the final release candidate remain a separate acceptance condition.

## Tested optional Laya stack

The following versions resolved together on macOS arm64 and completed the original CPU/cached-offline upstream smoke in [providers](providers.md). The later Actseal provider milestone also passed native product tests on macOS and the Linux CPU variant, as recorded below. Preserve this tested combination and the platform-specific wheel selection in the lockfile.

| Package | Version | License evidence |
| --- | --- | --- |
| Laya | 0.3.28 | [Apache-2.0 source LICENSE](https://github.com/NandhaKishorM/laya/blob/v0.3.28/LICENSE); [exact PyPI metadata](https://pypi.org/pypi/laya/0.3.28/json). |
| Torch | 2.14.1 on tested macOS; 2.14.1+cpu on tested Ubuntu/Python 3.12.3 | Installed macOS wheel license files and metadata: Apache-2.0, Apache-2.0 WITH LLVM-exception, BSD-2-Clause, BSD-3-Clause, BSL-1.0, MIT; [version metadata](https://pypi.org/pypi/torch/2.14.1/json). Linux CPU wheel metadata declares the same expression; the candidate-specific native runtime receipt is below. Do not label the entire distribution with just one of these licenses. |
| Transformers | 5.18.0 | Installed Apache-2.0 LICENSE; [version metadata](https://pypi.org/pypi/transformers/5.18.0/json), [upstream license](https://github.com/huggingface/transformers/blob/main/LICENSE). |
| huggingface-hub | 1.33.0 | Installed Apache-2.0 LICENSE; [version metadata](https://pypi.org/pypi/huggingface-hub/1.33.0/json), [upstream license](https://github.com/huggingface/huggingface_hub/blob/main/LICENSE). The resolver selected this compatible version; registry-latest 2.1.1 was not used. |
| Safetensors | 0.8.0 | Apache-2.0 verified by reading `safetensors-0.8.0.dist-info/licenses/LICENSE` in the installed wheel. The PyPI `license` field was null; the Apache classifier alone was not the final check. [Version metadata](https://pypi.org/pypi/safetensors/0.8.0/json). |
| NumPy | 2.5.3 | Installed LICENSE and bundled notice files read; metadata declares BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0. [Version metadata](https://pypi.org/pypi/numpy/2.5.3/json). |

The [Laya project manifest](https://github.com/NandhaKishorM/laya/blob/v0.3.28/pyproject.toml) declares Torch/Transformers/Safetensors/HF Hub/NumPy dependencies and Python >=3.10. It does not require MLX. The original native compatibility check used Python 3.12.13 on macOS arm64. Later product tests establish the specific macOS and Ubuntu/Python 3.12.3 paths below, not every supported interpreter or machine.

Laya 0.3.28 was uploaded to PyPI on **5 October 2026 at 18:05:12 UTC**. Its wheel SHA256 is `a1493cff474c0a5d84861db55c0c5c9b17f1db8561e458764da9a322dc542a88`. The research's 0.3.24 recommendation is superseded deliberately: 0.3.28 fixes published-wheel packaging and additional calibration/runtime defects. See the [release](https://github.com/NandhaKishorM/laya/releases/tag/v0.3.28).

## Linux CPU selection and rejected CUDA dependencies

The initial T00 lock resolved PyPI `torch==2.14.1` to a Linux CUDA dependency graph, including `cuda-toolkit` and `nvidia-cublas==13.1.1.3`. The latter explicitly declares `LicenseRef-NVIDIA-Proprietary` in its [exact package metadata](https://pypi.org/pypi/nvidia-cublas/13.1.1.3/json). That default is rejected under the open-source runtime constraint. Setting `device="cpu"` at inference time does not change installed package dependencies.

Use these two entries in the existing `laya` optional-dependency array, preserving its other pinned packages:

```toml
"torch==2.14.1+cpu; sys_platform == 'linux'",
"torch==2.14.1; sys_platform != 'linux'",
```

Select the official CPU index only for Linux:

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", marker = "sys_platform == 'linux'" },
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true
```

This follows [uv's official PyTorch source/index mechanism](https://docs.astral.sh/uv/guides/integration/pytorch/); `explicit = true` confines the alternate index to the named package. The `+cpu` requirement must also be present in standard dependency metadata, because `tool.uv.sources` alone does not configure other installers or consumers of the published distribution. A plain `torch==2.14.1` requirement can match a CUDA build; the Linux `==2.14.1+cpu` requirement instead fails if no CPU source is configured. See the [Python packaging version-matching rules](https://packaging.python.org/en/latest/specifications/version-specifiers/#version-matching). The supported repository installation uses the committed lock with `uv sync --locked --extra laya`; any later pip instructions must explicitly arrange the CPU source too.

The following **Linux x86_64, glibc >=2.28** artifacts were listed in the [official CPU index](https://download.pytorch.org/whl/cpu/torch/) on 6 October 2026. Direct wheel HEAD requests returned HTTP 200, and both small `.whl.metadata` responses were read. Hashes are published index values, not hashes computed from downloaded wheel binaries. No Linux wheel was installed or executed during this check.

| Python | CPU wheel | Bytes from HEAD | Published SHA256 |
| --- | --- | ---: | --- |
| 3.12 | [torch-2.14.1+cpu-cp312-cp312-manylinux_2_28_x86_64.whl](https://download.pytorch.org/whl/cpu/torch-2.14.1%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl) | 196,253,677 | `5a6363570c753812540a05eb82380e329469cbe668643e88111414c12627711f` |
| 3.13 | [torch-2.14.1+cpu-cp313-cp313-manylinux_2_28_x86_64.whl](https://download.pytorch.org/whl/cpu/torch-2.14.1%2Bcpu-cp313-cp313-manylinux_2_28_x86_64.whl) | 196,253,851 | `331fa474e26e428e2e6af1143b2fdab19cee492d7d21897b8899ce1c14755662` |

The [3.12 metadata](https://download.pytorch.org/whl/cpu/torch-2.14.1%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl.metadata) and [3.13 metadata](https://download.pytorch.org/whl/cpu/torch-2.14.1%2Bcpu-cp313-cp313-manylinux_2_28_x86_64.whl.metadata) declare `Version: 2.14.1+cpu`, no CUDA/NVIDIA requirements, and `License-Expression: Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT`. Their ordinary dependencies are filelock, typing-extensions, setuptools, SymPy, networkx, Jinja2, and fsspec. Optional metadata extras add optree, opt-einsum, or PyYAML; Actseal does not select those Torch extras.

Keep macOS on PyPI to preserve the tested Python 3.12 arm64 wheel: `torch-2.14.1-cp312-cp312-macosx_14_0_arm64.whl`, 127,307,099 bytes, SHA256 `420dbf314c180ee4b86e9bc00aee5746a7d6e5bacdd7df925af671ed393f0b2e`. The CPU index serves a differently hashed macOS artifact, so an all-platform index switch would change the tested binary.

**Verified:** CPU artifact availability, published hashes, license declarations, declared dependency metadata, and the corrected resolution in the final T00 lock audited below. That lock has no CUDA/NVIDIA/Triton package and retains the tested macOS hash. Earlier direct metadata requests to some `download-r2.pytorch.org` index links returned HTTP 403, while equivalent `download.pytorch.org` requests returned HTTP 200. Successful locking was not itself a Linux runtime test; the later native product workflow below supplies that separate evidence for its exact candidate/environment. Full T30 integration and final-release checks remain pending. No support claim extends to other Linux architectures or libc variants from these checks.

## Verified provider milestone on macOS and Linux

On **6 October 2026**, the parent orchestrator independently accepted the corrected provider/normalizer milestone at **`17ed0875541ecfa6402991dc90e278beb2f4cc01`**, recorded in [REVIEW T30-02](../plan/reviews/T30-02.md). Root reran 243 provider/normalizer unit tests in **4.12 s** and five cached-native product tests on macOS/Python 3.12.13 in **4.58 s**, plus targeted lint, formatting and strict typing. Both [push CI](https://github.com/ajaysurya1221/actseal/actions/runs/37439252390) and [PR CI](https://github.com/ajaysurya1221/actseal/actions/runs/37439282488) passed all four Linux/macOS Python 3.12/3.13 matrix jobs at that candidate; those ordinary jobs are distinct from native inference.

The separate [Linux native workflow](https://github.com/ajaysurya1221/actseal/actions/runs/37439327535) succeeded at the same candidate. Its logs confirm Ubuntu, Python **3.12.3**, **laya 0.3.28** and **torch 2.14.1+cpu** installed from the frozen graph. The pinned checkpoint snapshot was prepared in a separate step, then **five cached-offline Actseal product tests passed in 10.75 s**. This updates the earlier metadata-only Linux status with actual installation/inference evidence.

These are test-suite elapsed times, not per-request latency or throughput measurements. The receipt verifies the tested product adapter paths; it establishes neither broad hardware support nor model quality/calibration. **Full T30 remains PARTIAL** while the fault campaign is integrated; no release acceptance follows from this milestone. The exact commands and provenance are appended to [VERIFICATION](../plan/VERIFICATION.md#product-adapter-milestone--6-october-2026).

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

## Resolved lockfile license inventory

Final T00 lock audited on **6 October 2026**: `.worktrees/t00/uv.lock`, SHA256 `06eec429c7bd6d9dda0d960cd36a13b121a6e0c85f0e910a8bd913f651163268`. It contains **54 package records: Actseal plus 53 third-party records covering 52 unique third-party names**. Torch appears twice for the platform-specific builds. This inventory replaces the earlier 35-distribution preflight snapshot; that snapshot also contained pip, which is not in this product lock. Python, uv, the build backend, and GitHub Actions are recorded separately above rather than counted as locked runtime packages.

Every third-party record was checked against its exact-version PyPI JSON endpoint, except Linux CPU Torch, which was checked against official wheel metadata. Null license fields and generic BSD labels were not treated as proof: the exceptions below were resolved from already-installed exact-version license files or tagged upstream LICENSE files. These checks downloaded metadata and text only, with no package or weight binary downloads.

**Scope:** “Laya” means reachable only from the optional inference extra; “Dev” means reachable only from the development group; “Both” means shared by those two graphs. Reachability includes locked platform-marker alternatives, not a claim that every record installs on every platform. The fixture/core runtime has no third-party requirements. There are 30 Laya-only names, 17 development-only names, and five shared names.

| Transitive group | Why it is present |
| --- | --- |
| Inference and numerical support | Laya brings Torch, Transformers, NumPy, Safetensors, tokenizers, regex, SymPy/mpmath, networkx, Jinja2/MarkupSafe, and setuptools for the native CPU path. |
| Artifact download, cache, and transport | Hugging Face Hub brings hf-xet, fsspec, filelock, HTTPX/httpcore/h11, AnyIO, certifi, and idna to prepare and cache the pinned model. |
| Upstream parsing and console utilities | Transformers/Hub bring PyYAML, packaging, typing-extensions, tqdm, click, and Typer; Typer brings annotated-doc, Rich, Markdown parsing, Pygments, and shellingham. Actseal does not add its own CLI framework. |
| Type, test, and lint tooling | mypy brings ast-serialize, librt, mypy-extensions, pathspec, and typing-extensions; pytest brings iniconfig, pluggy, packaging, and Pygments; Ruff is a direct development tool. |
| Hook environment management | pre-commit brings cfgv, identify, nodeenv, PyYAML, and virtualenv; virtualenv brings distlib, filelock, packaging, platformdirs, and python-discovery. nodeenv is transitive tooling, not a Node requirement for Actseal core. |

| Package | Locked version | Scope | Verified license declaration / file | Exact primary source |
| --- | --- | --- | --- | --- |
| annotated-doc | 0.0.5 | Laya | MIT | [PyPI 0.0.5](https://pypi.org/pypi/annotated-doc/0.0.5/json) |
| anyio | 4.15.1 | Laya | MIT | [PyPI 4.15.1](https://pypi.org/pypi/anyio/4.15.1/json) |
| ast-serialize | 0.12.1 | Dev | MIT | [PyPI 0.12.1](https://pypi.org/pypi/ast-serialize/0.12.1/json) |
| certifi | 2026.7.22 | Laya | MPL-2.0 | [PyPI 2026.7.22](https://pypi.org/pypi/certifi/2026.7.22/json) |
| cfgv | 3.5.0 | Dev | MIT | [PyPI 3.5.0](https://pypi.org/pypi/cfgv/3.5.0/json) |
| click | 8.5.0 | Laya | BSD-3-Clause | [PyPI 8.5.0](https://pypi.org/pypi/click/8.5.0/json) |
| distlib | 0.4.3 | Dev | PSF-2.0 | [PyPI 0.4.3](https://pypi.org/pypi/distlib/0.4.3/json) |
| filelock | 4.0.12 | Both | MIT | [PyPI 4.0.12](https://pypi.org/pypi/filelock/4.0.12/json) |
| fsspec | 2026.9.0 | Laya | BSD-3-Clause | [PyPI 2026.9.0](https://pypi.org/pypi/fsspec/2026.9.0/json) |
| h11 | 0.16.0 | Laya | MIT | [PyPI 0.16.0](https://pypi.org/pypi/h11/0.16.0/json) |
| hf-xet | 1.6.0 | Laya | Apache-2.0 | [PyPI 1.6.0](https://pypi.org/pypi/hf-xet/1.6.0/json) |
| httpcore | 1.0.9 | Laya | BSD-3-Clause | [PyPI 1.0.9](https://pypi.org/pypi/httpcore/1.0.9/json) |
| httpx | 0.28.1 | Laya | BSD-3-Clause | [PyPI 0.28.1](https://pypi.org/pypi/httpx/0.28.1/json) |
| huggingface-hub | 1.33.0 | Laya | Apache-2.0 | [PyPI 1.33.0](https://pypi.org/pypi/huggingface-hub/1.33.0/json) |
| identify | 2.6.20 | Dev | MIT | [PyPI 2.6.20](https://pypi.org/pypi/identify/2.6.20/json) |
| idna | 3.20 | Laya | BSD-3-Clause | [PyPI 3.20](https://pypi.org/pypi/idna/3.20/json) |
| iniconfig | 2.3.0 | Dev | MIT | [PyPI 2.3.0](https://pypi.org/pypi/iniconfig/2.3.0/json) |
| jinja2 | 3.1.6 | Laya | BSD-3-Clause | [PyPI 3.1.6](https://pypi.org/pypi/jinja2/3.1.6/json); [version LICENSE](https://github.com/pallets/jinja/blob/3.1.6/LICENSE.txt) |
| laya | 0.3.28 | Laya | Apache-2.0 | [PyPI 0.3.28](https://pypi.org/pypi/laya/0.3.28/json) |
| librt | 0.16.0 | Dev | MIT | [PyPI 0.16.0](https://pypi.org/pypi/librt/0.16.0/json) |
| markdown-it-py | 4.2.0 | Laya | MIT | [PyPI 4.2.0](https://pypi.org/pypi/markdown-it-py/4.2.0/json); [version LICENSE](https://github.com/executablebooks/markdown-it-py/blob/v4.2.0/LICENSE) and installed bundled MIT notice |
| markupsafe | 3.0.4 | Laya | BSD-3-Clause | [PyPI 3.0.4](https://pypi.org/pypi/markupsafe/3.0.4/json) |
| mdurl | 0.1.2 | Laya | MIT | [PyPI 0.1.2](https://pypi.org/pypi/mdurl/0.1.2/json); installed `mdurl-0.1.2.dist-info/LICENSE`, including bundled MIT notice |
| mpmath | 1.3.0 | Laya | BSD-3-Clause | [PyPI 1.3.0](https://pypi.org/pypi/mpmath/1.3.0/json); [version LICENSE](https://github.com/mpmath/mpmath/blob/1.3.0/LICENSE) |
| mypy | 2.4.0 | Dev | MIT | [PyPI 2.4.0](https://pypi.org/pypi/mypy/2.4.0/json) |
| mypy-extensions | 1.1.0 | Dev | MIT | [PyPI 1.1.0](https://pypi.org/pypi/mypy-extensions/1.1.0/json); [version LICENSE](https://github.com/python/mypy_extensions/blob/1.1.0/LICENSE) |
| networkx | 3.7 | Laya | BSD-3-Clause | [PyPI 3.7](https://pypi.org/pypi/networkx/3.7/json) |
| nodeenv | 1.11.0 | Dev | BSD-3-Clause | [PyPI 1.11.0](https://pypi.org/pypi/nodeenv/1.11.0/json); [version LICENSE](https://github.com/ekalinin/nodeenv/blob/1.11.0/LICENSE) |
| numpy | 2.5.3 | Laya | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | [PyPI 2.5.3](https://pypi.org/pypi/numpy/2.5.3/json) |
| packaging | 26.3 | Both | Apache-2.0 OR BSD-2-Clause | [PyPI 26.3](https://pypi.org/pypi/packaging/26.3/json) |
| pathspec | 1.1.1 | Dev | MPL-2.0 | [PyPI 1.1.1](https://pypi.org/pypi/pathspec/1.1.1/json); [version LICENSE](https://github.com/cpburnz/python-pathspec/blob/v1.1.1/LICENSE) |
| platformdirs | 4.12.3 | Dev | MIT | [PyPI 4.12.3](https://pypi.org/pypi/platformdirs/4.12.3/json) |
| pluggy | 1.6.0 | Dev | MIT | [PyPI 1.6.0](https://pypi.org/pypi/pluggy/1.6.0/json) |
| pre-commit | 4.6.2 | Dev | MIT | [PyPI 4.6.2](https://pypi.org/pypi/pre-commit/4.6.2/json) |
| pygments | 2.21.0 | Both | BSD-2-Clause | [PyPI 2.21.0](https://pypi.org/pypi/pygments/2.21.0/json) |
| pytest | 9.1.1 | Dev | MIT | [PyPI 9.1.1](https://pypi.org/pypi/pytest/9.1.1/json) |
| python-discovery | 1.6.1 | Dev | MIT | [PyPI 1.6.1](https://pypi.org/pypi/python-discovery/1.6.1/json) |
| pyyaml | 6.0.3 | Both | MIT | [PyPI 6.0.3](https://pypi.org/pypi/pyyaml/6.0.3/json) |
| regex | 2026.9.29 | Laya | Apache-2.0 AND CNRI-Python | [PyPI 2026.9.29](https://pypi.org/pypi/regex/2026.9.29/json) |
| rich | 15.0.0 | Laya | MIT | [PyPI 15.0.0](https://pypi.org/pypi/rich/15.0.0/json) |
| ruff | 0.16.10 | Dev | MIT | [PyPI 0.16.10](https://pypi.org/pypi/ruff/0.16.10/json) |
| safetensors | 0.8.0 | Laya | Apache-2.0 | [PyPI 0.8.0](https://pypi.org/pypi/safetensors/0.8.0/json); installed `safetensors-0.8.0.dist-info/licenses/LICENSE` |
| setuptools | 84.0.0 | Laya | MIT | [PyPI 84.0.0](https://pypi.org/pypi/setuptools/84.0.0/json) |
| shellingham | 1.5.4 | Laya | ISC | [PyPI 1.5.4](https://pypi.org/pypi/shellingham/1.5.4/json) |
| sympy | 1.14.0 | Laya | BSD-3-Clause AND MIT (bundled code) | [PyPI 1.14.0](https://pypi.org/pypi/sympy/1.14.0/json); [version LICENSE and bundled notices](https://github.com/sympy/sympy/blob/sympy-1.14.0/LICENSE) |
| tokenizers | 0.23.2 | Laya | Apache-2.0 | [PyPI 0.23.2](https://pypi.org/pypi/tokenizers/0.23.2/json); [version LICENSE](https://github.com/huggingface/tokenizers/blob/v0.23.2/LICENSE) |
| torch | 2.14.1 | Laya | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | [PyPI 2.14.1](https://pypi.org/pypi/torch/2.14.1/json) |
| torch | 2.14.1+cpu | Laya | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | [official wheel metadata](https://download.pytorch.org/whl/cpu/torch-2.14.1%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl.metadata) |
| tqdm | 4.70.1 | Laya | MPL-2.0 AND MIT | [PyPI 4.70.1](https://pypi.org/pypi/tqdm/4.70.1/json) |
| transformers | 5.18.0 | Laya | Apache-2.0 | [PyPI 5.18.0](https://pypi.org/pypi/transformers/5.18.0/json) |
| typer | 0.27.2 | Laya | MIT | [PyPI 0.27.2](https://pypi.org/pypi/typer/0.27.2/json) |
| typing-extensions | 4.16.0 | Both | PSF-2.0 | [PyPI 4.16.0](https://pypi.org/pypi/typing-extensions/4.16.0/json) |
| virtualenv | 21.14.5 | Dev | MIT | [PyPI 21.14.5](https://pypi.org/pypi/virtualenv/21.14.5/json) |

**Ambiguities resolved:** Jinja2, mpmath, and nodeenv use BSD-3-Clause as confirmed by all three license conditions; SymPy includes BSD-3-Clause notices and MIT-licensed latex2sympy code. mypy-extensions has no PyPI license declaration or classifier but its installed and tagged LICENSE both explicitly grant MIT. markdown-it-py, mdurl, pathspec, Safetensors, and tokenizers have absent license-expression/legacy fields; exact license files confirm the table. python-discovery embeds the full MIT permission/disclaimer text in its exact-version metadata. A missing SPDX field is not silently substituted with a guess.

**Audit result:** no unresolved missing, ambiguous, or proprietary package-level license remains in this inspected lock. No `cuda*`, `nvidia*`, or Triton package is present. The macOS Python 3.12 Torch wheel retains SHA256 `420dbf314c180ee4b86e9bc00aee5746a7d6e5bacdd7df925af671ed393f0b2e`; Linux Torch resolves to the official CPU registry and `2.14.1+cpu`. This establishes the corrected resolution recorded in the lock; this audit did not execute a Linux installation or inference.

This is an exact-version declaration and selected license-file audit, not an exhaustive audit of every file embedded in every platform wheel. Keep compound expressions and applicable notices intact when redistributing dependencies. Any changed locked version, source, or license must be rechecked; an unresolved declaration or incompatible license blocks publication of the affected dependency path. The separate provider milestone above now records Linux installation/native execution and hosted CI. Final task integration and release-candidate checks must still pass; historical license auditing is not their substitute.

## Changes and release gate

Record dependency updates as explicit changes to the frozen provider identity when they can affect predictions or normalization. Re-run the native reference smoke and associated fixtures before accepting such an update; then regenerate the committed lockfile using the pinned uv version. Do not float package or model aliases in published evidence.

Jev is an optional v2 service adapter, not a dependency or substitute for the open local path. Its [customer agreement](https://typesafe.ai/legal/mca) is proprietary service terms, not an OSI license. No vendor SDK, hosted tier, access key, or paid API call is required by the v1 reference stack.

Before release, CI must verify the final lockfile, build, tests, lint, formatting, types, and pre-commit commands. A successful upstream smoke does not replace those product checks. Include all attributed copied-code notices in the repository and distribution, and report any newly introduced dependency/license before merging it.
