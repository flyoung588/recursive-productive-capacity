# Offline real-framework description-composition experiment

**Round 2 update:** [Real localhost HTTP/JSON-RPC/SSE experiment](HTTP_INTEROP.md) now replaces the transport double for a separate set of 16 runs. The round 1 record below remains historical; real-model efficacy remains untested.

This is an AI-assisted, independently maintained experimental companion to Microsoft Agent Framework #9561. It does not modify upstream code or propose a permanent API. Maintainer guidance remains **design review only**; no upstream PR or acceptance is claimed.

## What actually runs

Upstream source: `microsoft/agent-framework` commit `4a272d2b8e96242a1e00783e833d42922a618d23` (retrieved 2026-10-28). Editable installations of the actual core, A2A and orchestrations packages are used. `a2a-sdk==1.3.0` provides real protobuf `AgentCard`/`AgentSkill` objects. The existing helper from `9f4ef5c0580cba18c7c886312e1f9dd42e2fc66c` is reused here (formatting only).

The chain is actual `GroupChatBuilder` → `AgentBasedGroupChatOrchestrator` selection prompt → deterministic `Agent` test double → actual `A2AAgent` → recording transport double → SDK completed task/artifact → group chat. The selector reads the framework-generated participant-description prompt; it does not receive cards or fixture answers. A transport invocation and its result reaching the manager are asserted for each delegated case. No model or HTTP server is involved.

Baseline and treatment share tasks, two candidates, selector algorithm and transport. Only `description=card.description` versus `description=selection_description(card)` changes. The seven cases cover similar descriptions/different skills, multiple skills, specialist skill, overlapping skills, no match, misleading advertised skill, and incomplete skill description. Sample rows retain generated prompts, expected eligible participants, actual choice, results, lengths, elapsed time and invocation counts.

## Results

| Deterministic fixture diagnostic | Baseline | Treatment |
|---|---:|---:|
| Samples | 7 | 7 |
| Expected decision incl. correct abstention | 2/7 | 5/7 |
| Wrong delegation | 0/7 | 1/7 |
| Transport calls | 0 | 5 |
| Total candidate description characters | 50 | 162–206 |
| Median local workflow time (ms, one run) | 0.376 | 1.391 |

These are **test-double diagnostics, not model accuracy estimates**. Generic descriptions contain no keyword so baseline abstains on every case. Treatment exposes sufficient text for four positive cases, but the misleading claim induces an incorrect delegation and the incomplete specialist description causes abstention. This validates information propagation and demonstrates that card text is not verified competence. Repeated deterministic samples add no statistical evidence; timings are single-run local overhead, not network/model latency.

`run.log` records all 14 executions. `tests.log`: 13/13 checks passed (10 existing helper tests + 3 integration-result/SDK checks). `upstream-tests.log`: 17/17 upstream A2A group-chat regression tests passed, with a pytest timeout-plugin configuration warning. `lint.log`: E/F checks pass after Ruff formatting.

No model was invoked, paid credentials were not used, and no already-authorized no-new-cost model endpoint was established. Real selector-model efficacy, token usage/cost, independent agent task quality, prompt-injection resistance, network behavior and real multi-skill server interoperability remain **UNTESTED**. Model token/cost fields are null, not measured zeros. Model call count is zero. No `skill_id` metadata is sent. Explicit application descriptions, including the empty string, are preserved by the actual constructor. Empty descriptions may still be represented by the orchestration's existing placeholder behavior.

## Reproduce

Use Python 3.11, a fresh environment, and a checkout of the upstream commit above:

```sh
python -m venv .venv
.venv/bin/pip install -e /path/to/agent-framework/python/packages/core -e /path/to/agent-framework/python/packages/a2a -e /path/to/agent-framework/python/packages/orchestrations a2a-sdk==1.3.0 pytest pytest-asyncio ruff
cd co-do-001/framework_experiment
/path/to/.venv/bin/python run_experiment.py
/path/to/.venv/bin/python -m pytest -v test_integration.py ../test_capability_preview.py
/path/to/.venv/bin/ruff check --select E,F run_experiment.py test_integration.py capability_preview.py
/path/to/.venv/bin/python -m pytest --confcutdir=/path/to/agent-framework/python/packages/a2a/tests /path/to/agent-framework/python/packages/a2a/tests/test_a2a_group_chat.py
```

Exact installed versions are in `environment.txt`; editable source commit is pinned above. Execution does not require API keys. The transport is a test double deliberately, so `.invalid` URLs are never contacted. Follow-up should evaluate real selector behavior and a real server using an agreed protocol contract; this experiment justifies no remote-skill API. Upstream source is MIT licensed; no upstream source is vendored in this experiment. The surrounding owned repository has no root license at this revision, so upstream adoption would need explicit licensing resolution as well as maintainer agreement.
