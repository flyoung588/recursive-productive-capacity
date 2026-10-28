"""Validate captured HTTP lifecycle evidence and preserve state distinctions."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def evidence():
    return json.loads(Path("lifecycle-results.json").read_text())


def test_input_required_resumes_same_remote_task(evidence):
    row = evidence["input_required"]
    assert row["prompt"]["user_input_request"]
    assert row["prompt"]["text"] == "What is your name?"
    initial, resumed = row["calls"]
    assert initial["task_id"] == resumed["task_id"]
    assert resumed["incoming_task_id"] == initial["task_id"]
    assert resumed["text"] == "Alice"
    assert "Thanks, Alice" in row["response"]
    posts = [entry for entry in row["wire"] if entry["method"] == "POST"]
    assert (
        json.loads(posts[0]["response"])["result"]["task"]["status"]["state"]
        == "TASK_STATE_INPUT_REQUIRED"
    )
    assert (
        json.loads(posts[1]["response"])["result"]["task"]["status"]["state"]
        == "TASK_STATE_COMPLETED"
    )


def test_cancel_interrupts_execution_and_persists_state(evidence):
    row = evidence["cancellation"]
    assert row["cancel_called"] and row["execution_interrupted"]
    assert row["stored"]["status"]["state"] == "TASK_STATE_CANCELED"
    assert not row["stored"].get("artifacts")
    posts = [entry for entry in row["wire"] if entry["method"] == "POST"]
    assert [json.loads(entry["request"])["method"] for entry in posts] == [
        "SendStreamingMessage",
        "GetTask",
        "CancelTask",
        "GetTask",
    ]
    assert "data:" in posts[0]["response"]
    assert "TASK_STATE_CANCELED" in posts[0]["response"]
    assert (
        json.loads(posts[2]["response"])["result"]["status"]["state"]
        == "TASK_STATE_CANCELED"
    )
    # This adapter emits no content update for a canceled task without artifacts.
    assert row["updates"] == []


def test_protocol_errors_are_not_successful_task_outputs(evidence):
    row = evidence["errors"]
    assert row["missing_task_error"]["type"] == "TaskNotFoundError"
    assert row["crash"]["exception_type"] == "InternalError"
    posts = [entry for entry in row["wire"] if entry["method"] == "POST"]
    assert all("error" in json.loads(entry["response"]) for entry in posts)
    assert json.loads(posts[-1]["response"])["error"]["code"] == -32603
