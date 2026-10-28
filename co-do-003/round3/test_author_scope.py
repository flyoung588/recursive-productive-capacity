"""Checks aligned with the PR author's explicit ordinary-model repair scope."""

from typing import Literal

import pytest
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, Field


class Ordinary(BaseModel):
    value: int = Field(default=1, alias="wireValue")


class NestedOrdinary(BaseModel):
    values: list[Ordinary]


class NumericOrdinary(BaseModel):
    kind: Literal["number"] = "number"
    value: int = Field(default=1, alias="wireValue")


class TextOrdinary(BaseModel):
    kind: Literal["text"] = "text"
    text: str


class UnionOrdinary(BaseModel):
    item: NumericOrdinary | TextOrdinary = Field(discriminator="kind")


class ChoiceOrdinary(BaseModel):
    value: int = Field(
        default=1, validation_alias=AliasChoices("wireValue", "legacyValue")
    )


class PathOrdinary(BaseModel):
    value: int = Field(default=1, validation_alias=AliasPath("payload", "value"))


class OptInCustom(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    value: int = Field(default=1, alias="wireValue")

    def __init__(self, **data):
        super().__init__(**data)


class NestedOptIn(BaseModel):
    inner: OptInCustom


@pytest.mark.parametrize(
    "obj",
    [
        Ordinary(wireValue=42),
        NestedOrdinary(values=[Ordinary(wireValue=42)]),
        UnionOrdinary(item=NumericOrdinary(wireValue=42)),
        UnionOrdinary(item=TextOrdinary(text="retained")),
        ChoiceOrdinary(legacyValue=42),
        PathOrdinary(payload={"value": 42}),
        OptInCustom(wireValue=42),
        NestedOptIn(inner=OptInCustom(wireValue=42)),
    ],
)
def test_author_scoped_roundtrip(obj):
    serde = JsonPlusSerializer(allowed_msgpack_modules=True)
    assert serde.loads_typed(serde.dumps_typed(obj)) == obj
