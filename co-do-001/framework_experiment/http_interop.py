"""Real loopback HTTP A2A interop; deterministic application and selector, no model."""

import asyncio
import json
import socket
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from a2a.client import A2ACardResolver, minimal_agent_card
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill, Artifact, Part, Task, TaskState, TaskStatus
from agent_framework import Message
from agent_framework.a2a import A2AAgent
from agent_framework.orchestrations import GroupChatBuilder
from starlette.applications import Starlette

from capability_preview import selection_description
from run_experiment import RecordingSelector


class LocalMultiSkillExecutor(AgentExecutor):
    """Small auditable task service; advertised skills do not control dispatch."""

    def __init__(self, name):
        self.name = name
        self.calls = []

    async def execute(self, context, event_queue):
        text = context.get_user_input()
        if "translate" in text:
            answer, state = "translation: hello", TaskState.TASK_STATE_COMPLETED
        elif "summarize" in text and self.name == "alpha":
            answer, state = "summary: red blue", TaskState.TASK_STATE_COMPLETED
        elif "calculate" in text and self.name == "beta":
            if "invalid" in text:
                answer, state = (
                    "error: invalid arithmetic input",
                    TaskState.TASK_STATE_FAILED,
                )
            else:
                answer, state = "calculation: 5", TaskState.TASK_STATE_COMPLETED
        elif "spectroscopy" in text and self.name == "beta":
            answer, state = (
                "spectroscopy: peak at 500 nm",
                TaskState.TASK_STATE_COMPLETED,
            )
        else:
            answer, state = "unsupported capability", TaskState.TASK_STATE_FAILED
        self.calls.append(dict(input=text, answer=answer, state=TaskState.Name(state)))
        await event_queue.enqueue_event(
            Task(
                id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=state),
                artifacts=[Artifact(artifact_id="answer", parts=[Part(text=answer)])],
            )
        )

    async def cancel(self, context, event_queue):
        raise NotImplementedError("Cancellation is outside this bounded experiment")


class WireRecorder:
    """ASGI pass-through preserves actual request/response bytes; no headers logged."""

    def __init__(self, app, records):
        self.app, self.records = app, records

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        item = dict(
            method=scope["method"],
            path=scope["path"],
            request="",
            response="",
            status=None,
        )
        self.records.append(item)

        async def captured_receive():
            event = await receive()
            if event["type"] == "http.request":
                item["request"] += event.get("body", b"").decode()
            return event

        async def captured_send(event):
            if event["type"] == "http.response.start":
                item["status"] = event["status"]
            elif event["type"] == "http.response.body":
                item["response"] += event.get("body", b"").decode()
            await send(event)

        await self.app(scope, captured_receive, captured_send)


@asynccontextmanager
async def server(name, skills):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    card = minimal_agent_card(base + "/", ["JSONRPC"])
    card.name, card.description, card.version = (
        name,
        "General purpose assistant",
        "1.0.0",
    )
    card.supported_interfaces[0].protocol_version = "1.0"
    card.capabilities.streaming = True
    card.default_input_modes.append("text/plain")
    card.default_output_modes.append("text/plain")
    card.skills.extend(
        [AgentSkill(id=n, name=n, description=d, tags=["fixture"]) for n, d in skills]
    )
    executor, wire = LocalMultiSkillExecutor(name), []
    handler = DefaultRequestHandler(executor, InMemoryTaskStore(), card)
    app = WireRecorder(
        Starlette(
            routes=[
                *create_agent_card_routes(card),
                *create_jsonrpc_routes(handler, "/"),
            ]
        ),
        wire,
    )
    running = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
    task = asyncio.create_task(running.serve(sockets=[sock]))
    try:
        for _ in range(200):
            if running.started:
                break
            if task.done():
                await task
                raise RuntimeError("HTTP server failed to start")
            await asyncio.sleep(0.01)
        assert running.started
        yield base, executor, wire
    finally:
        running.should_exit = True
        await task
        sock.close()


CASES = [
    (
        "similar descriptions distinct skills",
        "calculate",
        "calculate 2+3",
        ["beta"],
        "calculation: 5",
    ),
    (
        "multiple skills",
        "summarize",
        "summarize red blue green",
        ["alpha"],
        "summary: red blue",
    ),
    (
        "specialist",
        "spectroscopy",
        "spectroscopy peak",
        ["beta"],
        "spectroscopy: peak at 500 nm",
    ),
    (
        "overlap",
        "translate",
        "translate bonjour",
        ["alpha", "beta"],
        "translation: hello",
    ),
    ("no match", "gardening", "gardening", [], None),
    ("misleading claim", "surgery", "surgery", [], "unsupported capability"),
    ("incomplete skill", "chromatography", "chromatography", ["alpha"], None),
    (
        "remote task failure",
        "calculate",
        "calculate invalid",
        ["beta"],
        "error: invalid arithmetic input",
    ),
]


async def main():
    rows = []
    async with (
        server(
            "alpha",
            [
                ("translate", "Translate bonjour"),
                ("summarize", "Summarize words"),
                ("surgery", "Expert surgery"),
                ("analysis", "General analysis"),
            ],
        ) as alpha,
        server(
            "beta",
            [
                ("calculate", "Calculate 2+3"),
                ("translate", "Translate bonjour"),
                ("spectroscopy", "Analyze spectroscopy"),
            ],
        ) as beta,
    ):
        services = [alpha, beta]
        async with httpx.AsyncClient(trust_env=False, timeout=10) as http:
            cards = [
                await A2ACardResolver(http, url).get_agent_card()
                for url, _, _ in services
            ]
            assert [len(card.skills) for card in cards] == [4, 3]
            for label, keyword, task, eligible, expected in CASES:
                for treatment in (False, True):
                    wire_before = [len(wire) for _, _, wire in services]
                    calls_before = [len(executor.calls) for _, executor, _ in services]
                    agents = [
                        A2AAgent(
                            agent_card=card,
                            http_client=http,
                            description=selection_description(card)
                            if treatment
                            else card.description,
                        )
                        for card in cards
                    ]
                    selector = RecordingSelector(keyword)
                    workflow = GroupChatBuilder(
                        participants=agents, orchestrator_agent=selector
                    ).build()
                    error = None
                    started = time.perf_counter()
                    try:
                        result = await workflow.run(task)
                        outputs = [str(output) for output in result.get_outputs()]
                    except Exception as exc:
                        error, outputs = f"{type(exc).__name__}: {exc}", []
                    elapsed = (time.perf_counter() - started) * 1000
                    calls = [
                        call
                        for (_, executor, _), before in zip(services, calls_before)
                        for call in executor.calls[before:]
                    ]
                    wire = [
                        record
                        for (_, _, records), before in zip(services, wire_before)
                        for record in records[before:]
                    ]
                    selected = selector.selected
                    assert len(calls) == (selected is not None)
                    assert all("skill_id" not in record["request"] for record in wire)
                    if selected:
                        assert len(wire) >= 1 and all(
                            record["status"] == 200 for record in wire
                        )
                        assert calls[0]["answer"] == expected
                    rows.append(
                        dict(
                            case=label,
                            arm="treatment" if treatment else "baseline",
                            task=task,
                            selected=selected,
                            eligible=eligible,
                            expected_decision=selected in eligible
                            if eligible
                            else selected is None,
                            wrong_delegation=selected is not None
                            and selected not in eligible,
                            calls=calls,
                            wire=wire,
                            error=error,
                            outputs=outputs,
                            latency_ms=elapsed,
                            prompt=selector.prompts[0],
                            conversations=selector.conversations,
                            description_chars=sum(len(a.description) for a in agents),
                            model_calls=0,
                            model_source=None,
                            tokens=None,
                            model_cost=None,
                        )
                    )
            # Existing canonical message metadata can carry application-owned data.
            # This is a private echo contract, not an A2A normative skill selector.
            before = len(beta[2])
            client = A2AAgent(agent_card=cards[1], http_client=http)
            reply = await client.run(
                Message(
                    "user",
                    ["calculate 2+3"],
                    additional_properties={"a2a": {"application_probe": "round2"}},
                )
            )
            probe = dict(response=reply.text, wire=beta[2][before:])
            assert reply.text == "calculation: 5"
            assert "application_probe" in probe["wire"][0]["request"]
            before_stream = len(beta[2])
            stream_text = ""
            async for update in client.run("translate bonjour", stream=True):
                stream_text += update.text
            streaming_probe = dict(text=stream_text, wire=beta[2][before_stream:])
            assert stream_text == "translation: hello"
            assert "data:" in streaming_probe["wire"][0]["response"]
            discovery = [
                record
                for _, _, records in services
                for record in records
                if record["method"] == "GET"
            ]
    Path("http-results.json").write_text(
        json.dumps(
            dict(
                discovery=discovery,
                samples=rows,
                metadata_probe=probe,
                streaming_probe=streaming_probe,
            ),
            indent=2,
        )
    )
    for arm in ("baseline", "treatment"):
        group = [row for row in rows if row["arm"] == arm]
        print(
            arm,
            json.dumps(
                dict(
                    samples=len(group),
                    expected_decisions=sum(row["expected_decision"] for row in group),
                    wrong_delegations=sum(row["wrong_delegation"] for row in group),
                    actual_http_tasks=sum(len(row["calls"]) for row in group),
                )
            ),
        )
    print(
        "PASS: real localhost SDK discovery + JSON-RPC/SSE + A2AAgent; "
        "real model UNTESTED"
    )


if __name__ == "__main__":
    asyncio.run(main())
