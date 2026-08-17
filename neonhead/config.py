"""Configuration loading: JSON file merged over the packaged defaults."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(_HERE, "config.json")


def hex_to_rgb(value: str):
    """'#3FB870' -> (0.247, 0.722, 0.439). Accepts 3- or 6-digit hex."""
    s = value.lstrip("#").strip()
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"bad colour: {value!r}")
    return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    """Dotted access over the merged config dict, with colours pre-parsed."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.rgb = {k: hex_to_rgb(v) for k, v in data["palette"].items()}

    def __getitem__(self, key: str):
        return self.data[key]

    def get(self, path: str, default=None):
        node: Any = self.data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def apply(self, patch: Dict[str, Any]) -> None:
        """Live-patch the config (used by the `config` network command)."""
        self.data = deep_merge(self.data, patch)
        self.rgb = {k: hex_to_rgb(v) for k, v in self.data["palette"].items()}

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        with open(DEFAULT_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if path and os.path.abspath(path) != os.path.abspath(DEFAULT_PATH):
            with open(path, "r", encoding="utf-8") as fh:
                data = deep_merge(data, json.load(fh))
        return cls(data)
