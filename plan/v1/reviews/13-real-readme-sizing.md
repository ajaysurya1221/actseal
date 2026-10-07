# REVIEW 13 — real README sizing

Verdict: **REVISE** at `c84d515de1c4b76529178496e4673ceef68afaf7`.
Source semantics and temporary pixels otherwise have no identified blocker.
Independent source review matched architecture.py SHA256
`9e10de3b82518c7a69de5e1fca8e6d1136c7a82f25ed6dc6ae48a43a87572828`.

The seven groups, real module map, experimental Jev live boundary, synthetic
faults and provider-free replay are correct. Parent viewed all four temporary
light/dark desktop/mobile images. Earlier accepted hero/workflow/social bytes
are preserved. The executor reports335 visual and3896 ordinary tests passing;
parent has not rerun these because the sizing defect below requires revision.

## Required change

The assumed880/360 CSS-pixel image widths are larger than GitHub actually gives
the images. Read-only browser measurements on the public repository tree at
candidate5e7931a (not a local renderer) returned:

| Browser viewport width | Actual README image width |
| --- | --- |
| 320 | 254 |
| 360 | 294 |
| 1000 | 638 |
| 1100 | 658 |
| 1200 | 758 |
| 1280 | 838 |
| 1366 | 838 |

The file-preview page is wider; it must not substitute for the repository view.
At800px its image was702px and still selected the desktop variant. The current
README switches to mobile only at600px. Architecture/workflow desktop26-unit
text at838px becomes13.6175px; mobile30-unit text at294px becomes12.25px.
Both violate the explicit14px floor. Hero desktop28-unit labels fit at838px;
its mobile30-unit labels also require correction.

Correct measured display-width validation, font sizes/wrapping/layout and the
README responsive threshold together. Use838px desktop and254px mobile as
conservative validation widths for the measured320px-and-larger range. Select
mobile variants below1280px viewport. Preserve wording, topology, palette,
module traceability, no-overlap tests and all negative prerequisite checks.
Do not lower the14px floor, add horizontal scrolling or claim browser evidence
from standalone SVG dimensions. Preserve historical reports; add new receipts.

Follow-ups: bounded visual ownership amendment V1-051; separate README/ADR
documentation task; regenerated real pixels at measured widths; fresh actual
repository first-screen test and exact-head CI after integration. Browser
viewport override was reset after the measurement; no page content was edited.
