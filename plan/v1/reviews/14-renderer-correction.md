# REVIEW 14 — bounded renderer correction

Verdict: **REVISE** at `d8b10a36df6ec62dc501057e88c26545ae124cc3`.

All five prior repairs are present. Parent410 visual tests pass with the same
one known missing-architecture failure (1.77s); strict17-file typing, hooks
and diff checks pass. Independent88 focused tests pass (0.31s). Original
dangling/duplicate control, truncated-header and empty-image probes now
raise DemoError. Ownership and original reports are preserved.

Two bounded required changes remain within V1-046:

1. The generic non-GCE extension branch accepts malformed application/plain
   text/unknown extensions and retains a pending image delay across them.
   Independent probes insert `21ff00`, `210100` or `210000` after a GCE and
   are incorrectly accepted. Support only the needed agg subset: bounded
   comments and application extensions with their required11-byte header;
   reject unsupported plain-text/unknown labels. Keep any pending GCE across
   allowed non-graphic extensions only. Add these three regressions and a
   correctly shaped application-extension positive. No pixel decoder.
2. In recording.md step7, replace "that proof is the step3/5 binding" with
   evidence/receipt wording. Structural checks cannot authenticate output or
   establish execution; the separately recorded binding provides supporting
   evidence, not a blanket proof claim.

Preserve earlier reports and add a final correction report. No inventory
activation, genuine recording, product asset or public-interface change.
No merge until these fixes have independent acceptance.
