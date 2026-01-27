import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any


def _read_json(path: Path, default: Any):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


@dataclass
class ConfigStore:
    repo_root: Path
    terms_path: Path = field(init=False)
    settings_path: Path = field(init=False)

    def __post_init__(self):
        self.terms_path = self.repo_root / "config" / "custom_terms.json"
        self.settings_path = self.repo_root / "config" / "app_settings.json"

    def load_terms(self) -> Dict[str, List[str]]:
        return _read_json(self.terms_path, default={})

    def save_terms(self, terms: Dict[str, List[str]]) -> None:
        _write_json(self.terms_path, terms)

    def load_settings(self) -> Dict[str, Any]:
        return _read_json(self.settings_path, default={})

    def save_settings(self, settings: Dict[str, Any]) -> None:
        _write_json(self.settings_path, settings)

    @staticmethod
    def ensure_list_unique(items: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in items:
            x = (x or "").strip()
            if not x:
                continue
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out
