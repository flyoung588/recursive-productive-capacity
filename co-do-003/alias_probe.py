"""Additional regression matrix for LangGraph #9343 / existing PR #9352.

Uses the actual installed JsonPlusSerializer; no model or remote service.
"""
import json
import pytest
from pydantic import BaseModel, Field, AliasChoices, AliasPath
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


class PlainAlias(BaseModel):
    value: int = Field(default=1, alias="wireValue")


class CustomInitAlias(BaseModel):
    value: int = Field(default=1, alias="wireValue")

    def __init__(self, **data):
        super().__init__(**data)


class ChoicesAlias(BaseModel):
    value: int = Field(default=1, validation_alias=AliasChoices("wireValue", "legacyValue"))


class PathAlias(BaseModel):
    value: int = Field(default=1, validation_alias=AliasPath("payload", "value"))


class CustomRequiredAlias(BaseModel):
    value: int = Field(alias="wireValue")

    def __init__(self, **data):
        super().__init__(**data)


def main():
    serde = JsonPlusSerializer(allowed_msgpack_modules=True)
    cases = [PlainAlias(wireValue=42), CustomInitAlias(wireValue=42),
             ChoicesAlias(legacyValue=42), PathAlias(payload={"value": 42}),
             CustomRequiredAlias(wireValue=42)]
    results = []
    for original in cases:
        restored = serde.loads_typed(serde.dumps_typed(original))
        results.append({"case": type(original).__name__, "before": original.model_dump(),
                        "after": restored.model_dump(), "preserved": restored == original})
    print(json.dumps(results, indent=2))


@pytest.mark.parametrize("model,data", [
    (PlainAlias, {"wireValue": 42}),
    (CustomInitAlias, {"wireValue": 42}),
    (ChoicesAlias, {"legacyValue": 42}),
    (PathAlias, {"payload": {"value": 42}}),
    (CustomRequiredAlias, {"wireValue": 42}),
])
def test_preserves_value(model, data):
    serde = JsonPlusSerializer(allowed_msgpack_modules=True)
    original = model(**data)
    restored = serde.loads_typed(serde.dumps_typed(original))
    assert restored.model_dump() == original.model_dump()


if __name__ == "__main__":
    main()
