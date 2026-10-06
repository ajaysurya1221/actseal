# ADR 0006: Pin the tested Laya CPU path and keep inference optional

- Status: accepted; optional adapter product acceptance recorded below. Final release gates remain separate.
- Date: 2026-10-06.
- Initial preflight provenance: model-verification lane supplied two successful macOS native smoke-run receipts and subsequently checked Linux CPU wheel metadata and availability. Linux inference was not run at that stage; later product execution is recorded below.

## Decision

Use the following **tested preflight stack** for the initial Laya adapter. Pin it in the optional inference dependency group and lockfile when the executor creates the package. The standard-library core and fixture quickstart do not require it.

| Component | Tested version | Licensing reference |
|---|---|---|
| Python | 3.12.13 | PSF; see the release/license inventory in [dependencies](../dependencies.md). |
| Laya | 0.3.28 | Apache-2.0; [upstream LICENSE](https://github.com/NandhaKishorM/laya/blob/main/LICENSE). |
| PyTorch | 2.14.1 on macOS; 2.14.1+cpu selected for Linux | Compound Apache/BSD/BSL/MIT license expression, including the LLVM exception; complete inventory and distinction between tested binaries and metadata checks in [dependencies](../dependencies.md). |
| Transformers | 5.18.0 | Apache-2.0 upstream; complete inventory in [dependencies](../dependencies.md). |
| Hugging Face Hub | 1.33.0 | Apache-2.0 upstream; complete inventory in [dependencies](../dependencies.md). |
| safetensors | 0.8.0 | Apache-2.0; verifier reports checking installed wheel LICENSE. |
| NumPy | 2.5.3 | BSD-3-Clause upstream distribution with bundled notices; complete inventory in [dependencies](../dependencies.md). |

Pin public model `convaiinnovations/laya-typed-decisions` to revision `e929ae5cf69bc34259cd2f95c9e91145b818b1f0`, under the Apache-2.0 [model card](https://huggingface.co/convaiinnovations/laya-typed-decisions/blob/e929ae5cf69bc34259cd2f95c9e91145b818b1f0/README.md). The verifier reports 421,293,830 F16 stored parameters and a model file of 842,609,220 bytes, SHA-256 `4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e`. Loading for the tested route used CPU FP32.

Use Torch CPU inference with four threads, `device="cpu"`, `backend="eager"`, `compile=False`, and `fast=False`. The verified loader is:

```python
laya.load(
    "convaiinnovations/laya-typed-decisions",
    revision="e929ae5cf69bc34259cd2f95c9e91145b818b1f0",
    device="cpu",
    backend="eager",
    compile=False,
    fast=False,
)
```

This is a configuration reference for the executor, not product code implemented by this planning task. Do not substitute the research's unverified MLX route or its older Laya 0.3.24 recommendation. MPS/GPU acceleration and additional model families are outside v1.

## Linux packaging amendment

Reject the initial T00 PyPI-only Linux resolution. `torch==2.14.1` there pulls a CUDA graph including `nvidia-cublas==13.1.1.3`, whose [version metadata](https://pypi.org/pypi/nvidia-cublas/13.1.1.3/json) declares `LicenseRef-NVIDIA-Proprietary`. Selecting CPU at runtime cannot fix that installation-time conflict with the user's open-source constraint.

Require `torch==2.14.1+cpu; sys_platform == 'linux'` and `torch==2.14.1; sys_platform != 'linux'` in the optional Laya dependency metadata. Map Torch to the explicit `pytorch-cpu` index at `https://download.pytorch.org/whl/cpu` only when `sys_platform == 'linux'`, using `[tool.uv.sources]` and `[[tool.uv.index]]` as specified in [dependencies](../dependencies.md#linux-cpu-selection-and-rejected-cuda-dependencies). The `+cpu` dependency is necessary beyond uv's source configuration: other consumers do not inherit that tool-specific table and must fail rather than silently select PyPI CUDA packages. The [uv PyTorch guide](https://docs.astral.sh/uv/guides/integration/pytorch/) documents explicit indexes and platform markers.

The [official CPU index](https://download.pytorch.org/whl/cpu/torch/) lists Python 3.12 and 3.13 Linux x86_64 wheels requiring glibc >=2.28. Their direct wheel HEAD and metadata requests returned HTTP 200 on 6 October 2026. The published SHA256 values are:

- Python 3.12: `5a6363570c753812540a05eb82380e329469cbe668643e88111414c12627711f`.
- Python 3.13: `331fa474e26e428e2e6af1143b2fdab19cee492d7d21897b8899ce1c14755662`.

The [3.12 metadata](https://download.pytorch.org/whl/cpu/torch-2.14.1%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl.metadata) and [3.13 metadata](https://download.pytorch.org/whl/cpu/torch-2.14.1%2Bcpu-cp313-cp313-manylinux_2_28_x86_64.whl.metadata) declare `2.14.1+cpu`, no CUDA/NVIDIA dependency, and `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT`. This verifies published availability and license/dependency declarations, not installed Linux compatibility or a full binary-notice audit. Wheel binaries were not downloaded during this check.

Preserve the tested macOS Python 3.12 arm64 PyPI wheel hash `420dbf314c180ee4b86e9bc00aee5746a7d6e5bacdd7df925af671ed393f0b2e`. Switching macOS to the CPU index would select a differently hashed artifact. The Linux source marker therefore preserves the evidence behind the existing macOS smoke.

At this amendment's preflight stage, actual uv resolution and Linux live runtime checks were pending. The required lock inspection and Linux integration acceptance were subsequently completed as recorded below. Some `download-r2.pytorch.org` metadata links returned HTTP 403 while equivalent `download.pytorch.org` links returned HTTP 200; direct availability checks did not substitute for a successful uv lock/install. No other Linux architecture or libc is accepted by this amendment.

## Product acceptance update — 6 October 2026

T00's accepted lock resolves the CPU-only graph without CUDA/NVIDIA/Triton nodes;
the full pinned license inventory is in [dependencies](../dependencies.md).
[REVIEW T30-02](../../plan/reviews/T30-02.md) accepts provider milestone
`17ed0875541ecfa6402991dc90e278beb2f4cc01`: root ran five cached-native macOS
tests in 4.58 s, and [Linux run 37439327535](https://github.com/ajaysurya1221/actseal/actions/runs/37439327535)
ran five product tests in 10.75 s on Ubuntu/Python 3.12.3 with Torch 2.14.1+cpu.
These are suite durations, not inference benchmarks or model-quality evidence.

[REVIEW T30-03](../../plan/reviews/T30-03.md) accepts full T30 at
`8b1efd6314b5b65ecb51f292a5bc767ff8b93ed7`; the native-tested adapter and
normalization bytes are unchanged. Native Python 3.13 and broader hardware are
not established by these receipts. Final CLI integration and release acceptance
remain separate gates; no historical preflight claim is retrospectively widened.

## Evidence and known limits

The verifier's online and fresh offline subprocess each returned the same billing category on one case with exit 0. Peak process RSS was about 1.87 GB online and 2.92 GB offline on the supplied Mac M5 Pro / 24 GiB system. These runs establish narrow loader/inference feasibility, not throughput, model quality, or community-platform support. [VERIFICATION](../../plan/VERIFICATION.md) retains exact measurements and provenance.

The pinned model card reports calibration on training rows; a repaired notebook does not establish that these checkpoint weights were refitted. Treat confidence as an unvalidated score until the frozen Actseal selector has independent certification evidence. A native `choice:11+` warning reports `0.10058` clamped to `0.5` on each load; preserve and explain it rather than suppress it. The checkpoint is specialized around four synthetic workflows, not established as a general decision model.

The provider returned rounded probabilities whose sum is `1.0001`. The frozen normalizer may apply only an explicitly specified rounding tolerance and deterministic renormalization, preserving raw values. This permitted transformation must be bound to the normalizer version and reproduced during replay. Arbitrary malformed-response repair remains forbidden.

`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` were used for the fresh cached subprocess. These are library offline flags, not an operating-system egress firewall. A download is needed for first real-model use; the first 60-second fixture quickstart requires no model download.

## License and publication gate

The tested versions are a reproducibility choice, not a claim to be the newest or safest releases. The executor must freeze the full resolved dependency graph and retain applicable distribution notices. No unverified transitive license may become load-bearing. [dependencies](../dependencies.md) owns the consolidated checked inventory; unresolved licensing blocks publication of the affected optional path, not operation of the dependency-free fixture core.
