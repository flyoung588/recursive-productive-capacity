# Direct assistance for OpenHands PR #19014

Reviewed PR head `fce5e1f78bcdc6628de9bad3947ea80735a795b4` on 2026-10-28.
The PR remains open. No author response to the earlier reference-harness comment
was present when checked. Its changed-file list contains no test files.

## New reproducible lifecycle defect

1. A completed turn persisted HEAD A in `openhands:git-snapshot:<conversationId>`.
2. Someone commits externally, producing HEAD B.
3. Reopen the conversation while its agent state is STOPPED.
4. The idle effect immediately writes B as the baseline, despite no observed run.
5. Transition to RUNNING; comparison sees B versus B and reports `detected: false`.

This misses even a HEAD change; it is separate from the already-reported
same-count dirty-file fingerprint limitation.

## Actual test execution

`use-git-resume-drift.test.tsx` imports the **actual PR hook**, rendered by React
Testing Library in the repository's Vitest jsdom project. Only the Git service
and active-conversation query are mocked. No helper algorithm is copied.

The failing test represents a persisted baseline, mounting STOPPED, then RUNNING.
Controls verify unchanged HEAD does not warn and an observed RUNNING→STOPPED turn
still refreshes its baseline. Together with the existing use-agent-state tests:

* Unmodified PR hook: 1 failed, 4 passed. Failure: expected detected=true, got false.
* With `idle-baseline.patch`: 5 passed.
* Original standalone reference detector: 16/16 passed again (separate suite).
* Added test file: Prettier formatted; targeted ESLint passed (exit 0).

Raw before/after outputs and the standalone-suite output are included. Tests used
Node 24.19.0 and locked Vitest 5.0.0. Dependencies were installed with npm ci
--ignore-scripts; the host npm was 10.9.2 rather than the repo's 11.12.1 pin.
No lockfile changes, resolver updates, or full repository validation are claimed.

## Reproduce in the PR checkout

Start with the PR head above and its locked dependencies installed. Copy this
folder's test file to `src/hooks/use-git-resume-drift.test.tsx`. Run:

```sh
node node_modules/vitest/vitest.mjs run src/hooks/use-git-resume-drift.test.tsx src/hooks/use-agent-state.test.tsx
```

The unmodified hook should produce the failure in hook-before.txt. Then apply
`git apply /absolute/path/to/idle-baseline.patch` and repeat the same command.
This produced hook-after.txt.

The patch records which conversation was observed RUNNING and only refreshes an
idle baseline after such an observed run. It is a narrow author-facing fix for
this regression, not a complete implementation of issue #18981.

## Comparison with the 16 Git reference cases

The reference suite covers branch/detached HEAD, same-branch commits,
staged/unstaged/untracked edits, unchanged/ignored files, non-Git rejection,
read-only snapshot, staged and unstaged dirty-to-dirty edits, untracked edits
without filename changes, linked-worktree working-file isolation, and unborn
rejection. The PR currently adds no tests. Its HEAD/count representation cannot
cover branch-only changes at the same SHA or changes that preserve path count.
The new hook test adds a separate lifecycle regression not exercised by that
framework-independent Git suite.

## Boundaries

This is a frontend hook behavioral test with service mocks. It does not run a
real Agent Server, SDK lifecycle, Git service, browser UI, or model. There is no
server-side persistence/context integration or actual shared test execution with
the author. Existing count-based detection, branch identity, transient-null
baseline clearing, and asynchronous baseline races remain outside this narrow
patch. Server-owned capture/context injection and public typed interfaces are
still needed for the full acceptance criteria. No competing PR was created.
