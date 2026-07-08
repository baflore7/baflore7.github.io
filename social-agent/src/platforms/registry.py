from __future__ import annotations

from src.content.generator import GeneratedPost
from src.platforms.base import DryRunAdapter, PlatformAdapter
from src.platforms.instagram import InstagramAdapter
from src.platforms.twitter import TwitterAdapter


def get_adapter(platform: str, *, dry_run: bool = False) -> PlatformAdapter:
    if dry_run:
        return DryRunAdapter(platform)

    adapters: dict[str, PlatformAdapter] = {
        "twitter": TwitterAdapter(),
        "threads": TwitterAdapter(),  # Threads API is limited; reuse X infra or dry-run
        "instagram": InstagramAdapter(),
    }
    return adapters.get(platform, DryRunAdapter(platform))
