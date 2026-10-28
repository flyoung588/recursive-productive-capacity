# Co-Do #003: additional regression evidence for LangGraph #9343

AI-assisted experiment, not an upstream fix or accepted contribution. This supports the existing contributor's PR #9352; no competing PR is opened.

## Finding

On actual langgraph-checkpoint 4.3.1 source at `eb8ec111b3e9d3108af5d7bdcac51e3e913637a0`, a defaulted aliased field silently loses its value on round trip. Applying only the serializer hunk from PR #9352 (`b580e399e209bc3b7d6128c238acdb83fe120964`) fixes ordinary aliases, AliasChoices and AliasPath in this matrix, but does not fix a model that overrides `__init__` and forwards data to `super().__init__(**data)`.

The distinguishing combination is **custom initialization plus defaulted alias**, rather than custom initialization alone. For this case, the restored value remains 1 instead of 42. A required aliased field with the same custom initialization is a passing control because the existing fallback constructs it.

| Five real serializer preservation assertions | Unmodified source | PR serializer hunk |
|---|---:|---:|
| Passed | 1 | 4 |
| Failed | 4 | 1 |

Confirmed the same four-failure baseline and one-failure candidate matrix on Pydantic 2.12.5 (the issue version), with raw outputs retained.

Initial matrix: Python 3.11.12, Pydantic 2.14.1, ormsgpack 1.13.0. Raw results and exact environment are in `evidence/`. Failures are deliberate bug-reproduction evidence; this is not a passing fix suite. No model, API key or remote service is used by the experiment. This is serializer integration, not an end-to-end graph/resume test. No general reconstruction fix is proposed because arbitrary custom constructors require a deliberate compatibility contract.

## Reproduce

Clone LangGraph and select the source revision above. In an isolated Python 3.11 environment:

```sh
python -m pip install -e /path/to/langgraph/libs/checkpoint pydantic==2.14.1 ormsgpack==1.13.0 pytest==9.2.0
python -m pytest alias_probe.py -q
```

Expect four failures and one pass on the unmodified source. Apply `evidence/applied-pr9352.patch` at the LangGraph root and rerun; expect one failure and four passes. `python alias_probe.py` prints sample values. The patch is an experimental application of the existing contributor's serializer change; it is not authored or claimed as a new fix here. Upstream LangGraph is MIT licensed; this branch makes no additional licensing or acceptance claim.

## Actual reuse

Track B's unchanged `workspace_drift.snapshot/compare` was imported directly to fingerprint the isolated LangGraph checkout before and after applying the candidate serializer hunk. `evidence/reuse-drift.json` records `unstaged_changes_changed`, with unchanged branch/HEAD/staged/untracked fingerprints. This avoided writing another repository-state comparator. It is internal cross-task reuse of a Git utility on a second project's checkout, not integration into or adoption by LangGraph.

## Discovery limits

The prior top-20 list was not located in the supplied public branches or targeted local references. Live searches returned 50 candidate rows across MCP Python SDK, Google ADK, LangGraph and Deep Agents; 11 issues received full issue/comment inspection. Search rows are not verified opportunities. `evidence/queue.json` records concrete exclusions, existing owners/PRs and the selected additional regression. No MCP contribution was posted because its policy asks autonomous agents not to submit without a human who hit the problem and reviewed the output. No maintainer response, collaboration agreement, acceptance or merge is claimed.
