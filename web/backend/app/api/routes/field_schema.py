from backend.app.schemas.field_schema import (
    FieldSchemaNormalizeRequest,
    FieldSchemaNormalizeResponse,
)
from backend.app.services.field_schema import normalize_field_schema

from fastapi import APIRouter


router = APIRouter(prefix="/field-schema", tags=["field-schema"])


@router.post("/normalize", response_model=FieldSchemaNormalizeResponse)
def normalize_schema(request: FieldSchemaNormalizeRequest) -> FieldSchemaNormalizeResponse:
    return normalize_field_schema(request)
