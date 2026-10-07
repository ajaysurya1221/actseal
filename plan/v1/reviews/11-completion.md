# REVIEW 11 — real hero assets

Verdict: ACCEPT for the hero figure, with exact-head hosted CI still required before merge. The assembled README blind test remains a release gate.

Claude authored fonts/notices/receipts461f9ee, generated assetsdb56f36 and report7bb32f4ca78194d5316e0615528420a521cdf78a. Codex transplanted only these three commits onto the Task11 parent5f3fee5, isolating finished hero work from unfinished social source. The new head736d912302645efe33a75b805b2718265a9e8604 contains byte-identical hero source, four SVGs, fonts and receipts. It changes no product code.

Independent review rasterized all four SVGs offline with resvg0.48.1, rechecking the approved archive digest and extracting only its regular executable member. It used the pinned fonts with --skip-system-fonts. At880x220 desktop and360x281 mobile, labels and all three evidence limits are readable; no clipping, overlap, security symbolism or extra guarantee. SVGs have outlined text and no external references, scripts or styles. Parent also viewed desktop light and mobile dark.

Hero SHA256 values:
- light:19a8f20f4987d69481622d372d6eb5de2262896a1b8f2db62d0f2ce7989b3fe6
- dark:77bb337db71e1224df3d83f43cf73754e84201d93cabf61c62f63d3492b3d324
- mobile light:0de55733d1a247328da52c793445b9d195d97caafa6aac0f0c8ab269efa990f3
- mobile dark:eeeac139209f95ae6f99cab7ea5770978a28156074eb0ada6585fd731a84d27e

Screenshots and exact command/hash receipt: /tmp/actseal-hero-pixel-review.ipoaufqp/receipt.json. Parent reran the exact hero regeneration check at736d912: four matches, zero errors;226 visual tests passed1.16s; all pre-commit hooks and diff checks passed. PR25 has been updated to this isolated head. The original Claude report's250-test total includes the social branch; it is not presented as this isolated branch's count.

Required changes: none in the reviewed hero scope. Follow-ups: current CI and final README integration/blind test. No social PNG or upload claim.
