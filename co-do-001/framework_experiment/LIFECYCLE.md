# Round 3: real HTTP lifecycle checks

This AI-assisted increment adds actual network lifecycle evidence rather than another selector simulation. It reuses the round 2 `server` and `WireRecorder` implementations from `http_interop.py`, adding an injectable executor and explicit SDK handler shutdown. `http_lifecycle.py` supplies a separate executor and consumes the same server/recording infrastructure without duplicating the HTTP setup. This is concrete reuse within this project; no independent external adopter or cross-project reuse is claimed.

Framework source remains `4a272d2b8e96242a1e00783e833d42922a618d23`, SDK remains 1.3.0 and server dependencies remain as recorded in `http-environment.txt`.

## Actual outcomes

- **Input-required/resume:** real `A2ACardResolver` discovery, actual HTTP `SendMessage`, and real GroupChatBuilder-as-agent request-info envelope. A tool response containing `Alice` resumes the **same remote task ID**, and the server returns a completed artifact `Thanks, Alice`. The sample opts into `output_from="all"` to surface participant output; max-round termination text is also present and is not the remote task result. The first implementation tried to replace an existing task with a new `Task`, which SDK ignored. The working application sends `TaskArtifactUpdateEvent` and `TaskStatusUpdateEvent` instead. This was an application correction, not a framework defect or fix.
- **Cancellation:** actual `SendStreamingMessage` opens SSE; `GetTask` observes WORKING; an actual HTTP `CancelTask` invokes the server cancel hook and interrupts its executing coroutine; another `GetTask` confirms persisted CANCELED without artifacts. The SSE body includes CANCELED and the consumer ends. The framework projects no content updates for this artifact-free canceled task (`updates=[]`), so stream closure alone must not be mistaken for successful task completion. Cancellation uses the SDK client exposed by the A2AAgent, not a new public framework cancellation API.
- **Protocol errors:** actual `GetTask` for a nonexistent task raises `TaskNotFoundError`; a bounded server executor exception becomes JSON-RPC `-32603` and propagates from actual `A2AAgent.run` as `InternalError`. No failed call is recorded as a successful task output.

The run records three HTTP discoveries and eight JSON-RPC HTTP calls, including the open SSE request. All request/response bodies, executor/task IDs, user-input envelope, cancellation flags and error types are in `lifecycle-results.json`. No authentication headers, credentials or private user files are involved.

`lifecycle-run.log` contains the expected error-path traceback, max-round warning and an SDK dispatcher-shutdown warning. These remain visible; the run does **not** establish leak-free shutdown, production readiness or arbitrary cancellation races. The harness asserts bounded completion, cancellation interruption and stored state for this run only.

## Checks

- New live harness assertions passed for all three lifecycle cases.
- `lifecycle-tests.log`: 19/19 evidence/helper checks passed (3 new lifecycle checks + prior 16 checks).
- `lifecycle-upstream-tests.log`: 17/17 existing upstream A2A group-chat regressions passed.
- `lifecycle-http-regression.log`: the prior real-HTTP harness still passes with injectable executors and explicit handler cleanup. Its new temporary results were kept locally; historical round 2 results were preserved.
- `lifecycle-lint.log`: Ruff E/F checks passed; new files formatted.

Reproduce after the round 2 installation:

```sh
cd co-do-001/framework_experiment
/path/to/.venv/bin/python http_lifecycle.py
/path/to/.venv/bin/python -m pytest -v test_lifecycle_results.py test_http_results.py test_integration.py ../test_capability_preview.py
/path/to/.venv/bin/ruff check --select E,F http_lifecycle.py test_lifecycle_results.py http_interop.py
```

## Remaining boundary

The bounded round 3 local model probe again found no listening default Ollama endpoint and no default model-manifest directory (`model-resource-round3.json`). This does not prove there are no resources elsewhere. No authorized no-new-cash model was established; no credentials were inspected, no paid API was used and no model was downloaded. Model source, real-model routing effects and costs remain untested. No new selector benchmark is claimed.

The #9561 recheck found five comments, with the latest being the prior experimental update and no new maintainer reply. These lifecycle results add reusable local transport evidence but do not settle the selection API or a normative remote-skill contract. No new upstream issue comment or PR is warranted solely by these adjacent lifecycle checks. No upstream implementation approval, external adoption or bilateral collaboration is claimed. The owned repository's missing root license remains an adoption limitation.
