# REVIEW 12 — actual pixel acceptance

Verdict: ACCEPT for the workflow figure. Source/assets unchanged from exact PR22headf712daef51ee005c1b34c9744dbe1d99cf499c33, reviewed in child2e2a7b220d401f5899df08bf41a6cff60769f11b.

The exact assets-group done-when independently passed: allfourSVGs match regeneration,0errors. Actualpixelreview used previously approved resvg0.48.1 after independently checking officialmacarchive SHA25606440eb5aa14a28cbfc7e40ae39e1ffa71adc051b89fbaa913b4f1d9b905d09f. Localtemp extraction only, no product/globalinstallchange. Systemfont fallbackHelvetica→ArialUnicodeMS was reported byrenderer; no JetBrainsfontsubstitution.

At880x220desktop and360x895mobile, allfourlight/darkpreviews show readablelabels, unobstructedarrows, correctdecisions/verdicts/exits and no visibleclipping/overlap/unsupportedassurance. Smallest14.3pxdesktop/15pxmobile. Parentalsoinspecteddesktoplightpixels.

Previewdirectory `/tmp/actseal-task12-pixels.cqi6Hi/`:
- how-it-works-light-880.png SHA2563f38d3bf8910092a5f16ea741ad9f7266c8aa33bd03755e490d1cf5c24df1054
- how-it-works-dark-880.png SHA256ff6cb31bc7b6758bef1b45c0d3abba64d1cacc988551716190e41f2bf86405b7
- how-it-works-mobile-light-360.png SHA256a67564676e844141b54c022b4d9659da2f9cc2f1ffa7e005ea723492c47d727a
- how-it-works-mobile-dark-360.png SHA25684cf890b020c05dc93140db61059f9ced5c00dbe8ff2c1dec807e117f2d79e2d

The CUA browser rejectedfileURLs and forbidsbrowserworkarounds, while explicitlypermitting materiallysaferalternatives not requiringtheblockedaction. No browserretry occurred. The separatelyapprovedoffline localrasterizer uses no browser/server/browser-script execution/CDP. This is not the blindREADME10secondtest; that remains Task20.

Exact-head hostedCIrefreshed: eightgreen37528503650/37528510828. Findings:none. Follow-ups: READMEintegration andblindtest.
