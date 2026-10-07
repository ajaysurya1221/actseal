# Final README first-screen comprehension receipt

Observed main:277d729c192a7e41ffc4432e5943e74cd4a87c35 (PR46); capture UTC:2026-10-07T09:32:34.498785+00:00.
URL:https://github.com/ajaysurya1221/actseal#readme-ov-file.
Actual browser viewport1366x900,DPR1; image width838CSSpx. Scroll places the
hero top54px below the native GitHub sticky README tab bar; no page content
or image was edited. The PyPI0.1.0badge accurately predates1.0 publication.

Screenshot: [readme-first-screen-277d729-final.jpg](readme-first-screen-277d729-final.jpg)
SHA256:7f8860d88c570b69a117ee1eaef16e4093280651bf551f6c4e8c6316230fa794.
The earlier readme-first-screen-277d729.jpg capture clips the hero under the
sticky bar; it is preserved as a framing attempt and was NOT given to the
reviewer. This final capture is unedited and the only reviewer input.

## Blind prompt (verbatim)

You are a fresh comprehension reviewer. View ONLY this screenshot using view_image: /Users/ajay/Developer/not-yet-named/plan/v1/reports/readme-first-screen-277d729-final.jpg . Do not read any other files, repo context, messages, or web pages. After a quick first-screen glance (about ten seconds), respond in exactly two sentences: what does the project do, who is it for, and what does it guarantee or not guarantee? Do not edit files.

## Reviewer answer (verbatim)

Actseal helps developers test model-chosen application actions by freezing a policy, checking recorded decisions against risk and coverage bounds and fault rules, and sealing evidence for offline replay. It can recompute the verdict without a model call, but replay cannot authenticate responses, prove inference occurred, or establish label truth.

Fresh subagent:/root/readme_first_screen_final_blind, fork_turns=none. No
project history or acceptance wording was supplied. This is the approved
qualitative first-glance test, not a measured human usability/time study.

## Codex REVIEW

Verdict: ACCEPT for first-screen comprehension. The answer identifies the
developer audience, frozen policy, risk/coverage and fault checks, evidence
and provider-free verdict recomputation. It explicitly states all three
limits: response authenticity, inference occurrence and label truth. It does
not claim application containment, universally correct actions or calibration.
This matches docs/stability.md and docs/threat-model.md. No visual iteration
is required by this gate. Release publication and genuine recording remain
separate. Task08F changes only the below-fold release-notes link label, not
the captured opening/source images; recheck that invariant at integration.

## Actual responsive selection after capture

On the same public README, allthree picture images loaded successfully:

|Viewport CSSpx|Image width CSSpx|Selected family|Natural SVG width|
|---|---|---|---|
|320|254|hero/how-it-works/architecture mobile-light|720|
|1200|758|hero/how-it-works/architecture mobile-light|720|
|1280|838|hero/how-it-works/architecture desktop-light|1600|
|1366|838|desktop-light (capture)|1600|

Measurements use read-only DOM geometry/currentSrc after UI viewport changes;
initial asynchronous not-yet-loaded observations were not treated as passes.
The temporary viewport override was reset after verification. Dark variants
were independently pixel-reviewed in13-readability.md; no browser dark-mode
selection claim is added by this light-theme observation.
