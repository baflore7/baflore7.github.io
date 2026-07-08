from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class PlatformConfig:
    name: str
    enabled: bool
    max_chars: int
    hashtag_count: int
    include_image_prompt: bool = False


@dataclass
class AccountConfig:
    raw: dict[str, Any]
    config_path: Path

    @property
    def account(self) -> dict[str, Any]:
        return self.raw["account"]

    @property
    def voice(self) -> dict[str, Any]:
        return self.raw["voice"]

    @property
    def content_pillars(self) -> list[dict[str, Any]]:
        return self.raw["content_pillars"]

    @property
    def schedule(self) -> dict[str, Any]:
        return self.raw["schedule"]

    @property
    def safety(self) -> dict[str, Any]:
        return self.raw["safety"]

    def platform_configs(self) -> list[PlatformConfig]:
        platforms = self.raw.get("platforms", {})
        result: list[PlatformConfig] = []
        for name, cfg in platforms.items():
            if not cfg.get("enabled", True):
                continue
            result.append(
                PlatformConfig(
                    name=name,
                    enabled=True,
                    max_chars=int(cfg.get("max_chars", 280)),
                    hashtag_count=int(cfg.get("hashtag_count", 3)),
                    include_image_prompt=bool(cfg.get("include_image_prompt", False)),
                )
            )
        return result


def load_config(path: str | Path | None = None) -> AccountConfig:
    load_dotenv()
    config_path = Path(path or os.environ.get("SOCIAL_AGENT_CONFIG", "config/account.yaml"))
    if not config_path.is_absolute():
        root = Path(__file__).resolve().parent.parent
        config_path = root / config_path

    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return AccountConfig(raw=raw, config_path=config_path)


def weighted_pillars(pillars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for pillar in pillars:
        weight = max(1, int(pillar.get("weight", 1)))
        expanded.extend([pillar] * weight)
    return expanded
