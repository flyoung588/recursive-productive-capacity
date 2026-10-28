# Round 3: constructor-preserving checkpoint restoration boundary

AI-assisted counterexample execution supporting LangGraph #9343 / existing PR #9352. The issue remained unassigned and the PR remained bot-closed/unmerged at `b580e399e209bc3b7d6128c238acdb83fe120964`. After the initial check, the original author supplied concrete scope feedback; see the responsive verification below. No competing PR or general fix is proposed.

## What the real executions establish

Eight cases run in fresh processes against each of three actual serializer source variants: current upstream `eb8ec111b3e9d3108af5d7bdcac51e3e913637a0`, that source with PR #9352's serializer hunk, and that source with our round-2 scoped prototype. Each run uses actual JsonPlusSerializer and Pydantic 2.12.5. No constructor is bypassed or field overwritten by the probe; it observes the serializer's existing behavior.

| Counterexample | Upstream | PR serializer hunk | Round-2 scoped prototype |
|---|---|---|---|
| Direct custom-init/defaulted alias | 42 → 1 | 42 → 1 | 42 preserved |
| Nested custom-init alias | 42 → 1 | 42 → 1 | 42 → 1 |
| Discriminated Union branch with custom-init alias | 42 → 1 | 42 → 1 | 42 → 1 |
| Union text branch control | preserved | preserved | preserved |
| Custom init + AliasChoices | 42 → 1 | 42 → 1 | 42 → 1 |
| Custom init + AliasPath | 42 → 1 | 42 → 1 | 42 → 1 |
| Constructor doubles input: original input 21 stores 42 | 42 → 84 | 42 → 84 | 42 → 84 |
| Constructor raises on stored value 42 | equality preserved by existing fallback; zero successful initializations | same | same |

The last row is the reason equality-only tests are insufficient. The probe records actual initialization attempts/successes for the two instrumented constructor cases. For other classes the uninstrumented counters are null, not measured zeros. Existing serializer code catches the initializer's exception and calls model_construct, so successful value equality there does **not** establish constructor-preserving reconstruction. The probe neither adds nor recommends that fallback.

## Scope decision

Checkpoint payloads contain post-initialization field values. Running an arbitrary custom initializer again is not generally equivalent to reconstructing those values: it can transform input again, require unavailable original inputs, or raise. Recursive key rewriting alone cannot establish a generic constructor-preserving contract. These counterexamples do not show that all custom initializers are unsupported or that a narrower fix is impossible; they show why our prototype is not a transparent general repair.

Stop extending that prototype until maintainers choose an explicit scope/reconstruction contract. The ordinary no-custom-init alias improvement can be reviewed separately by the existing author. Do not merge our round-2 patch as a complete fix or claim nested custom construction is repaired. We have not proven a safe general solution and have not submitted a fix PR under the assignment gate.

## Reproduce

Use an isolated, unchanged LangGraph checkout at the upstream commit above and Python 3.11 with the checkpoint package installed editable, Pydantic 2.12.5 and ormsgpack 1.13.0. The two candidate patches are included unchanged for comparison; they are experimental prior work, not new fixes.

```sh
python run_matrix.py --source /path/to/langgraph --python /path/to/venv/bin/python --pr-patch pr9352.patch --scoped-patch round2-scoped.patch
```

The runner refuses an already-modified serializer, uses separate processes, and restores the original source in a finally block. Raw values, constructor traces, warnings and summary are in `evidence/`. Its assertions confirm observed counterexamples, **not** repair success. It performs 24 case observations (8 × 3), not a model evaluation.

Current unchanged-source checkpoint regression excludes unavailable Redis service tests: 252 passed. That is a baseline check, not regression validation of a new fix. Ruff checks pass for the probe files. No external adoption/shared testing/assignment is established.

## Responsive verification after the author's feedback

Original author JohnnyWilson16 [responded directly](https://github.com/langchain-ai/langgraph/pull/9352#issuecomment-6464651192), agreed that ad-hoc key rewriting should not be merged as a general solution, and explicitly preferred the ordinary-model alias repair scope of the existing PR. This is verified two-way technical discussion. It is not evidence that the author ran our code or adopted tests.

In response, `test_author_scope.py` verifies eight cases within that stated scope: ordinary defaulted alias, nested list of ordinary models, discriminated Union number/text branches, AliasChoices, AliasPath, and two simple forwarding-custom-init controls explicitly configured with populate_by_name=True. On unchanged upstream: **5 failed / 3 passed**. With only the author's original serializer hunk: **8 passed**. The same hunk also passes **252 official checkpoint tests**, excluding the unavailable Redis service tests. No scoped re-key prototype is included in that verification. Pytest-asyncio emitted a fixture-scope deprecation warning, retained in raw outputs.

These results support the existing author's narrowed fix. The populate_by_name controls do not imply that configuration repairs arbitrary transforming or rejecting constructors; the counterexamples above remain separate. The ordinary-scope test file can be adapted into the existing PR after its author/maintainers choose to do so. We have not opened a competing PR or claimed upstream adoption.
