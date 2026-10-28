"""Real HTTP/SSE lifecycle evidence: input, cancellation, and protocol errors."""

import asyncio
import json
from pathlib import Path

import httpx
from a2a.client import A2ACardResolver
from a2a.server.agent_execution import AgentExecutor
from a2a.types import (
    Artifact,
    CancelTaskRequest,
    GetTaskRequest,
    Message as RemoteMessage,
    Part,
    Role,
    Task,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from agent_framework import Content, Message
from agent_framework.a2a import A2AAgent
from agent_framework.orchestrations import GroupChatBuilder
from google.protobuf.json_format import MessageToDict

from http_interop import server


class LifecycleExecutor(AgentExecutor):
    def __init__(self):
        self.calls = []
        self.started = asyncio.Event()
        self.interrupted = asyncio.Event()
        self.cancel_called = False
        self.task_id = None

    async def execute(self, context, event_queue):
        text = context.get_user_input()
        self.calls.append(
            dict(
                text=text,
                task_id=context.task_id,
                context_id=context.context_id,
                incoming_task_id=context.message.task_id,
            )
        )
        if text == "Start":
            await event_queue.enqueue_event(
                Task(
                    id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(
                        state=TaskState.TASK_STATE_INPUT_REQUIRED,
                        message=RemoteMessage(
                            message_id="request-name",
                            role=Role.ROLE_AGENT,
                            parts=[Part(text="What is your name?")],
                        ),
                    ),
                )
            )
        elif text == "Long operation":
            self.task_id = context.task_id
            await event_queue.enqueue_event(
                Task(
                    id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_WORKING),
                )
            )
            self.started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.interrupted.set()
                raise
        elif text == "Crash":
            raise RuntimeError("bounded lifecycle executor failure")
        else:
            # Resuming an existing task requires updates, not a replacement Task.
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    artifact=Artifact(
                        artifact_id="answer", parts=[Part(text=f"Thanks, {text}")]
                    ),
                )
            )
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
                )
            )

    async def cancel(self, context, event_queue):
        self.cancel_called = True
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_CANCELED),
            )
        )


async def input_required_case():
    executor = LifecycleExecutor()
    async with server("remote", [("conversation", "Ask for a name")], executor) as (
        url,
        _,
        wire,
    ):
        async with httpx.AsyncClient(trust_env=False, timeout=10) as http:
            card = await A2ACardResolver(http, url).get_agent_card()
            remote = A2AAgent(agent_card=card, http_client=http)
            workflow_agent = (
                GroupChatBuilder(
                    participants=[remote],
                    selection_func=lambda state: "remote",
                    max_rounds=1,
                    output_from="all",
                )
                .build()
                .as_agent(name="conversation")
            )
            initial = await workflow_agent.run("Start")
            requests = [
                content
                for message in initial.messages
                for content in message.contents
                if content.type == "function_call" and content.name == "request_info"
            ]
            assert len(requests) == 1
            response = await workflow_agent.run(
                Message(
                    "tool",
                    [
                        Content.from_function_result(
                            call_id=requests[0].call_id, result="Alice"
                        )
                    ],
                )
            )
            assert not response.user_input_requests
            assert len(executor.calls) == 2
            assert executor.calls[0]["task_id"] == executor.calls[1]["task_id"]
            assert executor.calls[1]["incoming_task_id"] == executor.calls[0]["task_id"]
            assert any("Thanks, Alice" in record["response"] for record in wire)
            assert "Thanks, Alice" in response.text
    return dict(
        calls=executor.calls,
        prompt=requests[0].arguments["request_event"]["data"].to_dict(),
        response=response.text,
        wire=wire,
    )


async def cancellation_case():
    executor = LifecycleExecutor()
    async with server(
        "remote", [("long-operation", "Cancelable operation")], executor
    ) as (url, _, wire):
        async with httpx.AsyncClient(trust_env=False, timeout=10) as http:
            card = await A2ACardResolver(http, url).get_agent_card()
            remote = A2AAgent(agent_card=card, http_client=http)
            updates = []

            async def consume():
                async for update in remote.run("Long operation", stream=True):
                    updates.append(
                        dict(
                            text=update.text,
                            response_id=update.response_id,
                            raw_type=type(update.raw_representation).__name__,
                            raw=MessageToDict(update.raw_representation)
                            if hasattr(update.raw_representation, "DESCRIPTOR")
                            else None,
                        )
                    )

            consumer = asyncio.create_task(consume())
            await asyncio.wait_for(executor.started.wait(), timeout=5)
            # Query the actual SDK store over HTTP before requesting cancellation.
            for _ in range(100):
                try:
                    working = await remote.client.get_task(
                        GetTaskRequest(id=executor.task_id)
                    )
                    if working.status.state == TaskState.TASK_STATE_WORKING:
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.01)
            else:
                raise AssertionError("working task not observable")
            canceled = await remote.client.cancel_task(
                CancelTaskRequest(id=executor.task_id)
            )
            assert canceled.status.state == TaskState.TASK_STATE_CANCELED
            await asyncio.wait_for(consumer, timeout=5)
            await asyncio.wait_for(executor.interrupted.wait(), timeout=5)
            stored = await remote.client.get_task(GetTaskRequest(id=executor.task_id))
            assert stored.status.state == TaskState.TASK_STATE_CANCELED
            assert executor.cancel_called
            assert not stored.artifacts
    return dict(
        task_id=executor.task_id,
        cancel_called=executor.cancel_called,
        execution_interrupted=executor.interrupted.is_set(),
        stored=MessageToDict(stored),
        updates=updates,
        wire=wire,
    )


async def error_case():
    executor = LifecycleExecutor()
    async with server("remote", [("failure", "Bounded failure probe")], executor) as (
        url,
        _,
        wire,
    ):
        async with httpx.AsyncClient(trust_env=False, timeout=10) as http:
            card = await A2ACardResolver(http, url).get_agent_card()
            remote = A2AAgent(agent_card=card, http_client=http)
            missing = None
            try:
                await remote.client.get_task(
                    GetTaskRequest(id="nonexistent-lifecycle-task")
                )
            except Exception as exc:
                missing = dict(type=type(exc).__name__, message=str(exc))
            assert missing is not None
            crash = None
            try:
                response = await remote.run("Crash")
                crash = dict(
                    text=response.text,
                    raw_type=type(response.raw_representation).__name__,
                )
            except Exception as exc:
                crash = dict(exception_type=type(exc).__name__, message=str(exc))
            post = [record for record in wire if record["method"] == "POST"]
            assert len(post) == 2
            assert "error" in json.loads(post[0]["response"])
            # Do not impose a success interpretation on an empty projected reply.
            assert "TASK_STATE_FAILED" in post[1]["response"] or "error" in json.loads(
                post[1]["response"]
            )
    return dict(missing_task_error=missing, crash=crash, wire=wire)


async def main():
    results = dict(
        input_required=await input_required_case(),
        cancellation=await cancellation_case(),
        errors=await error_case(),
    )
    Path("lifecycle-results.json").write_text(json.dumps(results, indent=2))
    print("PASS input-required: real HTTP group-chat pause/resume, same remote task")
    print(
        "PASS cancellation: HTTP CancelTask, SSE closure, interrupted executor, "
        "persisted CANCELED"
    )
    print("PASS errors: nonexistent task and executor failure remain errors on wire")
    print("No model or selection experiment performed")


if __name__ == "__main__":
    asyncio.run(main())
