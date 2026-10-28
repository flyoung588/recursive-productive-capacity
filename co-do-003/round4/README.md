# Round 4: ready-to-cherry-pick native scope tests for #9352

Tests-only commit: `a61165f2f5bb26885fa4fc20e05bb2e5c603e73e` on flyoung588/langgraph branch `co-do-9343-author-scope-tests`.

Its parent is exactly original-author PR head `b580e399e209bc3b7d6128c238acdb83fe120964`. It adds one native file, `libs/checkpoint/tests/test_jsonplus_alias_scope.py` (80 lines), with eight named cases. It changes no production code, dependency, license or workflow. The scope follows JohnnyWilson16's explicit feedback: ordinary-model alias repair plus simple forwarding-init controls with populate_by_name=True, not arbitrary constructor reconstruction.

```sh
git fetch https://github.com/flyoung588/langgraph.git co-do-9343-author-scope-tests
git cherry-pick a61165f2f5bb26885fa4fc20e05bb2e5c603e73e
cd libs/checkpoint
uv run pytest tests/test_jsonplus_alias_scope.py
```

An email-format patch is also included as `native-tests.patch` for `git am`.

## Actual checks

- Native eight-case suite: 8 passed on each of Pydantic 2.11.10, 2.12.5 and 2.14.1 / Python 3.11.12. Versions below 2.11 and other Python versions were not checked.
- Removing only the original author's serializer change: 5 failed / 3 passing controls. Production source was restored afterward.
- Full native checkpoint suite on the exact author HEAD plus this test: 240 passed, excluding unavailable Redis service tests. This differs from the previous 252 count because that earlier run used newer upstream main, not this PR's older base.
- New test file passes upstream Ruff check/format and ty without diagnostics. No full make lint or whole-repository CI pass is claimed. Pytest-asyncio's fixture-scope deprecation warning is preserved in raw output.

The AliasChoices/AliasPath inputs use model_validate rather than keyword constructors so the upstream type checker can recognize them without incorrect extra-key diagnostics. Existing pytest parametrization and module-level models are retained, with descriptive case IDs.

## Collaboration state

At the latest check #9352 remains closed, unmerged and unassigned, with unchanged author HEAD. The author has already provided scope feedback, but has not requested another change or confirmed running/absorbing our tests. This commit is offered for the existing author to cherry-pick; no competing upstream PR is opened and no upstream-assignment requirement is bypassed. Prior broad constructor experiments are not included. No new intellectual-property license terms are selected.

Raw validation output and live snapshots are in `evidence/`. Code delivery is not adoption; parent/HEAD agreement is not evidence of an external developer running the tests.
