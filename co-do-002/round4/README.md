# Round 4: remaining lint failures and rebased lifecycle regression

Target: OpenHands/OpenHands PR #19014, exact head
`2af6564a24b2d2988c2103d119dc03822ccb58e3`, open at check.

Both translation keys from the prior report are restored with their existing
16-language values. That outcome matches the earlier repair; no reply or commit
attribution establishes that our contribution caused it. Do not reapply round 3.
No author request, prior hook-patch absorption, or shared test execution was
present in the fetched PR comments/reviews and current source.

## Actual remaining CI reproduction

Current Ubuntu job 122718351329 (run 40659393519) fails lint. Local
`npm run lint` reproduces **44 errors, 403 warnings** (exit 1):

* 39 formatting errors, fixed mechanically with targeted `eslint --fix`.
* Five manual `i18next/no-literal-string` errors in the new banner: title,
  previous/current revision labels, acknowledge label, and dismiss aria-label.

The patches keep these categories separate:

1. `01-format.patch`: formatter-only changes in the three PR source files.
   Tested local commit `19b7e54083a4631a91e19d453ceda4460a1c89be`.
2. `02-localize-banner.patch`: routes copy through `useTranslation`/`I18nKey`,
   reuses the existing dismiss key, and adds four banner keys with 16 locales.
   Commit `71db55a791b5584cd81ab32dcaa6062802b98ff9`.
3. `03-idle-baseline-and-test.patch`: rebased narrow lifecycle guard and actual
   React hook test. Commit `ea823bea048ba4368f26ca444dcdefa2ff59a66d`.

With all three, **full `npm run lint` passes (exit 0)**: typecheck passes,
ESLint reports 0 errors/403 existing warnings, and Prettier check passes.
Warnings were not suppressed. Raw before/autofix/after outputs are preserved.

## Actual lifecycle regression on this head

The same STOPPED-reopening defect remains: an idle effect overwrites the durable
baseline before RUNNING compares it. The existing regression was rerun against
the exact new-head hook source: **1 failed, 4 passed** with adjacent state tests.
After the narrow guard: **5/5 pass**. These import the real hook and use React
Testing Library, with only Git-service and active-query mocks. They are not a
real Agent Server/Git or browser integration test.

## Apply and verify

Start at the target head with locked dependencies installed and a supported Node
version (used here: Node 24.19.0). Either apply `combined.patch` once, or apply
the three numbered patches in order; do not do both.

```sh
git apply /absolute/path/to/combined.patch
npm run lint
node node_modules/vitest/vitest.mjs run src/hooks/use-git-resume-drift.test.tsx src/hooks/use-agent-state.test.tsx
```

Patch verification applied the combined patch to exact PR-head file contents in
a temporary Git repository and byte-compared all five resulting files against
the tested code commit. All matched; see patch-apply-round4.txt.

## Locale-check limitation retained

The full translation-completeness script still fails on two pre-existing keys:
`CONVERSATION_PANEL$WAKE_ALL_AGENTS_NONE` and
`CONVERSATION_PANEL$WAKE_ALL_AGENTS_SUCCESS`, each missing 13 locales. Running
its exported checker on the original head and our patched data returns exactly
the same failures. Checking only the four added keys returns no missing/extra/
English-copied-value errors. This patch does not modify the unrelated keys or
weaken the checker. Translation wording has no independent native-language review.

## Limits

No complete test suite, build, E2E, model calls, server-owned snapshot/context
integration, upstream CI rerun, acceptance or merge claim. The previous remaining
count-based, branch-only and asynchronous limitations are unchanged. Local npm
is 10.9.2 rather than the repository pin 11.12.1; lockfiles were not modified.
No competing PR was created. The public artifact contains patches and raw local
results; current upstream CI remains failed until its author changes/reruns it.
