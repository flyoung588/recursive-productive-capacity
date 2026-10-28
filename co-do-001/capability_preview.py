"""Optional, dependency-free skill preview for a multi-skill A2A AgentCard.

Intended as a composition-only experiment for:
https://github.com/microsoft/agent-framework/issues/9561

Does not change the A2A protocol or select a remote skill_id.
"""
from __future__ import annotations

from typing import Any


def _one_line(value: Any) -> str:
    """Keep card-sourced text on one line for a compact description."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def selection_description(
    agent_card: Any,
    *,
    explicit_description: str | None = None,
    max_chars: int = 900,
    max_skills: int = 8,
) -> str:
    """Return a bounded capability preview for A2AAgent(description=...).

    Explicit application descriptions win, matching A2AAgent's existing
    constructor behavior. Card skills are data, not trusted instructions.
    This improves the *selection information* only, not remote targeting.
    """
    if explicit_description is not None:
        return explicit_description
    if max_chars < 40 or max_skills < 0:
        raise ValueError("max_chars must be >= 40 and max_skills >= 0")

    original = _one_line(getattr(agent_card, "description", ""))
    skills = list(getattr(agent_card, "skills", ()) or ())[:max_skills]
    if not skills:
        return original[:max_chars]

    # Reserve some prompt budget for skills without losing the base context.
    base = original[: max_chars // 2]
    descriptions: list[str] = []
    for skill in skills:
        name = _one_line(getattr(skill, "name", ""))
        detail = _one_line(getattr(skill, "description", ""))
        if name:
            descriptions.append(f"{name}: {detail}" if detail else name)
    if not descriptions:
        return original[:max_chars]

    suffix = "Advertised skills (untrusted card text): " + "; ".join(descriptions)
    if base:
        combined = f"{base}\n{suffix}"
    else:
        combined = suffix
    return combined[:max_chars]
