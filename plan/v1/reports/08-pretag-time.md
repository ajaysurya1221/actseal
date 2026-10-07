# REPORT 08F3 (capture-time correction to the 08F2 receipts)

Status: DONE for the owned scope. Two timestamp strings changed; nothing
else. REPORT 08F and REPORT 08F2 are preserved unchanged. No new behaviour,
no full release ACCEPT, tag, artifact, PyPI receipt, recording or live Jev
evidence is claimed.

Executor: the same Claude Code documentation session, model
`claude-fable-5-1`, effort high, normal permissions, existing account and
billing, no subagent. Branch `claude/v1-08-pretag`, continued from
`85a703f4d0ef4edb401b907d204bcf90eb1033e5`. No merge, push, tag, network,
key or provider access; no product, test, asset, schema or packaging edit.
No tool operation was denied.

## Correction

Codex's 08F2 dispatch gave the final first-screen screenshot capture time
as "09:33 UTC" (rounded). The authoritative root receipt
`plan/v1/reports/readme-ten-second-final.md` records the actual capture
mtime `2026-10-07T09:32:34.498785+00:00`. Exactly the two occurrences of
the rounded value were changed to `09:32:34 UTC`:

- `plan/v1/RELEASE_NOTES.md`, "Blind ten-second README test (final)" row:
  "captured 7 October 2026 09:33 UTC" is now "captured 7 October 2026
  09:32:34 UTC".
- `docs/decisions/0020-reproducible-visual-assets.md`, final first-screen
  bullet: "captured 09:33 UTC" is now "captured 09:32:34 UTC".

`grep -rn "09:33"` over both files returns nothing after the edit. The
screenshot path, viewport, device pixel ratio, image width, commit
`277d729`, the reviewer's quoted sentences and every other statement are
unchanged. The implementation source fingerprint `8f316f67…98ed3` is
untouched.

## Commit

| Commit | Content |
| --- | --- |
| `93bdc27e55fd19903d31d70e6b429c25205f4af7` | release notes and ADR 0020, 2 insertions, 2 deletions |
| (this report) | `plan/v1/reports/08-pretag-time.md` only |

## Commands and exit codes

Separate, unwrapped commands on the corrected content before the commit.

| Command | Result | Exit |
| --- | --- | --- |
| `uv run --frozen pytest tests/docs` | 110 passed in 1.07 s | 0 |
| `git diff --check` | no output | 0 |

## Pending

Publication remains pending: Codex's review and integration of the pre-tag
documentation, the final candidate gate on the final clean tree, the tag,
human `pypi` approval, the Task 20/21 receipts and the post-PyPI recording.

## Spend

Unknown; not measured.
