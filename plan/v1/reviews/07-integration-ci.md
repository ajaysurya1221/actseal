# REVIEW 07 — merge-preview CI

Verdict: REVISE for integration; do not merge PR35. Exactbranch277d8e23f0de161e72a8617c74d3b05e6d75069a passesallfourpushCIjobs37566824944. Merge-preview37566923811 againstupdatedmain fails7exampletests (Linux3.12:2923passed,1skipped,20deselected;131.82s). Logs independentlyretrieved; untrustedANSI strippedbeforeinspection.

The original archiveproducer a5fe0902… isnotregisteredforchanged runningproducer70fa95939f59… afteracceptednumericboundarycode. Core returnsERROR/integrity.lock and examplecorrectlyblocksqueueeffects. Preserveoriginalarchivebytes/lock. Task19 must explicitlyreview/register originalandfinalcompatibleproducers and rerunarchived evidence; do notreseal/exclude/treatERRORaspass. Two test_run.py333 expectations alsohardcode '(exact' forcommittedarchive andmustbeupdatedtotruthfullytestapprovedcross-producerbehavior alongsideexact-sourcefixtures.

This isknown integrationwork, not aflawin57passingtests againsttheunchangedproducer. SourcebranchACCEPTdoesnotoverridefailedmergeCI.
