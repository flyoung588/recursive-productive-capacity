# 共做 #001 — A2A skill visibility via existing interfaces

External issue: https://github.com/microsoft/agent-framework/issues/9561

**Status:** An experimental, self-contained contribution on a separate GitHub branch; not merged into this repository's main branch, not integrated into Microsoft Agent Framework, and not approved by its maintainers.

## Actual contribution

A lightweight standard-library helper constructs a bounded list of an AgentCard's advertised skills and can be passed as the existing `description=` argument of `agent_framework_a2a.A2AAgent`. The existing group-chat registry reads participant descriptions. This makes capabilities available for consideration by the selector. It does **not** demonstrate better routing or an actual A2A remote skill invocation.

No framework APIs, protocol metadata, or `skill_id` behavior are changed. The remote skill-targeting half of #9561 remains unresolved.

## Run

From this directory, execute:

```bash
python -m unittest -v test_capability_preview.py
```

The same source and tests were executed locally on 2026-10-28 with **10/10 passed**. The Microsoft Agent Framework's actual runtime integration was **not executed**.

## Usage sketch (not integration-tested)

```python
from agent_framework_a2a import A2AAgent
from capability_preview import selection_description

# card is an AgentCard retrieved via your existing A2A card resolver.
agent = A2AAgent(
    agent_card=card,
    name=card.name,
    description=selection_description(card),
    url=remote_url,
)
```

The `explicit_description` parameter deliberately preserves application overrides. Cards are untrusted input: whitespace normalization and length caps do not prevent prompt injection.

## Next decision

Maintainers asked for a design-only review. Is description composition sufficient as an opt-in sample for the participant-selection half, or is a real interoperable multi-skill server/client case needed? A permanent routing API should not be invented without specification and evidence.

The source is presented for public technical discussion. No new license grant or institutional endorsement is implied by this branch.
