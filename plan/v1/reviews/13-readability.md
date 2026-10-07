# REVIEW 13 / 13R — architecture and measured-width correction

Verdict: **ACCEPT for source, generated static assets and local checks** at
`77a13bd6e8ed408a3579dfbdedeb761a796f6283`. Exact-head hosted CI, integrated
README selection and the final blind repository-first-screen gate remain.
This is not full release acceptance or permission to publish.

Parent read the renderer delta and report, and independently reproduced:

| Command | Result |
| --- | --- |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` | exit0;12SVGs and socialPNG byte-identical regeneration;4implemented/4planned |
| `uv run --frozen --group assets pytest tests/visual` | exit0;337passed in1.59s |
| `uv run --frozen mypy --strict docs/assets/src tests/visual` | exit0;29files |
| `uv run --frozen pytest -m "not integration and not packaging"` | exit0;3898passed,27deselected in74.21s |
| `uv run --frozen pre-commit run --all-files` | exit0;lint/format/strict typing PASS |
| `git diff --check` | exit0 |

These are this isolated branch's counts, not the later combined release matrix.
Native/packaging paths were unchanged and were not rerun for this visual delta.
The isolated renderer reports0README references because it predates README
integration; the combined reference gate must run with the accepted08R README.

Independent source reviewer and parent matched these final SHA256s:

```text
hero.py a96201c5213bca779e61085fc5c0431b9e8f7bef6f8d141ea71e7790cc7cc33a
how_it_works.py f3ee5077bb0d4aecdf523ddec453330317e13f7df96a8ba6b71e882ed074852c
architecture.py cbc172461a561dc58e74712a6923b54917fa9247c47d4bbfd1a6834ecad3c60d
inventory.py 5023cc7a17588584997b8896f190d678e765a18520d3eb77e8c5920d63907cd8
```

Seven architecture groups match real modules; only Laya/experimental Jev are
inside the live-provider boundary. Fixture, six synthetic faults and replay
remain deterministic paths. Replay edges do not reach providers. The five-stage
workflow preserves decisions/verdicts/exits, and hero text preserves all three
evidence limits. No runtime source, registry, tool/font pin, validator floor or
synthetic880px test probe changed. Desktop hero and social bytes match7820dba.

Parent viewed all12light/dark figure variants as actual resvg PNGs at838px
desktop and254px mobile, with no clipping, overlapping labels or unsupported
claim. PNG paths/hashes are in REPORT13R and were checked against the viewed
files. In particular the architecture hashes match its four838/254px entries.
These are standalone actual pixels at the measured widths, not a new browser
screenshot. Workflow/architecture minimum type is14.14125px desktop and
14.11111px mobile; desktop hero remains14.665px. Taller mobile canvases preserve
content and readable labels; no text was removed to satisfy the floor.

Two explanatory qualifications to the immutable REPORT13R: at638px an
unchanged27-unit desktop label is10.76625px, not the illustrative13.0px in
its open-issues paragraph. Also the validator uses the recorded display-width
constants; it does not automatically detect future GitHub layout changes.
Neither affects the accepted838/254px arithmetic or generated output. Future
layout changes require a new measured-width review before any guarantee.

Follow-ups: integrate paired08R, preserve original example/registry bytes,
run combined docs/assets/fullCI/rehearsal, final actual first-screen gate.
Real demo recording remains the approved post-PyPI exception, not completed.
