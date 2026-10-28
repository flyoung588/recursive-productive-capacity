"""Check recorded real HTTP outcomes separately from selector expectations."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def evidence():
    return json.loads(Path("http-results.json").read_text())


def test_actual_network_discovery_and_advertised_skills(evidence):
    cards = [json.loads(row["response"]) for row in evidence["discovery"]]
    assert len(cards) == 2
    assert [len(card["skills"]) for card in cards] == [4, 3]
    assert all(
        card["supportedInterfaces"][0]["protocolVersion"] == "1.0" for card in cards
    )


def test_real_http_task_outcomes_and_no_match(evidence):
    rows = evidence["samples"]
    assert len(rows) == 16
    treatment = {row["case"]: row for row in rows if row["arm"] == "treatment"}
    assert treatment["no match"]["wire"] == []
    assert treatment["incomplete skill"]["wire"] == []
    completed = [
        call
        for row in rows
        for call in row["calls"]
        if call["state"] == "TASK_STATE_COMPLETED"
    ]
    assert len(completed) == 4
    for label in ("misleading claim", "remote task failure"):
        row = treatment[label]
        assert row["calls"][0]["state"] == "TASK_STATE_FAILED"
        wire_result = json.loads(row["wire"][0]["response"])["result"]["task"]
        assert wire_result["status"]["state"] == "TASK_STATE_FAILED"
        # The framework projects failure artifact text into the manager conversation;
        # the scripted manager's final output is not a claim of task success.
        assert row["calls"][0]["answer"] in row["conversations"][-1]
    assert treatment["misleading claim"]["wrong_delegation"]


def test_metadata_and_sse_use_real_wire(evidence):
    probe = evidence["metadata_probe"]
    assert probe["response"] == "calculation: 5"
    request = json.loads(probe["wire"][0]["request"])
    assert request["params"]["message"]["metadata"]["application_probe"] == "round2"
    streaming = evidence["streaming_probe"]
    assert streaming["text"] == "translation: hello"
    assert (
        json.loads(streaming["wire"][0]["request"])["method"] == "SendStreamingMessage"
    )
    assert "data:" in streaming["wire"][0]["response"]
    assert all(
        "skill_id" not in row["request"]
        for sample in evidence["samples"]
        for row in sample["wire"]
    )
