"""Shared image helpers used by protocol adapters."""

from __future__ import annotations

import base64
from pathlib import Path


def encode_image_from_path(image_path: str) -> str:
    try:
        from dsetkit.utils.image import image_to_base64

        return image_to_base64(image_path)
    except ModuleNotFoundError:
        image_bytes = Path(image_path).read_bytes()
        return base64.b64encode(image_bytes).decode("utf-8")


def read_image_size(image_path: str) -> tuple[int, int]:
    try:
        from dsetkit.utils.image import read_image_info

        width, height = read_image_info(image_path).size
        return int(width), int(height)
    except ModuleNotFoundError:
        try:
            from PIL import Image
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "Image size helpers require either dsetkit or Pillow to be installed"
            ) from exc

        with Image.open(image_path) as image:
            width, height = image.size
        return int(width), int(height)
