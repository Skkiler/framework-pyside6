# ui/services/theme_repository_json.py

import json, os
from typing import List, Dict, Any
from ..core.interface_ports import IThemeRepository

class JsonThemeRepository(IThemeRepository):
    def __init__(self, theme_dir: str):
        self.theme_dir = theme_dir

    def _path(self, name): 
        return os.path.join(self.theme_dir, f"{name}.json")

    def list_themes(self) -> List[str]:
        if not os.path.exists(self.theme_dir):
            return []
        return [os.path.splitext(f)[0] for f in os.listdir(self.theme_dir) if f.endswith(".json")]

    def load_theme(self, name: str) -> Dict[str, Any]:
        with open(self._path(name), "r", encoding="utf-8") as f:
            return json.load(f)

    def save_theme(self, name: str, data: Dict[str, Any]) -> None:
        os.makedirs(self.theme_dir, exist_ok=True)
        with open(self._path(name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete_theme(self, name: str) -> None:
        os.remove(self._path(name))
