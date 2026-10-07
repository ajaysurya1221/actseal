# REVIEW 14 — standalone renderer preparation

Verdict: **REVISE** at `c788dad19fd49368ed882aa97a3a3105b25f816d`.
Reviewed demo.py SHA256:
`a5d8cc057fd143776bccf4c362d78a8213e514f614ca0d019641050b3b2a54d5`.

1. Graphic-control delays are counted without their image. Parent and
   independent tiny in-memory probes accept a dangling 2000-centisecond
   control after the final image and two 1000-centisecond controls before
   one image as 20-second GIFs. Associate a single pending control with its
   following image; reject duplicate/dangling controls and malformed fixed
   graphic-control blocks. Do not count unshown time.
2. Complete-format validation is incomplete. A ten-byte header raises
   uncaught IndexError; an empty LZW image-data sequence counts as a frame.
   Validate bounded headers, tables, image descriptors, code-size fields,
   nonempty image-data subblocks and terminators explicitly. Errors must be
   DemoError. Do not claim pixel decoding if only structure is checked.
3. The file cap follows an unbounded read and a full parse. Read at most
   the cap plus one and reject oversized byte inputs before walking them.
   Keep the strict less-than-3,000,000 requirement.
4. Cast output payload types and the procedure's exact TERM/LANG env keys
   are unchecked; non-string output can be silently ignored by the shared
   parser. Enforce the owned renderer's structural rules. Command markers
   are consistency checks, not proof of execution or PyPI provenance;
   the separate post-publication binding receipt remains necessary.
5. Reverify agg immediately before each variant execution, with a regression
   for a changed cached binary between variants. Correct the stale claim
   that official tools remain permission-blocked in an additive report.
   Accepted tool provisioning/history is separate from this task's unrun
   genuine rendering. Preserve the original report unchanged.

Parent independently passed56 focused tests in0.17 seconds and strict mypy
over17 files. The tests do not currently cover the demonstrated defects.
The full visual suite's known missing-architecture failure remains visible.
No actual recording/GIF or inventory registration exists; no main merge.

V1-046 authorizes only these repairs and replacing the flawed procedure
walker with the corrected validator. Do not broaden the renderer into a
general image decoder, alter pins, or relax the original acceptance rules.
