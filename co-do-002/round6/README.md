# Round 6: actual revision hashes lost in the updated banner

PR #19014 target: `f307fd007f04bcbbbdc131a4cf740a7013ee1431`.
Local tested code: `5a04a3dd090e3e2431ef05083b4476104b39583a`.
This is a new rendering regression in the updated i18n implementation, not a
refresh of the unchanged lifecycle proposal. No lifecycle code is changed.

## Reproduced behavior

`GIT_DRIFT$PREV_HEAD` and `$NOW_HEAD` contain `prev {hash}` / `now {hash}`.
Default i18next interpolation needs `{{hash}}`. The actual banner therefore
renders literal `{hash}` rather than the supplied previous/current revisions.

The regression renders the actual component through a real I18nextProvider,
using the actual repository translation JSON. It explicitly un-mocks the shared
key-returning react-i18next stub; interpolation is not mocked or reimplemented.
Before: **1 test fails**, and its DOM output shows both literal placeholders.
After: **3/3 pass**, including the existing adjacent agent-state tests.

## Minimal patch

`hash-interpolation.patch` changes three files:

* Corrects the 32 existing hash placeholders (two keys × 16 locales).
* Uses generated I18nKey constants for the five current calls, fixing the new
  `no-restricted-syntax` CI errors without new keys or allowlist edits.
* Adds the real rendering regression test.

Native `npm run lint`: before exit 1, **5 errors / 403 warnings**; after exit 0,
typecheck passes, **0 errors / 403 unchanged warnings**, Prettier passes.
Patch was directly applied to exact target-head file contents in temporary Git;
all three resulting files byte-match the tested code commit. Raw outputs included.

```sh
git apply /absolute/path/to/hash-interpolation.patch
npm run lint
node node_modules/vitest/vitest.mjs run src/components/features/chat/git-drift-banner.test.tsx src/hooks/use-agent-state.test.tsx
```

Existing locked dependencies were reused; package/lockfile contents match.
Runtime Node 24.19.0; npm 10.9.2 differs from repository pin 11.12.1. No resolution
or lockfile changes occurred.

## Locale boundary changed upstream

The current head has filled the two earlier WAKE keys and five GIT_DRIFT keys
with English copied across all 16 locales, and added those keys to the checker
allowlist. Thus its configured locale checker now passes before and after this
patch. That does not establish actual language translation completeness.
This patch changes no allowlist, checker, language wording, or unrelated key.

## External evidence and limits

External reviewer Yut0Miura acknowledged the earlier dirty-to-dirty/worktree
findings and SDK/typed-contract boundary in issue comment 6471380332. Their
GitHub author_association is NONE. This is actual technical feedback, not an
implementation request, evidence of executing our tests, adoption attribution,
or merge. No PR reviews are present. The latest lifecycle source lacks our
proposed guard, and the PR file list contains no drift tests.

No competing PR. No full suite/build/E2E, real browser, Agent Server, Git service,
or model test. No upstream CI rerun or acceptance claim. Remaining lifecycle,
count-based and cross-worktree persistence requirements are unchanged.
