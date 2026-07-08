from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.content.generator import GeneratedPost


@dataclass
class PublishResult:
    success: bool
    platform: str
    post_id: str | None = None
    url: str | None = None
    message: str = ""


class PlatformAdapter(ABC):
    name: str

    @abstractmethod
    def publish(self, post: GeneratedPost) -> PublishResult:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...


class DryRunAdapter(PlatformAdapter):
    """Preview mode — logs what would be posted without API calls."""

    def __init__(self, name: str) -> None:
        self.name = name

    def is_configured(self) -> bool:
        return True

    def publish(self, post: GeneratedPost) -> PublishResult:
        return PublishResult(
            success=True,
            platform=self.name,
            post_id="dry-run",
            message=f"[DRY RUN] Would post to {self.name}: {post.full_text[:120]}...",
        )
