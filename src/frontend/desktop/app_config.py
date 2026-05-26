import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".enem_da_read" / "config.json"


def load_config() -> dict:
    """Load config from disk. Returns defaults if file doesn't exist."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {"language": "pt_BR", "theme": "dark_blue"}


def save_config(config: dict) -> None:
    """Persist config to disk."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
