# REVIEW09 CI integration glue

Verdict: ACCEPT for the six-file CI/packaging change atdec2afa97db4d174fba3d43bd22343f6e97d74b9. FullTask09 remains PARTIAL.

Required workflow outputs match the four Task12 variants. Each omission has a negative check. The sdist now includes the release helper and publish workflow required by its already-included tests. Its actual archive regular-file members and bytes are tested against the reviewed source; this does not claim arbitrary extracted-sdist execution or authentic inference.

Parent544 release tests passed16.32s. Initial PT007 lint failure was corrected by using a list of parametrized values; all hooks, tool typing and four affected tests subsequently passed. Independent review passed10 asset-gate tests and36 workflow/actual-sdist tests with UV_OFFLINE=1, plus owned lint/format/strict typing and workflow checks. No actual rendering, authoring setup, native inference or publication occurred.

Independent inspected sdist SHA256:1f51623b955dabc18eb2c1a8cafb0895bf1e7fe18d868a87781218616780bdec. This is a review artifact, not a release distribution. Final candidate build/test/promotion remains separate.

Ordinary-CI font/resvg setup is still awaiting the existing scoped download approval. Final hero/architecture declarations, docs/publishing gates and task-dependent package contents require their integration checks; no planned file is counted as delivered.
