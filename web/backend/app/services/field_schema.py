from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from backend.app.schemas.field_schema import (
    FieldSchemaNode,
    FieldSchemaNormalizeRequest,
    FieldSchemaNormalizeResponse,
)


def _preview_primitive(node: FieldSchemaNode) -> Any:
    if node.example is not None:
        return node.example
    if node.type == "string":
        return ""
    if node.type == "number":
        return 0
    if node.type == "boolean":
        return False
    return None


def _build_node_preview(node: FieldSchemaNode) -> Any:
    if node.type == "object":
        return {child.name: _build_node_preview(child) for child in node.children}

    if node.type == "array":
        if node.itemType == "object":
            item = {child.name: _build_node_preview(child) for child in node.children}
        elif node.itemType == "number":
            item = 0 if node.example is None else node.example
        elif node.itemType == "boolean":
            item = False if node.example is None else node.example
        else:
            item = "" if node.example is None else node.example
        return [item]

    return _preview_primitive(node)


def _normalize_node(node: FieldSchemaNode) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": node.name,
        "type": node.type,
        "required": node.required,
    }

    if node.description:
        data["description"] = node.description

    if node.type == "array":
        data["itemType"] = node.itemType

    if node.example is not None:
        data["example"] = node.example

    if node.children:
        data["children"] = [_normalize_node(child) for child in node.children]

    return data


def normalize_field_schema(request: FieldSchemaNormalizeRequest) -> FieldSchemaNormalizeResponse:
    if not request.fields:
        raise HTTPException(status_code=422, detail="At least one field is required")

    seen_names: set[str] = set()
    for field in request.fields:
        if field.name in seen_names:
            raise HTTPException(status_code=422, detail=f"Duplicate root field name: {field.name}")
        seen_names.add(field.name)

    schema = {
        "type": "object",
        "fields": [_normalize_node(field) for field in request.fields],
    }
    preview = {field.name: _build_node_preview(field) for field in request.fields}

    return FieldSchemaNormalizeResponse(
        status="success",
        message="Field schema normalized successfully",
        fieldCount=len(request.fields),
        schema=schema,
        preview=preview,
    )
