"""Dynamic configuration store — persists overrides to a JSON file."""

import json
from pathlib import Path
from app.config.schema import ConfigSchema


class ConfigStore:
    """Read/write runtime configuration overrides."""

    def __init__(self, path: str = "/data/config.json"):
        self._path = Path(path)

    def load(self, cfg: ConfigSchema) -> ConfigSchema:
        if not self._path.exists():
            return cfg
        try:
            overrides = json.loads(self._path.read_text())
            for k, v in overrides.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        except (json.JSONDecodeError, TypeError):
            pass
        return cfg

    def save(self, overrides: dict) -> ConfigSchema:
        cfg = ConfigSchema()
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(overrides, indent=2))
        return cfg
