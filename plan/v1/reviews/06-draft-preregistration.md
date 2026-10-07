# REVIEW 06 — interrupted preregistration draft

Verdict: REVISE before any preregistration approval. This is a static review of an incomplete, uncommitted draft interrupted by Fable quota. Unfinished modules are not counted as defects. No implementation or live-run acceptance.

P1: protocol.py549 loads onlytop-level shape/self-seal; verify_preregistration588–670 does not compare declaredexpectedidentity, source, selection, policy, collectionlimits, metrics, inventoryhashes ormostproducermetadata with frozen/currentauthorities. Altering and resealing budget_seconds, threshold, brierformula orpackage_version leaves existingchecksunchanged. contract_toml_sha256 isignored; a changedTOMLcommentpassessemanicparsing.

Requiredchanges: reconstruct and compare the complete expected document with stricttypes; bindactualcontractbytes; addresealed-mutation negatives for each boundgroup. Preserve separateCodexpreregistrationreview/live-dispatchgate.

Fullread hashes: source.py8ff065623478890586e2f2a27ba240a6876cea43d068bb8c4c76df389489de29; protocol.pyaf9f9798cd1ab77a412a8450253924053af517924eb7a4c2fcacd0eada975639; __init__.pyf2a9cd641cbb82bbf1753b817e66e0ef1e5b293a303363f18e5fc38631745ecd. Sourceonly; noexecution/provider/key/scratchscript. Selectionalgorithm, pinnedhashes, identityconstants, policy anddeclaredmetrics otherwisealign.
