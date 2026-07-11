"""Persist runtime config overrides across the process lifetime.

Writes to runtime_config.json which is read at startup before the app
initializes, overriding env vars for settings that admins can switch.
On Render (ephemeral disk) this still resets on redeploy — that's expected.
On a persistent VM or local setup it survives restarts.
"""

import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "runtime_config.json")
_CONFIG_PATH = os.path.abspath(_CONFIG_PATH)


def load() -> dict:
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(key: str, value: str):
    config = load()
    config[key] = value
    with open(_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get(key: str, default: str = None) -> str:
    return load().get(key, default)
