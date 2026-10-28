# LangGraph #9343 / #9352: scoped repair exploration

AI-assisted work supporting the existing contributor. PR #9352 remains closed by the assignment bot and unmerged; #9343 has no assignee at the checked time. No new upstream PR is created, and no complete fix or adoption is claimed.

## Actual increment

`scoped-repair.patch` builds on the existing load-only model_validate approach. For a model with a custom initializer, simple string validation aliases are re-keyed on load before validation so that `super().__init__` receives accepted keys. Models that already validate by name or disable alias validation retain their original input. Remapping is simultaneous and ambiguous target keys retain the old fallback path. The stored checkpoint format and JSON view are unchanged; no model configuration is mutated, and the custom initializer still runs.

The five direct regression cases from round 1 now pass (5/5). The new suite checks defaulted and required aliases with custom initialization, extra fields, name-only validation configuration, and AIMessage/ToolMessage/HumanMessage controls. **Seven pass and one fails**: a custom-initialized aliased model nested inside a normal model still silently loses its value. That failure remains an ordinary failing assertion, not an xfail or skipped test. A first prototype also broke name-only validation; the retained v1 log documents that failure, and the configuration guard repairs it in v2.

This is a scoped repair prototype, **not ready for a general fix PR**. It does not recursively rewrite arbitrary nested annotations, AliasPath/AliasChoices for custom initializers, discriminated unions or arbitrary constructor transformations. A general solution needs an agreed reconstruction/constructor contract. Do not adopt this patch as complete checkpoint safety.

## Verification

- Upstream source: `eb8ec111b3e9d3108af5d7bdcac51e3e913637a0`, confirmed current at execution.
- Python 3.11.12 / Pydantic 2.12.5 / ormsgpack 1.13.0.
- Original five-case suite on the prototype: **5 passed**.
- New boundary suite: **7 passed, 1 failed** (known nested corruption).
- Official checkpoint tests excluding `test_redis_cache.py`: **252 passed**. Redis service was unavailable; the separate full-suite attempt was stopped while its service-dependent tests waited/skipped. No Redis pass is claimed.
- Ruff check and formatting pass for touched source/test; `git diff --check` passes. Full upstream make lint/ty checks have not run; no PR readiness is claimed.

Raw output, initial failures, dependency logs and patch are retained in `evidence/`. Reproduce by checking out the upstream commit, installing checkpoint editable plus its test dependencies, applying the patch at the repository root, and running:

```sh
python -m pytest test_alias_repair.py -q
python -m pytest /path/to/langgraph/libs/checkpoint/tests --ignore=/path/to/langgraph/libs/checkpoint/tests/test_redis_cache.py -q
```

The first command must expose the nested failure. The patch derives from upstream MIT code and the existing contributor's approach; it is not claimed as a new general solution. Human-maintainer assignment/acceptance and external use remain unestablished.
