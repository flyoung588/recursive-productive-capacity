# Round 5: minimal patch for current PR #19014 head

Target/current checked upstream head:
`c17b21be14a282ee058a144d0dffec31d47369e2` (open).
Formatting is now clean and source-equivalent to the earlier formatting repair;
attribution is not established by a reply, request, review, or commit reference.
No author response or external run/adoption of our tests is evidenced.

## Remaining reproduction and minimum patch

Native `npm run lint` on the target: **5 errors / 403 warnings**, exit 1.
All five errors are banner literal-copy localization; no formatting fixes are
needed. The latest-head STOPPED-reopening hook regression also remains:
**1 failed / 4 passed**, including adjacent use-agent-state tests.

The combined patch changes only four files:

* Banner localization with existing dismiss key and four new keys/all 16 locales.
* Four new translation-key blocks, without modifying unrelated translations.
* A nine-line lifecycle guard that refreshes an idle baseline only after an
  observed running turn for the same conversation.
* The actual React hook regression and its unchanged/end-of-turn controls.

Split local tested commits:
`b92f0d16b7261758c1218827c9f7c8dbcba6cd6f` (localization), then
`b4281adc7b06a066f5d23c85084ed52b4696fe83` (lifecycle/test).

After patch: **native `npm run lint` exits 0**, typecheck passes, ESLint has
**0 errors / 403 unchanged warnings**, Prettier passes. Targeted hook/state tests
pass **5/5**. No warning/rule suppression. Combined patch size is 11,354 bytes.

## Apply

Use locked dependencies and a supported Node version (tested Node 24.19.0).
Apply the combined patch once, or the two numbered patches in order, not both:

```sh
git apply /absolute/path/to/combined.patch
npm run lint
node node_modules/vitest/vitest.mjs run src/hooks/use-git-resume-drift.test.tsx src/hooks/use-agent-state.test.tsx
```

The combined patch was applied in a temporary Git repository containing exact
upstream-head versions of the affected files. All four resulting files
byte-match the tested local code commit; raw verification is included.
No previous formatting or restored-translation-key patch should be reapplied.

## Checks that remain incomplete or failed

The full translation-completeness script still fails on the same two existing
WAKE_ALL_AGENTS_NONE/SUCCESS keys (13 missing locales each). Baseline and patched
checker results are identical. The four added keys have no missing/extra/copied-
English checker errors. Translation wording lacks independent native review.
No unrelated-key changes or checker weakening were made.

Hook tests import actual upstream code with Git service/query mocks; they are
not real Agent Server, Git-service, model, browser, or full acceptance tests.
No full suite/build/E2E or upstream CI rerun claimed. Count-based/branch-only/
asynchronous limitations remain. Current upstream Ubuntu check is failed;
Windows succeeded. No competing PR, acceptance, attribution or shared execution
claimed. npm 10.9.2 differs from repository pin 11.12.1; lockfile unchanged.

All raw outputs and exact commits are preserved. The existing author comment
is refreshed to this head instead of adding another duplicate comment.
