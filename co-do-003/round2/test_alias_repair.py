"""Regression checks for a scoped, experimental load-side alias repair."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import BaseModel, ConfigDict, Field


class DefaultAlias(BaseModel):
    value: int = Field(default=1, alias="wireValue")

    def __init__(self, **data):
        super().__init__(**data)


class RequiredAlias(BaseModel):
    value: int = Field(alias="wireValue")

    def __init__(self, **data):
        super().__init__(**data)


class AllowedExtraAlias(DefaultAlias):
    model_config = ConfigDict(extra="allow")


class ByNameAlias(DefaultAlias):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=False)


class NestedAlias(BaseModel):
    inner: DefaultAlias


@pytest.mark.parametrize(
    "obj",
    [
        DefaultAlias(wireValue=42),
        RequiredAlias(wireValue=42),
        AllowedExtraAlias(wireValue=42, note="retained"),
        ByNameAlias(value=42),
        AIMessage(
            content="answer", tool_calls=[{"name": "lookup", "args": {}, "id": "t"}]
        ),
        ToolMessage(content="result", tool_call_id="t"),
        HumanMessage(content="hello"),
    ],
)
def test_scoped_repair_preserves_model(obj):
    serde = JsonPlusSerializer(allowed_msgpack_modules=True)
    assert serde.loads_typed(serde.dumps_typed(obj)) == obj


def test_known_nested_custom_init_boundary():
    """Keep this failure visible: the prototype only repairs top-level aliases."""
    obj = NestedAlias(inner=DefaultAlias(wireValue=42))
    serde = JsonPlusSerializer(allowed_msgpack_modules=True)
    restored = serde.loads_typed(serde.dumps_typed(obj))
    assert restored == obj
