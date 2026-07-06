from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model


TYPE_MAP: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict[str, Any],
}


def _annotation_from_schema(field_schema: dict[str, Any]) -> Any:
    schema_type = field_schema.get("type", "string")

    if schema_type == "array":
        item_schema = field_schema.get("items", {"type": "string"})
        return list[_annotation_from_schema(item_schema)]

    return TYPE_MAP.get(schema_type, str)


def build_model_from_json_schema(name: str, schema: dict[str, Any]) -> type[BaseModel]:
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise ValueError("Schema must contain a non-empty 'properties' object.")

    required = set(schema.get("required", []))
    fields: dict[str, tuple[Any, Any]] = {}

    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            raise ValueError(f"Field '{field_name}' must be an object.")

        annotation = _annotation_from_schema(field_schema)
        description = field_schema.get("description")

        if field_name in required:
            default = Field(..., description=description)
        else:
            default = Field(None, description=description)
            annotation = Optional[annotation]

        fields[field_name] = (annotation, default)

    return create_model(
        name,
        __config__=ConfigDict(extra="ignore"),
        **fields,
    )
