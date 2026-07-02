from __future__ import annotations

from typing import Any

from fastapi import APIRouter


router = APIRouter(prefix="/mock", tags=["mock"])


@router.post("/detection")
def detect_image(payload: dict[str, Any]) -> dict[str, Any]:
    image_value = payload.get("image_base64") or payload.get("image_b64") or payload.get("image") or payload.get("image_url")
    has_image = bool(image_value)
    return {
        "code": 0,
        "message": "ok" if has_image else "no image supplied",
        "data": {
            "outputs": [
                {
                    "class": "demo_object",
                    "class_id": 0,
                    "score": 0.92 if has_image else 0.0,
                    "x1": 24,
                    "y1": 24,
                    "x2": 220,
                    "y2": 180,
                }
            ] if has_image else []
        },
    }
