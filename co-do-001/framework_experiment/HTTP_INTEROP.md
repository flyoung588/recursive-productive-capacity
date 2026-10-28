# Round 2: actual local HTTP A2A interoperability

This AI-assisted follow-up replaces the prior transport double with **two real Uvicorn loopback servers**, SDK 1.3.0 `DefaultRequestHandler`/`InMemoryTaskStore`/JSON-RPC and card-discovery routes, and actual framework `A2AAgent` network clients. No upstream source changes. Framework source remains pinned to `4a272d2b8e96242a1e00783e833d42922a618d23`.

## Executed scope

`http_interop.py` serves two independently addressed multi-skill cards, fetches them via `A2ACardResolver` over HTTP, composes descriptions with the existing helper and runs the real GroupChatBuilder. Alpha advertises translation, summarization, a deliberately false surgery claim, and semantically incomplete generic analysis. Beta advertises calculation, translation and spectroscopy. Required card fields are populated, including protocol version 1.0 and skill tags. The servers are deterministic application executors with bounded canned sample tasks; they are not general translation, scientific-analysis or medical services.

The selector remains the explicitly marked keyword fixture reused from round 1. It consumes the real framework selection prompt; it is not a model. Both arms use identical task inputs, candidates, selector algorithm, HTTP server implementations and SDK configuration, changing only description composition.

The server-side pass-through records **actual HTTP request and response bodies**, method, path and status, including SDK wire task states. It logs no HTTP headers or credentials. `http-results.json` includes two card-discovery responses, 16 sample rows, six delegated HTTP requests/responses, and two direct HTTP probes (metadata and streaming). Random local ports and task IDs are expected to change on reruns.

## Actual results

| Deterministic selection diagnostic | Baseline | Treatment |
|---|---:|---:|
| Cases | 8 | 8 |
| Expected routing decisions, including abstention | 2/8 | 6/8 |
| Wrong delegations | 0 | 1 |
| Actual delegated HTTP tasks | 0 | 6 |
| Completed delegated tasks | 0 | 4 |
| Failed delegated tasks | 0 | 2 |
| Candidate description characters | 50 | 333 |
| Median local workflow elapsed time (ms, one run) | 0.411 | 3.515 |

These are **fixture diagnostics, not model accuracy or user task-success rates**. Generic baseline descriptions contain none of the keyword fixture's requested capabilities, so it always abstains. Treatment sends actual HTTP tasks for distinct skills, multiple skills, specialization, overlap, misleading claims and invalid arithmetic input. The no-match and incomplete-description cases make no HTTP calls. The incomplete case is semantically insufficient but still a valid nonempty SDK description.

The false surgery claim causes an incorrect delegation and an actual `TASK_STATE_FAILED` result with `unsupported capability`. Invalid arithmetic input independently returns `TASK_STATE_FAILED` and an error artifact. Those failed states are present on the wire. The current framework projects artifact text to the manager; the scripted manager then says `fixture complete` without evaluating the task state. That final text must not be interpreted as successful task execution. This experiment does not establish automatic recovery or correct failure-aware model behavior.

Two additional probes pass:

- Canonical `additional_properties["a2a"]` message data appears on the real wire as `metadata.application_probe=round2`. This is application data, **not** a normative remote skill selector. No `skill_id` is sent or interpreted.
- `A2AAgent.run(..., stream=True)` uses a real `SendStreamingMessage` HTTP request and receives SDK SSE data returning `translation: hello`.

`http-run.log` records the completed network run. `http-tests.log`: **16/16** checks pass (3 HTTP-evidence checks, 3 prior integration checks, 10 original helper tests). The live harness itself asserts transport call counts, task answers, wire status, metadata and SSE. `http-upstream-regression.log`: **17/17** upstream A2A group-chat tests pass. `http-lint.log`: Ruff E/F passes; both new files formatted.

## Model resource and evidence boundary

No already-authorized no-new-cash model endpoint was established. Ollama is installed but the default local API at `127.0.0.1:11434/api/tags` was unreachable, and the default local model-manifest directory was absent. `model-resource-probe.json` records that bounded check; it does not prove no model exists elsewhere. Credentials were not inspected or used, no model was downloaded and no paid calls were made. Model source, tokens, cost and real-model efficacy remain null/untested. Replacing the selector with another deterministic heuristic would not close that gap.

The MIX demand-report/resolve tools were unavailable in this session; no capability-gap receipt was created or claimed.

This adds reproducible **local same-SDK HTTP integration evidence**, not independent cross-implementation interoperability, external adoption, maintainer feedback or bilateral collaboration. The live #9561 recheck found the issue open with only the existing four comments and no new maintainer response. Maintainer design-only guidance and the contribution policy remain binding; no core PR was opened. The owned repository's missing root license remains an adoption limitation.

## Reproduce

Start with the source/environment instructions in `README.md`, then install the server extras and run locally:

```sh
/path/to/.venv/bin/pip install 'a2a-sdk[http-server]==1.3.0' uvicorn pytest-timeout
cd co-do-001/framework_experiment
/path/to/.venv/bin/python http_interop.py
/path/to/.venv/bin/python -m pytest -v test_http_results.py test_integration.py ../test_capability_preview.py
/path/to/.venv/bin/ruff check --select E,F http_interop.py test_http_results.py
```

`http-environment.txt` retains installed versions. Servers bind only to `127.0.0.1` on ephemeral ports and shut down in `finally`. No API keys are required. Cancellation, authentication, resumability and remote production behavior are outside this run.
