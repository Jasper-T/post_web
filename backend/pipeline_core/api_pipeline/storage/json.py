import json
import os
import tempfile
from pathlib import Path

from .base import BaseStorage, StorageRegistry


@StorageRegistry.register("json")
class JsonStorage(BaseStorage):

    def __init__(self, save_dir):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _safe_name(self, name: str) -> str:
        return Path(name).stem.replace("/", "_").replace("\\", "_")

    def save(self, save_name: str, data: list):
        safe_name = self._safe_name(save_name)
        save_path = self.save_dir / f"{safe_name}.json"

        tmp_fd, tmp_path = tempfile.mkstemp(dir=self.save_dir)

        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            os.replace(tmp_path, save_path)

        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
