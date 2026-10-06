# ADR 0006: Pin the tested Laya CPU path and keep inference optional

- Status: accepted for the initial optional local adapter, subject to product-level acceptance.
- Date: 2026-10-06.
- Evidence provenance: model-verification lane supplied two successful native smoke-run receipts; the author of this ADR did not independently repeat those model runs.

## Decision

Use the following **tested preflight stack** for the initial Laya adapter. Pin it in the optional inference dependency group and lockfile when the executor creates the package. The standard-library core and fixture quickstart do not require it.

| Component | Tested version | Licensing reference |
|---|---|---|
| Python | 3.12.13 | PSF; see the release/license inventory in [dependencies](../dependencies.md). |
| Laya | 0.3.28 | Apache-2.0; [upstream LICENSE](https://github.com/NandhaKishorM/laya/blob/main/LICENSE). |
| PyTorch | 2.14.1 | BSD-3-Clause upstream distribution with bundled notices; complete inventory in [dependencies](../dependencies.md). |
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

## Evidence and known limits

The verifier's online and fresh offline subprocess each returned the same billing category on one case with exit 0. Peak process RSS was about 1.87 GB online and 2.92 GB offline on the supplied Mac M5 Pro / 24 GiB system. These runs establish narrow loader/inference feasibility, not throughput, model quality, or community-platform support. [VERIFICATION](../../plan/VERIFICATION.md) retains exact measurements and provenance.

The pinned model card reports calibration on training rows; a repaired notebook does not establish that these checkpoint weights were refitted. Treat confidence as an unvalidated score until the frozen Actseal selector has independent certification evidence. A native `choice:11+` warning reports `0.10058` clamped to `0.5` on each load; preserve and explain it rather than suppress it. The checkpoint is specialized around four synthetic workflows, not established as a general decision model.

The provider returned rounded probabilities whose sum is `1.0001`. The frozen normalizer may apply only an explicitly specified rounding tolerance and deterministic renormalization, preserving raw values. This permitted transformation must be bound to the normalizer version and reproduced during replay. Arbitrary malformed-response repair remains forbidden.

`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` were used for the fresh cached subprocess. These are library offline flags, not an operating-system egress firewall. A download is needed for first real-model use; the first 60-second fixture quickstart requires no model download.

## License and publication gate

The tested versions are a reproducibility choice, not a claim to be the newest or safest releases. The executor must freeze the full resolved dependency graph and retain applicable distribution notices. No unverified transitive license may become load-bearing. [dependencies](../dependencies.md) owns the consolidated checked inventory; unresolved licensing blocks publication of the affected optional path, not operation of the dependency-free fixture core.
