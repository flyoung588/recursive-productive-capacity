"""Real JsonPlusSerializer counterexamples; intentionally no reconstruction fix.

Run in a fresh process for each serializer source variant. This observes
constructor behavior as well as value equality; equality alone can hide fallback
construction after a user initializer has raised.
"""

import json
from typing import ClassVar, Literal

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import AliasChoices, AliasPath, BaseModel, Field


class Aliased(BaseModel):
    value: int = Field(default=1, alias="wireValue")

    def __init__(self, **data):
        super().__init__(**data)


class Nested(BaseModel):
    inner: Aliased


class NumberBranch(BaseModel):
    kind: Literal["number"] = "number"
    value: int = Field(default=1, alias="wireValue")

    def __init__(self, **data):
        super().__init__(**data)


class TextBranch(BaseModel):
    kind: Literal["text"] = "text"
    text: str


class UnionContainer(BaseModel):
    item: NumberBranch | TextBranch = Field(discriminator="kind")


class Choices(BaseModel):
    value: int = Field(
        default=1, validation_alias=AliasChoices("wireValue", "legacyValue")
    )

    def __init__(self, **data):
        super().__init__(**data)


class PathAlias(BaseModel):
    value: int = Field(default=1, validation_alias=AliasPath("payload", "value"))

    def __init__(self, **data):
        super().__init__(**data)


class DoublesOnConstruction(BaseModel):
    value: int
    successful_inits: ClassVar[int] = 0

    def __init__(self, **data):
        super().__init__(value=data["value"] * 2)
        type(self).successful_inits += 1


class RejectsStoredValue(BaseModel):
    value: int
    attempts: ClassVar[int] = 0
    successful_inits: ClassVar[int] = 0

    def __init__(self, **data):
        type(self).attempts += 1
        if data["value"] == 42:
            raise RuntimeError("stored value is not valid constructor input")
        super().__init__(value=data["value"] * 2)
        type(self).successful_inits += 1


def main():
    objects = [
        ("direct_alias", Aliased(wireValue=42)),
        ("nested_alias", Nested(inner=Aliased(wireValue=42))),
        ("discriminated_union", UnionContainer(item=NumberBranch(wireValue=42))),
        ("union_text_control", UnionContainer(item=TextBranch(text="retained"))),
        ("validation_alias_choices", Choices(legacyValue=42)),
        ("validation_alias_path", PathAlias(payload={"value": 42})),
        ("non_idempotent_constructor", DoublesOnConstruction(value=21)),
        ("constructor_exception", RejectsStoredValue(value=21)),
    ]
    serde = JsonPlusSerializer(allowed_msgpack_modules=True)
    rows = []
    for name, original in objects:
        cls = type(original)
        attempts = getattr(cls, "attempts", 0)
        successes = getattr(cls, "successful_inits", 0)
        restored = serde.loads_typed(serde.dumps_typed(original))
        rows.append(
            {
                "case": name,
                "before": original.model_dump(),
                "after": restored.model_dump(),
                "value_preserved": restored == original,
                "constructor_attempts_during_restore": (
                    cls.attempts - attempts if hasattr(cls, "attempts") else None
                ),
                "successful_custom_inits_during_restore": (
                    cls.successful_inits - successes
                    if hasattr(cls, "successful_inits")
                    else None
                ),
            }
        )
    # An oracle for the observations, not a claim that preservation is fixed.
    by_name = {row["case"]: row for row in rows}
    assert by_name["non_idempotent_constructor"]["after"] == {"value": 84}
    assert by_name["constructor_exception"]["value_preserved"] is True
    assert (
        by_name["constructor_exception"]["successful_custom_inits_during_restore"] == 0
    )
    assert by_name["constructor_exception"]["constructor_attempts_during_restore"] >= 1
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
