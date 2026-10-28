"""Assertions over the real-framework experiment and SDK constructor semantics."""

import json
from pathlib import Path

from a2a.client import minimal_agent_card
from a2a.types import AgentSkill
from agent_framework.a2a import A2AAgent
from capability_preview import selection_description


def test_framework_routes_and_declines():
    rows = json.loads(Path("results.json").read_text())
    assert len(rows) == 14
    by_case = {(r["case"], r["arm"]): r for r in rows}
    assert by_case["similar descriptions", "baseline"]["selected"] is None
    assert by_case["similar descriptions", "treatment"]["selected"] == "beta"
    assert by_case["no suitable agent", "treatment"]["transport_calls"] == 0
    assert by_case["misleading skill", "treatment"]["wrong_delegation"]
    assert by_case["incomplete description", "treatment"]["selected"] is None
    assert all(r["model_calls"] == 0 for r in rows)


def test_explicit_empty_override_survives_real_constructor():
    card = minimal_agent_card("https://example.invalid", ["JSONRPC"])
    card.description = "base"
    card.skills.extend(
        [AgentSkill(id="one", name="translate", description="text", tags=[])]
    )
    for override in ("", "application curated"):
        description = selection_description(card, explicit_description=override)
        agent = A2AAgent(agent_card=card, client=object(), description=description)
        assert agent.description == override


def test_preview_bound_with_real_sdk_card():
    card = minimal_agent_card("https://example.invalid", ["JSONRPC"])
    card.description = "base " * 1000
    card.skills.extend(
        [
            AgentSkill(id=str(i), name=f"skill{i}", description="detail" * 100, tags=[])
            for i in range(12)
        ]
    )
    preview = selection_description(card)
    assert len(preview) <= 900
    assert "skill0" in preview
    assert "skill8" not in preview
