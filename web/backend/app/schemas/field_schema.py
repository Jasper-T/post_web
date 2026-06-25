from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


FieldType = Literal["string", "number", "boolean", "object", "array"]
ArrayItemType = Literal["string", "number", "boolean", "object"]


class FieldSchemaNode(BaseModel):
    name: str = Field(..., min_length=1)
    type: FieldType
    required: bool = False
    description: str | None = None
    example: Any = None
    itemType: ArrayItemType | None = None
    children: list["FieldSchemaNode"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape(self) -> "FieldSchemaNode":
        if self.type == "array":
            if not self.itemType:
                raise ValueError(f"Array field '{self.name}' must declare itemType")
            if self.itemType == "object" and not self.children:
                raise ValueError(f"Array field '{self.name}' with object itemType must contain child fields")
            if self.itemType != "object" and self.children:
                raise ValueError(f"Array field '{self.name}' only supports children when itemType is object")

        if self.type not in {"object", "array"} and self.children:
            raise ValueError(f"Primitive field '{self.name}' cannot contain child fields")

        if self.type != "array" and self.itemType is not None:
            raise ValueError(f"Only array fields can declare itemType: '{self.name}'")

        return self


class FieldSchemaNormalizeRequest(BaseModel):
    fields: list[FieldSchemaNode] = Field(default_factory=list)


class FieldSchemaNormalizeResponse(BaseModel):
    status: Literal["success"]
    message: str
    fieldCount: int
    schema: dict[str, Any]
    preview: dict[str, Any]
