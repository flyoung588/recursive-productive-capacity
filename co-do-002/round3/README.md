# Round 3: exact-head CI repair for OpenHands PR #19014

Live recheck: PR open, HEAD still `fce5e1f78bcdc6628de9bad3947ea80735a795b4`.
No author response, external shared test, or absorption of our prior hook patch
was present in the fetched issue/PR threads or unchanged head. This is evidence
of unchanged code/thread state, not a conclusion about the author's intentions.

## New independently actionable CI defect

Ubuntu job 122703540443 in run 40654913887 fails during `npm run typecheck`:

* `conversation-card-context-menu.tsx:186` references `CONVERSATION$NEW_IN_SANDBOX`.
* `conversation-name-context-menu.tsx:182` references `CONVERSATION$SHARE_WITH_ORG_USERS`.

The PR removes both keys from translation.json while leaving these consumers.
`restore-required-translations.patch` restores only their existing 16-language
blocks verbatim from PR base `6354932e87f99e1583f482f2cea49d6d573443e0`.
It adds 36 lines to one file, without inventing translations or deleting usages.

Actual local validation:

1. Before: `npm run make-i18n` then `npm run typecheck` reproduces both TS2339 errors.
2. After: regenerate and typecheck pass (exit 0).
3. `node scripts/check-translation-completeness.cjs` passes (exit 0).
4. Existing real-hook regression and adjacent state tests: original PR hook still
   fails 1/5; prior minimal lifecycle patch still applies and passes 5/5.

Exact local tested code commits: original PR head above →
`fbacc823e8bfe914ac169c0d503ef4a299ee8da8` (prior hook patch/test) →
`58ef40c37754af56b5d9fca81f698d13648c22a5` (translation restoration).
Translation patch is independent of the hook patch and applies to original PR.
Raw before/after test outputs and captured CI check summary accompany this file.

## Direct application to PR head

```sh
git apply /absolute/path/to/restore-required-translations.patch
npm run make-i18n
npm run typecheck
node scripts/check-translation-completeness.cjs
```

The previous hook patch/test remains in ../round2 with its exact commands. No
new hook behavior is claimed in round 3. The tests use the actual React hook,
with Git service/query mocked, not a real Agent Server or browser integration.

Validation runtime: Node 24.19.0; installed lockfile dependencies unchanged.
Host npm remains 10.9.2 rather than repository pin 11.12.1. No complete lint,
build, E2E, upstream CI rerun, merge readiness or maintainer adoption is claimed.
Current recorded upstream CI still has Ubuntu failure; our local fix does not
change its status. No competing PR created.
